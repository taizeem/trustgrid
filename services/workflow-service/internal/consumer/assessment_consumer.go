package consumer

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/trustgrid/workflow-service/internal/domain"
	"github.com/trustgrid/workflow-service/internal/repository"
)

type EventEnvelope struct {
	ID            string          `json:"id"`
	Type          string          `json:"type"`
	TenantID      string          `json:"tenantid"`
	CorrelationID string          `json:"correlationid"`
	Data          json.RawMessage `json:"data"`
}

type AssessmentSubmittedData struct {
	AssessmentID string `json:"assessment_id"`
	VendorID     string `json:"vendor_id"`
	TemplateID   string `json:"template_id"`
	SubmittedBy  string `json:"submitted_by"`
}

type AssessmentConsumer struct {
	conn *amqp.Connection
	ch   *amqp.Channel
	repo *repository.PostgresRepository
	db   *sql.DB
}

func NewAssessmentConsumer(amqpURI string, repo *repository.PostgresRepository, db *sql.DB) (*AssessmentConsumer, error) {
	conn, err := amqp.Dial(amqpURI)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to rabbitmq: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		return nil, fmt.Errorf("failed to open channel: %w", err)
	}

	// 1. Declare Primary and Dead-Letter Exchanges
	if err := ch.ExchangeDeclare("trustgrid.events", "topic", true, false, false, false, nil); err != nil {
		return nil, err
	}
	if err := ch.ExchangeDeclare("trustgrid.dlx", "topic", true, false, false, false, nil); err != nil {
		return nil, err
	}

	// 2. Declare Dead-Letter Queue
	if _, err := ch.QueueDeclare("workflow.assessment.submitted.dlq", true, false, false, false, nil); err != nil {
		return nil, err
	}
	if err := ch.QueueBind("workflow.assessment.submitted.dlq", "vendor.assessment.submitted.v1", "trustgrid.dlx", false, nil); err != nil {
		return nil, err
	}

	// 3. Declare Main Consumer Queue with DLX routing
	args := amqp.Table{
		"x-dead-letter-exchange": "trustgrid.dlx",
	}
	q, err := ch.QueueDeclare("workflow.assessment.submitted", true, false, false, false, args)
	if err != nil {
		return nil, err
	}

	// 4. Bind queue to topic exchange
	if err := ch.QueueBind(q.Name, "vendor.assessment.submitted.v1", "trustgrid.events", false, nil); err != nil {
		return nil, err
	}

	return &AssessmentConsumer{conn: conn, ch: ch, repo: repo, db: db}, nil
}

func (c *AssessmentConsumer) Start(ctx context.Context) error {
	msgs, err := c.ch.Consume(
		"workflow.assessment.submitted",
		"workflow-service-consumer",
		false, // Manual Acknowledgements (autoAck = false)
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return err
	}

	log.Println("RabbitMQ Consumer started: listening on 'workflow.assessment.submitted'")

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case d, ok := <-msgs:
				if !ok {
					log.Println("RabbitMQ consumer channel closed.")
					return
				}
				c.handleDelivery(ctx, d)
			}
		}
	}()
	return nil
}

func (c *AssessmentConsumer) handleDelivery(ctx context.Context, d amqp.Delivery) {
	var env EventEnvelope
	if err := json.Unmarshal(d.Body, &env); err != nil {
		log.Printf("Invalid event envelope: %v. Rejecting to DLQ.", err)
		d.Nack(false, false) // Send to DLQ without requeue
		return
	}

	eventID, err := uuid.Parse(env.ID)
	if err != nil {
		log.Printf("Invalid event UUID: %v. Rejecting to DLQ.", err)
		d.Nack(false, false)
		return
	}

	tenantID, err := uuid.Parse(env.TenantID)
	if err != nil {
		log.Printf("Invalid tenant UUID: %v. Rejecting to DLQ.", err)
		d.Nack(false, false)
		return
	}

	// Consumer Idempotency Check in Transaction
	tx, err := c.db.BeginTx(ctx, nil)
	if err != nil {
		log.Printf("Failed to begin transaction: %v", err)
		d.Nack(false, true) // Requeue on transient DB failure
		return
	}
	defer tx.Rollback()

	// 1. Check if event was already processed
	var exists int
	err = tx.QueryRowContext(ctx, "SELECT 1 FROM processed_events WHERE event_id = $1", eventID).Scan(&exists)
	if err == nil {
		// Event already processed: Deduplicate immediately and ACK
		log.Printf("Duplicate event %s detected. Skipping processing.", eventID)
		tx.Rollback()
		d.Ack(false)
		return
	}

	// 2. Decode event payload
	var data AssessmentSubmittedData
	if err := json.Unmarshal(env.Data, &data); err != nil {
		log.Printf("Malformed event data: %v. Rejecting to DLQ.", err)
		d.Nack(false, false)
		return
	}

	assessmentID, err := uuid.Parse(data.AssessmentID)
	if err != nil {
		d.Nack(false, false)
		return
	}

	// 3. Create Workflow in IN_REVIEW status
	wf := &domain.Workflow{
		ID:           uuid.New(),
		TenantID:     tenantID,
		AssessmentID: assessmentID,
		CurrentState: domain.StateInReview,
		Version:      1,
		CreatedAt:    time.Now().UTC(),
		UpdatedAt:    time.Now().UTC(),
	}

	insertWfQuery := `
		INSERT INTO workflows (id, tenant_id, assessment_id, current_state, version, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)`
	_, err = tx.ExecContext(ctx, insertWfQuery, wf.ID, wf.TenantID, wf.AssessmentID, wf.CurrentState, wf.Version, wf.CreatedAt, wf.UpdatedAt)
	if err != nil {
		log.Printf("Failed to insert workflow: %v", err)
		d.Nack(false, true)
		return
	}

	// 4. Record event as processed
	_, err = tx.ExecContext(ctx, "INSERT INTO processed_events (event_id, event_type, processed_at) VALUES ($1, $2, NOW())", eventID, env.Type)
	if err != nil {
		log.Printf("Failed to record processed event: %v", err)
		d.Nack(false, true)
		return
	}

	if err := tx.Commit(); err != nil {
		log.Printf("Failed to commit transaction: %v", err)
		d.Nack(false, true)
		return
	}

	log.Printf("Successfully created workflow %s for assessment %s (Event: %s)", wf.ID, wf.AssessmentID, eventID)
	d.Ack(false)
}

func (c *AssessmentConsumer) Close() {
	if c.ch != nil {
		c.ch.Close()
	}
	if c.conn != nil {
		c.conn.Close()
	}
}
