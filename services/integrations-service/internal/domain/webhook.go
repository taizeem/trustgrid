package domain

import (
	"time"

	"github.com/google/uuid"
)

type Webhook struct {
	ID         uuid.UUID `json:"id"`
	TenantID   uuid.UUID `json:"tenant_id"`
	TargetURL  string    `json:"target_url"`
	Secret     string    `json:"-"` // Never expose shared secret in JSON responses
	EventTypes []string  `json:"event_types"`
	IsActive   bool      `json:"is_active"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

type DeliveryAttempt struct {
	ID           uuid.UUID `json:"id"`
	WebhookID    uuid.UUID `json:"webhook_id"`
	TenantID     uuid.UUID `json:"tenant_id"`
	EventType    string    `json:"event_type"`
	StatusCode   int       `json:"status_code"`
	ResponseBody string    `json:"response_body"`
	DurationMs   int64     `json:"duration_ms"`
	Error        string    `json:"error,omitempty"`
	DeliveredAt  time.Time `json:"delivered_at"`
}

type WebhookEventPayload struct {
	EventID   uuid.UUID      `json:"event_id"`
	EventType string         `json:"event_type"`
	Timestamp int64          `json:"timestamp"`
	TenantID  uuid.UUID      `json:"tenant_id"`
	Data      map[string]any `json:"data"`
}

type CreateWebhookRequest struct {
	TargetURL  string   `json:"target_url"`
	Secret     string   `json:"secret,omitempty"`
	EventTypes []string `json:"event_types"`
}

type TestWebhookRequest struct {
	EventType string         `json:"event_type"`
	Data      map[string]any `json:"data,omitempty"`
}
