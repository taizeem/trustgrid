package tests

import (
	"testing"
	"time"

	"github.com/trustgrid/integrations-service/internal/security"
)

func TestHMACSignatureGenerationAndVerification(t *testing.T) {
	secret := "whsec_test_secret_key_12345"
	timestamp := time.Now().Unix()
	payload := []byte(`{"event":"vendor.created","id":"550e8400-e29b-41d4-a716-446655440000"}`)

	sig := security.ComputeSignature(secret, timestamp, payload)
	if len(sig) < 10 || sig[:7] != "sha256=" {
		t.Fatalf("Expected signature with prefix sha256=, got %s", sig)
	}

	// Authentic verification
	if !security.VerifySignature(secret, timestamp, payload, sig) {
		t.Fatalf("Expected valid signature to verify successfully")
	}

	// Tampered payload verification failure
	tamperedPayload := []byte(`{"event":"vendor.created","id":"550e8400-e29b-41d4-a716-446655440001"}`)
	if security.VerifySignature(secret, timestamp, tamperedPayload, sig) {
		t.Fatalf("Tampered payload must fail signature verification")
	}

	// Incorrect secret verification failure
	if security.VerifySignature("wrong_secret", timestamp, payload, sig) {
		t.Fatalf("Wrong secret must fail signature verification")
	}
}
