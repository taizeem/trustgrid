package worker

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"

	"github.com/google/uuid"
	"github.com/trustgrid/integrations-service/internal/domain"
	"github.com/trustgrid/integrations-service/internal/repository"
	"github.com/trustgrid/integrations-service/internal/security"
)

type Dispatcher struct {
	repo       *repository.Repository
	validator  *security.SSRFValidator
	httpClient *http.Client
}

func NewDispatcher(repo *repository.Repository, validator *security.SSRFValidator) *Dispatcher {
	client := &http.Client{
		Timeout: 10 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 3 {
				return fmt.Errorf("stopped after 3 redirects")
			}
			return validator.ValidateURL(req.URL.String())
		},
	}

	return &Dispatcher{
		repo:       repo,
		validator:  validator,
		httpClient: client,
	}
}

func (d *Dispatcher) Deliver(ctx context.Context, w *domain.Webhook, event *domain.WebhookEventPayload) (*domain.DeliveryAttempt, error) {
	if err := d.validator.ValidateURL(w.TargetURL); err != nil {
		attempt := &domain.DeliveryAttempt{
			ID:          uuid.New(),
			WebhookID:   w.ID,
			TenantID:    w.TenantID,
			EventType:   event.EventType,
			StatusCode:  0,
			DurationMs:  0,
			Error:       err.Error(),
			DeliveredAt: time.Now().UTC(),
		}
		_ = d.repo.RecordDelivery(ctx, attempt)
		return attempt, err
	}

	payloadBytes, err := json.Marshal(event)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal event: %w", err)
	}

	deliveryID := uuid.New()
	timestamp := time.Now().UTC().Unix()
	signature := security.ComputeSignature(w.Secret, timestamp, payloadBytes)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, w.TargetURL, bytes.NewReader(payloadBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "TrustGrid-Webhook-Delivery/1.0")
	req.Header.Set("X-TrustGrid-Signature", signature)
	req.Header.Set("X-TrustGrid-Timestamp", strconv.FormatInt(timestamp, 10))
	req.Header.Set("X-TrustGrid-Event-ID", event.EventID.String())
	req.Header.Set("X-TrustGrid-Delivery-ID", deliveryID.String())
	req.Header.Set("X-TrustGrid-Tenant-ID", w.TenantID.String())

	start := time.Now()
	resp, reqErr := d.httpClient.Do(req)
	duration := time.Since(start).Milliseconds()

	attempt := &domain.DeliveryAttempt{
		ID:          deliveryID,
		WebhookID:   w.ID,
		TenantID:    w.TenantID,
		EventType:   event.EventType,
		DurationMs:  duration,
		DeliveredAt: time.Now().UTC(),
	}

	if reqErr != nil {
		attempt.StatusCode = 0
		attempt.Error = reqErr.Error()
	} else {
		defer resp.Body.Close()
		attempt.StatusCode = resp.StatusCode
		bodyBytes, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		attempt.ResponseBody = string(bodyBytes)
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			attempt.Error = fmt.Sprintf("destination returned non-2xx status: %d", resp.StatusCode)
		}
	}

	_ = d.repo.RecordDelivery(ctx, attempt)
	return attempt, reqErr
}

func (d *Dispatcher) DispatchEventAsync(tenantID uuid.UUID, eventType string, data map[string]any) {
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		webhooks, err := d.repo.ListActiveWebhooksForEvent(ctx, tenantID, eventType)
		if err != nil || len(webhooks) == 0 {
			return
		}

		eventPayload := &domain.WebhookEventPayload{
			EventID:   uuid.New(),
			EventType: eventType,
			Timestamp: time.Now().UTC().Unix(),
			TenantID:  tenantID,
			Data:      data,
		}

		for _, w := range webhooks {
			wCopy := w
			_, _ = d.Deliver(ctx, &wCopy, eventPayload)
		}
	}()
}
