package security

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strconv"
)

func ComputeSignature(secret string, timestamp int64, payload []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(strconv.FormatInt(timestamp, 10)))
	mac.Write([]byte("."))
	mac.Write(payload)
	return fmt.Sprintf("sha256=%s", hex.EncodeToString(mac.Sum(nil)))
}

func VerifySignature(secret string, timestamp int64, payload []byte, providedSig string) bool {
	expectedSig := ComputeSignature(secret, timestamp, payload)
	return hmac.Equal([]byte(expectedSig), []byte(providedSig))
}
