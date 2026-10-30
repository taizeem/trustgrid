use std::net::SocketAddr;
use axum::{
    routing::{get, post},
    Router,
};
use sqlx::postgres::PgPoolOptions;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod auth;
mod config;
mod error;
mod handlers;
mod models;
mod storage;
mod validator;

use config::AppConfig;
use handlers::{download_document, get_document_metadata, upload_document, AppState};
use storage::DiskStorage;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .with(tracing_subscriber::fmt::layer())
        .init();

    let cfg = AppConfig::from_env();

    // 1. Database Connection Pool
    let pool = PgPoolOptions::new()
        .max_connections(20)
        .connect(&cfg.database_url)
        .await?;
    tracing::info!("Connected to PostgreSQL (trustgrid_document).");

    // 2. Initialize tables (split multiple statements)
    let schema_sql = include_str!("../migrations/0001_create_documents.sql");
    for statement in schema_sql.split(';') {
        let trimmed = statement.trim();
        if !trimmed.is_empty() {
            sqlx::query(trimmed).execute(&pool).await?;
        }
    }
    tracing::info!("Applied database schema for documents.");

    // 3. Storage Backend
    let storage = DiskStorage::new(&cfg.storage_dir);
    let state = AppState { db: pool, storage };

    // 4. Routes
    let app = Router::new()
        .route("/health", get(|| async { r#"{"status":"healthy","service":"document-service"}"# }))
        .route("/api/v1/documents/upload", post(upload_document))
        .route("/api/v1/documents/:id", get(get_document_metadata))
        .route("/api/v1/documents/:id/download", get(download_document))
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.port));
    tracing::info!("Document Service listening on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}