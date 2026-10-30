package tests

import (
	"testing"

	"github.com/trustgrid/integrations-service/internal/security"
)

func TestSSRFValidatorBlocksRestrictedTargets(t *testing.T) {
	validator := security.NewSSRFValidator(false)

	blockedURLs := []string{
		"http://127.0.0.1:8080/admin",
		"http://localhost:5432",
		"http://10.0.0.5/secrets",
		"http://172.16.0.10/metadata",
		"http://192.168.1.1/router",
		"http://169.254.169.254/latest/meta-data/",
		"http://[::1]:8080/",
		"ftp://example.com/file",
		"file:///etc/passwd",
		"gopher://127.0.0.1:70",
	}

	for _, u := range blockedURLs {
		err := validator.ValidateURL(u)
		if err == nil {
			t.Errorf("Expected URL to be blocked: %s", u)
		}
	}
}

func TestSSRFValidatorAllowsPublicTargets(t *testing.T) {
	validator := security.NewSSRFValidator(false)

	allowedURLs := []string{
		"https://api.github.com/webhook",
		"https://hooks.slack.com/services/T00/B00/X00",
		"http://example.com/callback",
	}

	for _, u := range allowedURLs {
		err := validator.ValidateURL(u)
		if err != nil {
			t.Errorf("Expected public URL to be permitted: %s, got error: %v", u, err)
		}
	}
}

func TestSSRFValidatorAllowsPrivateWhenConfigured(t *testing.T) {
	// In dev mode with AllowPrivate = true
	devValidator := security.NewSSRFValidator(true)

	err := devValidator.ValidateURL("http://localhost:8080/callback")
	if err != nil {
		t.Fatalf("Dev validator must allow local URLs when AllowPrivate is true: %v", err)
	}
}
