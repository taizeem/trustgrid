package tests

import (
	"testing"

	"github.com/trustgrid/integrations-service/internal/security"
)

func TestSSRFValidatorBlocksRestrictedTargets(t *testing.T) {
	validator := security.NewSSRFValidator(false)

	blockedURLs := []string{
		"http://127.0.0.1:8080/admin",
		"http://0.0.0.0:8000/internal",
		"http://0.0.0.0/",
		"http://localhost:5432",
		"http://service.localhost/api",
		"http://host.internal/secrets",
		"http://server.local/debug",
		"http://10.0.0.5/secrets",
		"http://100.64.0.1/status",
		"http://172.16.0.10/metadata",
		"http://192.168.1.1/router",
		"http://169.254.169.254/latest/meta-data/",
		"http://192.0.2.1/test",
		"http://198.51.100.1/test",
		"http://203.0.113.1/test",
		"http://224.0.0.1/multicast",
		"http://[::1]:8080/",
		"http://[::]:8080/",
		"http://[fc00::1]/private",
		"http://[fe80::1]/link-local",
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

func TestSSRFValidatorAllowsPublicIPTargets(t *testing.T) {
	validator := security.NewSSRFValidator(false)

	// Test public IP literals directly to avoid DNS dependency in offline environments
	allowedURLs := []string{
		"https://93.184.216.34/webhook", // example.com IPv4
		"https://8.8.8.8:443/callback",  // Google Public DNS IPv4
		"http://1.1.1.1/event",          // Cloudflare Public DNS IPv4
	}

	for _, u := range allowedURLs {
		err := validator.ValidateURL(u)
		if err != nil {
			t.Errorf("Expected public IP URL to be permitted: %s, got error: %v", u, err)
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

	err = devValidator.ValidateURL("http://127.0.0.1:8000/test")
	if err != nil {
		t.Fatalf("Dev validator must allow loopback IP when AllowPrivate is true: %v", err)
	}
}
