package main

import (
	"context"
	"database/sql"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/lib/pq"
	"github.com/trustgrid/integrations-service/internal/config"
	"github.com/trustgrid/integrations-service/internal/handler"
	"github.com/trustgrid/integrations-service/internal/repository"
	"github.com/trustgrid/integrations-service/internal/security"
	"github.com/trustgrid/integrations-service/internal/worker"
)

func main() {
	cfg := config.Load()

	db, err := sql.Open("postgres", cfg.DSN())
	if err != nil {
		log.Fatalf("Failed to open database connection: %v", err)
	}
	defer db.Close()

	db.SetMaxOpenConns(20)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(10 * time.Minute)

	// Wait for Postgres connection with retries
	for attempts := 1; attempts <= 15; attempts++ {
		err = db.Ping()
		if err == nil {
			break
		}
		log.Printf("Awaiting database (%s:%s)... attempt %d/15", cfg.DBHost, cfg.DBPort, attempts)
		time.Sleep(2 * time.Second)
	}
	if err != nil {
		log.Fatalf("Database connection failed after retries: %v", err)
	}
	log.Println("Connected to PostgreSQL (trustgrid_integrations).")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	repo := repository.NewRepository(db)
	if err := repo.InitSchema(ctx); err != nil {
		log.Fatalf("Failed to initialize schema: %v", err)
	}
	log.Println("Applied database schema for integrations.")

	validator := security.NewSSRFValidator(cfg.AllowInternalWebhooks)
	dispatcher := worker.NewDispatcher(repo, validator)
	h := handler.NewHandler(repo, dispatcher, validator)
	router := handler.RegisterRoutes(h)

	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		log.Printf("Integrations Service listening on http://0.0.0.0:%s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down Integrations Service...")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("Server shutdown failed: %v", err)
	}
	log.Println("Integrations Service stopped gracefully.")
}
