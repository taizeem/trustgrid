package domain

import "errors"

var (
	ErrUnauthorized    = errors.New("unauthorized request")
	ErrWebhookNotFound = errors.New("webhook subscription not found")
	ErrInvalidURL      = errors.New("invalid webhook destination URL")
	ErrSSRFBlocked     = errors.New("destination URL resolved to private or restricted network address (SSRF blocked)")
	ErrDeliveryFailed  = errors.New("webhook delivery failed")
	ErrInvalidSecret   = errors.New("invalid signing secret")
)
