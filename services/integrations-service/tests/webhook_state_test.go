package tests

import (
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/trustgrid/integrations-service/internal/domain"
)

func TestWebhookModelValidation(t *testing.T) {
	tenantID := uuid.New()
	webhookID := uuid.New()

	w := domain.Webhook{
		ID:         webhookID,
		TenantID:   tenantID,
		TargetURL:  "https://compliance-monitor.example.com/alerts",
		Secret:     "super_secret_signing_key_32_bytes",
		EventTypes: []string{"assessment.completed", "workflow.approved"},
		IsActive:   true,
		CreatedAt:  time.Now().UTC(),
		UpdatedAt:  time.Now().UTC(),
	}

	if w.ID != webhookID || w.TenantID != tenantID {
		t.Fatalf("Webhook UUID initialization failed")
	}

	if len(w.EventTypes) != 2 {
		t.Fatalf("Expected 2 event types, got %d", len(w.EventTypes))
	}
}
