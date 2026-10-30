package handler

import (
	"net/http"

	"github.com/trustgrid/integrations-service/internal/auth"
)

func RegisterRoutes(h *Handler) http.Handler {
	mux := http.NewServeMux()

	// Public Health Check
	mux.HandleFunc("GET /health", h.Health)

	// Protected Webhook Routes registered directly with auth.AuthMiddleware
	mux.Handle("POST /api/v1/integrations/webhooks", auth.AuthMiddleware(http.HandlerFunc(h.CreateWebhook)))
	mux.Handle("GET /api/v1/integrations/webhooks", auth.AuthMiddleware(http.HandlerFunc(h.ListWebhooks)))
	mux.Handle("DELETE /api/v1/integrations/webhooks/{id}", auth.AuthMiddleware(http.HandlerFunc(h.DeleteWebhook)))
	mux.Handle("GET /api/v1/integrations/webhooks/{id}/deliveries", auth.AuthMiddleware(http.HandlerFunc(h.ListDeliveries)))
	mux.Handle("POST /api/v1/integrations/webhooks/{id}/test", auth.AuthMiddleware(http.HandlerFunc(h.TestWebhook)))

	return mux
}
