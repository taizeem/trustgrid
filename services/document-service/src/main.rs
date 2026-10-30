use std::net::SocketAddr;
use axum::{
    extract::{DefaultBodyLimit, Extension},
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
use validator::MAX_FILE_SIZE;

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

    // 2. Initialize tables safely (split on semicolons to avoid extended query protocol errors)
    let schema_sql = include_str!("../migrations/0001_create_documents.sql");
    for statement in schema_sql.split(';') {
        let stmt = statement.trim();
        if !stmt.is_empty() {
            sqlx::query(stmt).execute(&pool).await?;
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
        .layer(DefaultBodyLimit::max(MAX_FILE_SIZE))
        .layer(TraceLayer::new_for_http())
        .layer(Extension(state));

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.port));
    tracing::info!("Document Service listening on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}