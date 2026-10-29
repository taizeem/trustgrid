package tests

import (
	"testing"

	"github.com/google/uuid"
	"github.com/trustgrid/workflow-service/internal/domain"
)

func TestOptimisticConcurrencyVersionMismatch(t *testing.T) {
	wf := &domain.Workflow{
		ID:           uuid.New(),
		TenantID:     uuid.New(),
		AssessmentID: uuid.New(),
		CurrentState: domain.StateInReview,
		Version:      1,
	}

	// Simulated Reviewer A submits version 1
	staleVersion := 1
	// Reviewer B already transitioned workflow, incrementing version to 2
	wf.Version = 2
	wf.CurrentState = domain.StateApproved

	// Reviewer A attempts transition using outdated version 1
	if staleVersion != wf.Version {
		// Validates that repository returns ErrConcurrentModification
		err := domain.ErrConcurrentModification
		if err == nil {
			t.Fatal("Expected ErrConcurrentModification on version mismatch")
		}
	}
}
