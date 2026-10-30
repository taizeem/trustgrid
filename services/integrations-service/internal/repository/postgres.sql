package repository

import (
	"context"
	"database/sql"
	_ "embed"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
	"github.com/trustgrid/integrations-service/internal/domain"
)

//go:embed schema.sql
var SchemaSQL string

type Repository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

func (r *Repository) InitSchema(ctx context.Context) error {
	_, err := r.db.ExecContext(ctx, SchemaSQL)
	return err
}

func (r *Repository) CreateWebhook(ctx context.Context, w *domain.Webhook) error {
	query := `
		INSERT INTO webhooks (id, tenant_id, target_url, secret, event_types, is_active, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	now := time.Now().UTC()
	w.CreatedAt = now
	w.UpdatedAt = now

	_, err := r.db.ExecContext(ctx, query,
		w.ID, w.TenantID, w.TargetURL, w.Secret, pq.Array(w.EventTypes), w.IsActive, w.CreatedAt, w.UpdatedAt,
	)
	if err != nil {
		return fmt.Errorf("failed to insert webhook: %w", err)
	}
	return nil
}

func (r *Repository) GetWebhook(ctx context.Context, tenantID, id uuid.UUID) (*domain.Webhook, error) {
	query := `
		SELECT id, tenant_id, target_url, secret, event_types, is_active, created_at, updated_at
		FROM webhooks
		WHERE id = $1 AND tenant_id = $2
	`
	var w domain.Webhook
	err := r.db.QueryRowContext(ctx, query, id, tenantID).Scan(
		&w.ID, &w.TenantID, &w.TargetURL, &w.Secret, pq.Array(&w.EventTypes), &w.IsActive, &w.CreatedAt, &w.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, domain.ErrWebhookNotFound
		}
		return nil, fmt.Errorf("failed to query webhook: %w", err)
	}
	return &w, nil
}

func (r *Repository) ListWebhooks(ctx context.Context, tenantID uuid.UUID) ([]domain.Webhook, error) {
	query := `
		SELECT id, tenant_id, target_url, secret, event_types, is_active, created_at, updated_at
		FROM webhooks
		WHERE tenant_id = $1
		ORDER BY created_at DESC
	`
	rows, err := r.db.QueryContext(ctx, query, tenantID)
	if err != nil {
		return nil, fmt.Errorf("failed to list webhooks: %w", err)
	}
	defer rows.Close()

	var webhooks []domain.Webhook
	for rows.Next() {
		var w domain.Webhook
		if err := rows.Scan(
			&w.ID, &w.TenantID, &w.TargetURL, &w.Secret, pq.Array(&w.EventTypes), &w.IsActive, &w.CreatedAt, &w.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("failed to scan webhook row: %w", err)
		}
		webhooks = append(webhooks, w)
	}
	if webhooks == nil {
		webhooks = []domain.Webhook{}
	}
	return webhooks, nil
}

func (r *Repository) ListActiveWebhooksForEvent(ctx context.Context, tenantID uuid.UUID, eventType string) ([]domain.Webhook, error) {
	query := `
		SELECT id, tenant_id, target_url, secret, event_types, is_active, created_at, updated_at
		FROM webhooks
		WHERE tenant_id = $1 AND is_active = true AND ($2 = ANY(event_types) OR '*' = ANY(event_types))
	`
	rows, err := r.db.QueryContext(ctx, query, tenantID, eventType)
	if err != nil {
		return nil, fmt.Errorf("failed to query active webhooks: %w", err)
	}
	defer rows.Close()

	var webhooks []domain.Webhook
	for rows.Next() {
		var w domain.Webhook
		if err := rows.Scan(
			&w.ID, &w.TenantID, &w.TargetURL, &w.Secret, pq.Array(&w.EventTypes), &w.IsActive, &w.CreatedAt, &w.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("failed to scan active webhook row: %w", err)
		}
		webhooks = append(webhooks, w)
	}
	return webhooks, nil
}

func (r *Repository) DeleteWebhook(ctx context.Context, tenantID, id uuid.UUID) error {
	query := `DELETE FROM webhooks WHERE id = $1 AND tenant_id = $2`
	res, err := r.db.ExecContext(ctx, query, id, tenantID)
	if err != nil {
		return fmt.Errorf("failed to delete webhook: %w", err)
	}
	rows, _ := res.RowsAffected()
	if rows == 0 {
		return domain.ErrWebhookNotFound
	}
	return nil
}

func (r *Repository) RecordDelivery(ctx context.Context, d *domain.DeliveryAttempt) error {
	query := `
		INSERT INTO webhook_deliveries (id, webhook_id, tenant_id, event_type, status_code, response_body, duration_ms, error_message, delivered_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`
	_, err := r.db.ExecContext(ctx, query,
		d.ID, d.WebhookID, d.TenantID, d.EventType, d.StatusCode, d.ResponseBody, d.DurationMs, d.Error, d.DeliveredAt,
	)
	if err != nil {
		return fmt.Errorf("failed to insert delivery attempt: %w", err)
	}
	return nil
}

func (r *Repository) ListDeliveries(ctx context.Context, tenantID, webhookID uuid.UUID, limit int) ([]domain.DeliveryAttempt, error) {
	if limit <= 0 || limit > 100 {
		limit = 50
	}
	query := `
		SELECT id, webhook_id, tenant_id, event_type, status_code, response_body, duration_ms, COALESCE(error_message, ''), delivered_at
		FROM webhook_deliveries
		WHERE tenant_id = $1 AND webhook_id = $2
		ORDER BY delivered_at DESC
		LIMIT $3
	`
	rows, err := r.db.QueryContext(ctx, query, tenantID, webhookID, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list deliveries: %w", err)
	}
	defer rows.Close()

	var deliveries []domain.DeliveryAttempt
	for rows.Next() {
		var d domain.DeliveryAttempt
		if err := rows.Scan(
			&d.ID, &d.WebhookID, &d.TenantID, &d.EventType, &d.StatusCode, &d.ResponseBody, &d.DurationMs, &d.Error, &d.DeliveredAt,
		); err != nil {
			return nil, fmt.Errorf("failed to scan delivery row: %w", err)
		}
		deliveries = append(deliveries, d)
	}
	if deliveries == nil {
		deliveries = []domain.DeliveryAttempt{}
	}
	return deliveries, nil
}