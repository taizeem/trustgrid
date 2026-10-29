package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/lib/pq"
	"github.com/trustgrid/workflow-service/internal/auth"
	"github.com/trustgrid/workflow-service/internal/handler"
	"github.com/trustgrid/workflow-service/internal/repository"
)

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func main() {
	dbHost := getEnv("WORKFLOW_DB_HOST", "postgres")
	dbPort := getEnv("WORKFLOW_DB_PORT", "5432")
	dbUser := getEnv("WORKFLOW_DB_USER", "workflow_user")
	dbPass := getEnv("WORKFLOW_DB_PASSWORD", "workflow_secure_pass_dev")
	dbName := getEnv("WORKFLOW_DB_NAME", "trustgrid_workflow")
	jwtSecret := getEnv("JWT_SECRET_KEY", "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123")
	serverPort := getEnv("SERVER_PORT", "8003")

	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		dbHost, dbPort, dbUser, dbPass, dbName)

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatalf("Failed to open database connection: %v", err)
	}
	defer db.Close()

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	if err := db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}
	log.Println("Connected to PostgreSQL (trustgrid_workflow) successfully.")

	// Auto-initialize tables
	schemaSQL, err := os.ReadFile("internal/repository/schema.sql")
	if err == nil {
		if _, err := db.Exec(string(schemaSQL)); err != nil {
			log.Fatalf("Failed to execute database schema: %v", err)
		}
		log.Println("Database schema applied.")
	}

	repo := repository.NewPostgresRepository(db)
	h := handler.NewWorkflowHandler(repo)
	tokenValidator := auth.NewTokenValidator(jwtSecret)

	mux := http.NewServeMux()
	handler.RegisterRoutes(mux, h, tokenValidator)

	server := &http.Server{
		Addr:         ":" + serverPort,
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		log.Printf("Workflow Service listening on :%s", serverPort)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server ListenAndServe failed: %v", err)
		}
	}()

	// Graceful shutdown on SIGTERM / SIGINT
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down Workflow Service...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}
	log.Println("Workflow Service exited cleanly.")
}
