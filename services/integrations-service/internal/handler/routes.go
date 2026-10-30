package handler

import (
	"net/http"

	"github.com/trustgrid/integrations-service/internal/auth"
)

func RegisterRoutes(h *Handler) http.Handler {
	mux := http.NewServeMux()

	// Public Health
	mux.HandleFunc("GET /health", h.Health)

	// Protected Webhooks API
	protectedMux := http.NewServeMux()
	protectedMux.HandleFunc("POST /api/v1/integrations/webhooks", h.CreateWebhook)
	protectedMux.HandleFunc("GET /api/v1/integrations/webhooks", h.ListWebhooks)
	protectedMux.HandleFunc("DELETE /api/v1/integrations/webhooks/{id}", h.DeleteWebhook)
	protectedMux.HandleFunc("GET /api/v1/integrations/webhooks/{id}/deliveries", h.ListDeliveries)
	protectedMux.HandleFunc("POST /api/v1/integrations/webhooks/{id}/test", h.TestWebhook)

	mux.Handle("/api/v1/integrations/", auth.AuthMiddleware(protectedMux))

	return mux
}
