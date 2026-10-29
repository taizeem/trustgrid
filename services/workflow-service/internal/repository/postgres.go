package repository

import (
	"context"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
	"github.com/trustgrid/workflow-service/internal/domain"
)

type PostgresRepository struct {
	db *sql.DB
}

func NewPostgresRepository(db *sql.DB) *PostgresRepository {
	return &PostgresRepository{db: db}
}

func (r *PostgresRepository) Create(ctx context.Context, wf *domain.Workflow) error {
	query := `
		INSERT INTO workflows (id, tenant_id, assessment_id, current_state, assigned_to_id, deadline, version, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`

	now := time.Now().UTC()
	wf.CreatedAt = now
	wf.UpdatedAt = now
	wf.Version = 1

	_, err := r.db.ExecContext(ctx, query,
		wf.ID, wf.TenantID, wf.AssessmentID, wf.CurrentState,
		wf.AssignedToID, wf.Deadline, wf.Version, wf.CreatedAt, wf.UpdatedAt,
	)
	return err
}

func (r *PostgresRepository) GetByID(ctx context.Context, tenantID, id uuid.UUID) (*domain.Workflow, error) {
	query := `
		SELECT id, tenant_id, assessment_id, current_state, assigned_to_id, deadline, version, created_at, updated_at
		FROM workflows
		WHERE tenant_id = $1 AND id = $2`

	wf := &domain.Workflow{}
	err := r.db.QueryRowContext(ctx, query, tenantID, id).Scan(
		&wf.ID, &wf.TenantID, &wf.AssessmentID, &wf.CurrentState,
		&wf.AssignedToID, &wf.Deadline, &wf.Version, &wf.CreatedAt, &wf.UpdatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, domain.ErrWorkflowNotFound
	}
	return wf, err
}

// TransitionWorkflow executes state updates and history recording atomically using Optimistic Locking.
func (r *PostgresRepository) TransitionWorkflow(
	ctx context.Context,
	tenantID, workflowID uuid.UUID,
	expectedVersion int,
	nextState domain.State,
	reassignTo *uuid.UUID,
	transition *domain.TransitionRecord,
) (*domain.Workflow, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()

	// 1. Optimistic Lock Update: only succeeds if version matches expectedVersion
	updateQuery := `
		UPDATE workflows
		SET current_state = $1,
		    assigned_to_id = COALESCE($2, assigned_to_id),
		    version = version + 1,
		    updated_at = NOW()
		WHERE id = $3 AND tenant_id = $4 AND version = $5
		RETURNING id, tenant_id, assessment_id, current_state, assigned_to_id, deadline, version, created_at, updated_at`

	updated := &domain.Workflow{}
	err = tx.QueryRowContext(ctx, updateQuery, nextState, reassignTo, workflowID, tenantID, expectedVersion).Scan(
		&updated.ID, &updated.TenantID, &updated.AssessmentID, &updated.CurrentState,
		&updated.AssignedToID, &updated.Deadline, &updated.Version, &updated.CreatedAt, &updated.UpdatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		// Version mismatch or workflow does not exist
		return nil, domain.ErrConcurrentModification
	}
	if err != nil {
		return nil, err
	}

	// 2. Insert audit transition record
	historyQuery := `
		INSERT INTO workflow_transitions (id, workflow_id, tenant_id, from_state, to_state, action, actor_id, comment, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())`

	transition.ID = uuid.New()
	transition.WorkflowID = workflowID
	transition.TenantID = tenantID

	_, err = tx.ExecContext(ctx, historyQuery,
		transition.ID, transition.WorkflowID, transition.TenantID,
		transition.FromState, transition.ToState, transition.Action,
		transition.ActorID, transition.Comment,
	)
	if err != nil {
		return nil, err
	}

	return updated, tx.Commit()
}
