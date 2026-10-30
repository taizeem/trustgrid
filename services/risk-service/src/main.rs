use std::net::SocketAddr;
use axum::{
    routing::{get, post},
    Router,
};
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod auth;
mod config;
mod engine;
mod error;
mod handlers;

use config::AppConfig;
use handlers::{compute_risk, get_rule, health_check, list_rules};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .with(tracing_subscriber::fmt::layer())
        .init();

    let cfg = AppConfig::from_env();

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/api/v1/risk/compute", post(compute_risk))
        .route("/api/v1/risk/rules", get(list_rules))
        .route("/api/v1/risk/rules/:version", get(get_rule))
        .layer(TraceLayer::new_for_http());

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.port));
    tracing::info!("Risk Service listening on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}