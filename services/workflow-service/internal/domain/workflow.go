package domain

import (
	"time"

	"github.com/google/uuid"
)

type State string

const (
	StateDraft            State = "DRAFT"
	StateInReview         State = "IN_REVIEW"
	StateChangesRequested State = "CHANGES_REQUESTED"
	StateApproved         State = "APPROVED"
	StateRejected         State = "REJECTED"
)

type Action string

const (
	ActionSubmit         Action = "submit"
	ActionApprove        Action = "approve"
	ActionReject         Action = "reject"
	ActionRequestChanges Action = "request_changes"
	ActionReassign       Action = "reassign"
)

type Workflow struct {
	ID           uuid.UUID  `json:"id"`
	TenantID     uuid.UUID  `json:"tenant_id"`
	AssessmentID uuid.UUID  `json:"assessment_id"`
	CurrentState State      `json:"current_state"`
	AssignedToID *uuid.UUID `json:"assigned_to_id,omitempty"`
	Deadline     *time.Time `json:"deadline,omitempty"`
	Version      int        `json:"version"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
}

type TransitionRecord struct {
	ID         uuid.UUID `json:"id"`
	WorkflowID uuid.UUID `json:"workflow_id"`
	TenantID   uuid.UUID `json:"tenant_id"`
	FromState  State     `json:"from_state"`
	ToState    State     `json:"to_state"`
	Action     Action    `json:"action"`
	ActorID    uuid.UUID `json:"actor_id"`
	Comment    string    `json:"comment"`
	CreatedAt  time.Time `json:"created_at"`
}

// NextState evaluates the deterministic state machine rules.
func NextState(current State, action Action) (State, error) {
	switch current {
	case StateDraft:
		if action == ActionSubmit {
			return StateInReview, nil
		}
	case StateInReview:
		switch action {
		case ActionApprove:
			return StateApproved, nil
		case ActionReject:
			return StateRejected, nil
		case ActionRequestChanges:
			return StateChangesRequested, nil
		case ActionReassign:
			return StateInReview, nil
		}
	case StateChangesRequested:
		if action == ActionSubmit {
			return StateInReview, nil
		}
	case StateApproved, StateRejected:
		return "", ErrInvalidTransition // Terminal states cannot be transitioned
	}
	return "", ErrInvalidTransition
}
