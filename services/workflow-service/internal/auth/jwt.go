package auth

import (
	"context"
	"errors"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type contextKey string

const (
	TenantIDKey contextKey = "tenant_id"
	UserIDKey   contextKey = "user_id"
)

type Claims struct {
	TenantID string `json:"tid"`
	Email    string `json:"email"`
	jwt.RegisteredClaims
}

type TokenValidator struct {
	secretKey []byte
}

func NewTokenValidator(secretKey string) *TokenValidator {
	return &TokenValidator{secretKey: []byte(secretKey)}
}

func (tv *TokenValidator) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
			http.Error(w, `{"error":"missing or invalid authorization header"}`, http.StatusUnauthorized)
			return
		}

		tokenStr := strings.TrimPrefix(authHeader, "Bearer ")
		claims := &Claims{}

		token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
			if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, errors.New("unexpected signing method")
			}
			return tv.secretKey, nil
		})

		if err != nil || !token.Valid || claims.TenantID == "" {
			http.Error(w, `{"error":"invalid or expired token"}`, http.StatusForbidden)
			return
		}

		tenantUUID, err := uuid.Parse(claims.TenantID)
		if err != nil {
			http.Error(w, `{"error":"invalid tenant id in token"}`, http.StatusForbidden)
			return
		}

		userUUID, err := uuid.Parse(claims.Subject)
		if err != nil {
			http.Error(w, `{"error":"invalid user id in token"}`, http.StatusForbidden)
			return
		}

		ctx := context.WithValue(r.Context(), TenantIDKey, tenantUUID)
		ctx = context.WithValue(ctx, UserIDKey, userUUID)

		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
