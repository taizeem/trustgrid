package handler

import (
	"net/http"

	"github.com/trustgrid/workflow-service/internal/auth"
)

func RegisterRoutes(mux *http.ServeMux, h *WorkflowHandler, validator *auth.TokenValidator) {
	// Public Health Check
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","service":"workflow-service"}`))
	})

	// Protected Workflow Subtree
	protected := http.NewServeMux()
	protected.HandleFunc("POST /api/v1/workflows", h.Create)
	protected.HandleFunc("GET /api/v1/workflows/{id}", h.GetByID)
	protected.HandleFunc("POST /api/v1/workflows/{id}/transition", h.Transition)

	mux.Handle("/api/v1/workflows", validator.Middleware(protected))
	mux.Handle("/api/v1/workflows/", validator.Middleware(protected))
}
