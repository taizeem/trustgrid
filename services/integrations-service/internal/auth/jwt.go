package auth

import (
	"context"
	"errors"
	"net/http"
	"os"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type contextKey string

const AuthContextKey contextKey = "auth_context"

type AuthContext struct {
	UserID   uuid.UUID
	TenantID uuid.UUID
}

func AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
			http.Error(w, `{"error":"Missing or invalid Authorization header"}`, http.StatusUnauthorized)
			return
		}

		tokenStr := strings.TrimPrefix(authHeader, "Bearer ")
		secret := os.Getenv("JWT_SECRET_KEY")
		if secret == "" {
			secret = "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"
		}

		token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, errors.New("unexpected signing method")
			}
			return []byte(secret), nil
		}, jwt.WithAudience("trustgrid-services"))

		if err != nil || !token.Valid {
			http.Error(w, `{"error":"Invalid access token"}`, http.StatusUnauthorized)
			return
		}

		claims, ok := token.Claims.(jwt.MapClaims)
		if !ok {
			http.Error(w, `{"error":"Invalid token claims"}`, http.StatusUnauthorized)
			return
		}

		subStr, ok := claims["sub"].(string)
		if !ok {
			http.Error(w, `{"error":"Token missing sub claim"}`, http.StatusUnauthorized)
			return
		}
		userID, err := uuid.Parse(subStr)
		if err != nil {
			http.Error(w, `{"error":"Invalid user ID in token"}`, http.StatusUnauthorized)
			return
		}

		tidStr, ok := claims["tid"].(string)
		if !ok {
			http.Error(w, `{"error":"Token missing tenant ID (tid) claim"}`, http.StatusUnauthorized)
			return
		}
		tenantID, err := uuid.Parse(tidStr)
		if err != nil {
			http.Error(w, `{"error":"Invalid tenant ID in token"}`, http.StatusUnauthorized)
			return
		}

		ctx := context.WithValue(r.Context(), AuthContextKey, &AuthContext{
			UserID:   userID,
			TenantID: tenantID,
		})

		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func GetAuthContext(ctx context.Context) (*AuthContext, bool) {
	val, ok := ctx.Value(AuthContextKey).(*AuthContext)
	return val, ok
}
