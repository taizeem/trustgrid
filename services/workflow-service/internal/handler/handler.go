package handler

import (
	"encoding/json"
	"errors"
	"net/http"

	"github.com/google/uuid"
	"github.com/trustgrid/workflow-service/internal/auth"
	"github.com/trustgrid/workflow-service/internal/domain"
	"github.com/trustgrid/workflow-service/internal/repository"
)

type WorkflowHandler struct {
	repo *repository.PostgresRepository
}

func NewWorkflowHandler(repo *repository.PostgresRepository) *WorkflowHandler {
	return &WorkflowHandler{repo: repo}
}

type CreateWorkflowRequest struct {
	AssessmentID uuid.UUID  `json:"assessment_id"`
	AssignedToID *uuid.UUID `json:"assigned_to_id,omitempty"`
}

type TransitionRequest struct {
	Action     domain.Action `json:"action"`
	Version    int           `json:"version"`
	Comment    string        `json:"comment"`
	ReassignTo *uuid.UUID    `json:"reassign_to,omitempty"`
}

func (h *WorkflowHandler) Create(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Context().Value(auth.TenantIDKey).(uuid.UUID)

	var req CreateWorkflowRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request payload"}`, http.StatusBadRequest)
		return
	}

	wf := &domain.Workflow{
		ID:           uuid.New(),
		TenantID:     tenantID,
		AssessmentID: req.AssessmentID,
		CurrentState: domain.StateDraft,
		AssignedToID: req.AssignedToID,
	}

	if err := h.repo.Create(r.Context(), wf); err != nil {
		http.Error(w, `{"error":"failed to create workflow"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(wf)
}

func (h *WorkflowHandler) GetByID(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Context().Value(auth.TenantIDKey).(uuid.UUID)
	idStr := r.PathValue("id")
	wfID, err := uuid.Parse(idStr)
	if err != nil {
		http.Error(w, `{"error":"invalid workflow id"}`, http.StatusBadRequest)
		return
	}

	wf, err := h.repo.GetByID(r.Context(), tenantID, wfID)
	if errors.Is(err, domain.ErrWorkflowNotFound) {
		http.Error(w, `{"error":"workflow not found"}`, http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(wf)
}

func (h *WorkflowHandler) Transition(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Context().Value(auth.TenantIDKey).(uuid.UUID)
	actorID := r.Context().Value(auth.UserIDKey).(uuid.UUID)

	wfID, err := uuid.Parse(r.PathValue("id"))
	if err != nil {
		http.Error(w, `{"error":"invalid workflow id"}`, http.StatusBadRequest)
		return
	}

	var req TransitionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request payload"}`, http.StatusBadRequest)
		return
	}

	// 1. Fetch current workflow to evaluate state transition
	current, err := h.repo.GetByID(r.Context(), tenantID, wfID)
	if errors.Is(err, domain.ErrWorkflowNotFound) {
		http.Error(w, `{"error":"workflow not found"}`, http.StatusNotFound)
		return
	}

	// 2. Evaluate deterministic state transition
	nextState, err := domain.NextState(current.CurrentState, req.Action)
	if errors.Is(err, domain.ErrInvalidTransition) {
		http.Error(w, `{"error":"invalid state transition for current workflow state"}`, http.StatusBadRequest)
		return
	}

	// 3. Execute atomic transition with optimistic concurrency check
	transition := &domain.TransitionRecord{
		FromState: current.CurrentState,
		ToState:   nextState,
		Action:    req.Action,
		ActorID:   actorID,
		Comment:   req.Comment,
	}

	updated, err := h.repo.TransitionWorkflow(
		r.Context(),
		tenantID,
		wfID,
		req.Version,
		nextState,
		req.ReassignTo,
		transition,
	)
	if errors.Is(err, domain.ErrConcurrentModification) {
		http.Error(w, `{"error":"conflict: workflow has been modified by another operation"}`, http.StatusConflict)
		return
	} else if err != nil {
		http.Error(w, `{"error":"failed to execute workflow transition"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(updated)
}
