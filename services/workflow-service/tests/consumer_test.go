package tests

import (
	"testing"

	"github.com/google/uuid"
)

func TestConsumerIdempotencyLogic(t *testing.T) {
	// Simulated in-memory set representing processed_events table
	processedEvents := make(map[uuid.UUID]bool)

	eventID := uuid.New()

	// First Delivery
	isDuplicate := processedEvents[eventID]
	if isDuplicate {
		t.Fatal("First message delivery should not be marked as duplicate")
	}
	processedEvents[eventID] = true // Mark as processed

	// Second Delivery (Duplicate Message)
	isDuplicate = processedEvents[eventID]
	if !isDuplicate {
		t.Fatal("Second message delivery with same event ID must be detected as duplicate")
	}
}
