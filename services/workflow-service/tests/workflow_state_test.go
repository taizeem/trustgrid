package tests

import (
	"testing"

	"github.com/trustgrid/workflow-service/internal/domain"
)

func TestStateTransitions(t *testing.T) {
	tests := []struct {
		name        string
		from        domain.State
		action      domain.Action
		expected    domain.State
		expectError bool
	}{
		{"Draft to InReview", domain.StateDraft, domain.ActionSubmit, domain.StateInReview, false},
		{"InReview to Approved", domain.StateInReview, domain.ActionApprove, domain.StateApproved, false},
		{"InReview to Rejected", domain.StateInReview, domain.ActionReject, domain.StateRejected, false},
		{"InReview to ChangesRequested", domain.StateInReview, domain.ActionRequestChanges, domain.StateChangesRequested, false},
		{"ChangesRequested to InReview", domain.StateChangesRequested, domain.ActionSubmit, domain.StateInReview, false},
		{"Illegal: Draft directly to Approved", domain.StateDraft, domain.ActionApprove, "", true},
		{"Illegal: Approved to InReview", domain.StateApproved, domain.ActionSubmit, "", true},
		{"Illegal: Rejected to Approved", domain.StateRejected, domain.ActionApprove, "", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := domain.NextState(tt.from, tt.action)
			if (err != nil) != tt.expectError {
				t.Fatalf("NextState(%s, %s) error = %v, expectError = %v", tt.from, tt.action, err, tt.expectError)
			}
			if !tt.expectError && got != tt.expected {
				t.Fatalf("NextState(%s, %s) = %s, expected %s", tt.from, tt.action, got, tt.expected)
			}
		})
	}
}
