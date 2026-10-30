package handler

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/trustgrid/integrations-service/internal/auth"
	"github.com/trustgrid/integrations-service/internal/domain"
	"github.com/trustgrid/integrations-service/internal/repository"
	"github.com/trustgrid/integrations-service/internal/security"
	"github.com/trustgrid/integrations-service/internal/worker"
)

type Handler struct {
	repo       *repository.Repository
	dispatcher *worker.Dispatcher
	validator  *security.SSRFValidator
}

func NewHandler(repo *repository.Repository, dispatcher *worker.Dispatcher, validator *security.SSRFValidator) *Handler {
	return &Handler{
		repo:       repo,
		dispatcher: dispatcher,
		validator:  validator,
	}
}

func extractWebhookID(r *http.Request) (uuid.UUID, error) {
	idStr := r.PathValue("id")
	if idStr == "" {
		parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
		if len(parts) >= 5 {
			idStr = parts[4]
		}
	}
	return uuid.Parse(idStr)
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"healthy","service":"integrations-service"}`))
}

func (h *Handler) CreateWebhook(w http.ResponseWriter, r *http.Request) {
	authCtx, ok := auth.GetAuthContext(r.Context())
	if !ok {
		http.Error(w, `{"error":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	var req domain.CreateWebhookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"Invalid request payload"}`, http.StatusBadRequest)
		return
	}

	if err := h.validator.ValidateURL(req.TargetURL); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	if len(req.EventTypes) == 0 {
		req.EventTypes = []string{"*"}
	}

	secret := req.Secret
	if secret == "" {
		b := make([]byte, 32)
		_, _ = rand.Read(b)
		secret = hex.EncodeToString(b)
	}

	webhook := &domain.Webhook{
		ID:         uuid.New(),
		TenantID:   authCtx.TenantID,
		TargetURL:  req.TargetURL,
		Secret:     secret,
		EventTypes: req.EventTypes,
		IsActive:   true,
	}

	if err := h.repo.CreateWebhook(r.Context(), webhook); err != nil {
		http.Error(w, `{"error":"Failed to create webhook subscription"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"id":          webhook.ID,
		"tenant_id":   webhook.TenantID,
		"target_url":  webhook.TargetURL,
		"secret":      secret, // Reveal secret only upon initial creation
		"event_types": webhook.EventTypes,
		"is_active":   webhook.IsActive,
		"created_at":  webhook.CreatedAt,
	})
}

func (h *Handler) ListWebhooks(w http.ResponseWriter, r *http.Request) {
	authCtx, ok := auth.GetAuthContext(r.Context())
	if !ok {
		http.Error(w, `{"error":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	webhooks, err := h.repo.ListWebhooks(r.Context(), authCtx.TenantID)
	if err != nil {
		http.Error(w, `{"error":"Failed to list webhooks"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(webhooks)
}

func (h *Handler) DeleteWebhook(w http.ResponseWriter, r *http.Request) {
	authCtx, ok := auth.GetAuthContext(r.Context())
	if !ok {
		http.Error(w, `{"error":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	webhookID, err := extractWebhookID(r)
	if err != nil {
		http.Error(w, `{"error":"Invalid webhook ID format"}`, http.StatusBadRequest)
		return
	}

	if err := h.repo.DeleteWebhook(r.Context(), authCtx.TenantID, webhookID); err != nil {
		http.Error(w, `{"error":"Webhook not found or delete failed"}`, http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) ListDeliveries(w http.ResponseWriter, r *http.Request) {
	authCtx, ok := auth.GetAuthContext(r.Context())
	if !ok {
		http.Error(w, `{"error":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	webhookID, err := extractWebhookID(r)
	if err != nil {
		http.Error(w, `{"error":"Invalid webhook ID format"}`, http.StatusBadRequest)
		return
	}

	deliveries, err := h.repo.ListDeliveries(r.Context(), authCtx.TenantID, webhookID, 50)
	if err != nil {
		http.Error(w, `{"error":"Failed to retrieve delivery history"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(deliveries)
}

func (h *Handler) TestWebhook(w http.ResponseWriter, r *http.Request) {
	authCtx, ok := auth.GetAuthContext(r.Context())
	if !ok {
		http.Error(w, `{"error":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	webhookID, err := extractWebhookID(r)
	if err != nil {
		http.Error(w, `{"error":"Invalid webhook ID format"}`, http.StatusBadRequest)
		return
	}

	webhook, err := h.repo.GetWebhook(r.Context(), authCtx.TenantID, webhookID)
	if err != nil {
		http.Error(w, `{"error":"Webhook not found"}`, http.StatusNotFound)
		return
	}

	event := &domain.WebhookEventPayload{
		EventID:   uuid.New(),
		EventType: "ping.test",
		Timestamp: time.Now().UTC().Unix(),
		TenantID:  authCtx.TenantID,
		Data: map[string]any{
			"message": "TrustGrid webhook delivery test ping",
			"test":    true,
		},
	}

	attempt, _ := h.dispatcher.Deliver(r.Context(), webhook, event)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(attempt)
}
