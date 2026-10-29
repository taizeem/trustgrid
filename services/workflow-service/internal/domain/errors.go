package domain

import "errors"

var (
	ErrWorkflowNotFound       = errors.New("workflow not found")
	ErrInvalidTransition      = errors.New("invalid state transition")
	ErrConcurrentModification = errors.New("workflow was modified by another transaction; please refresh")
	ErrUnauthorized           = errors.New("unauthorized tenant context")
	ErrInvalidInput           = errors.New("invalid input data")
)
