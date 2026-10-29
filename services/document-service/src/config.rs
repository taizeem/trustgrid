#[derive(Clone)]
pub struct AppConfig {
    pub database_url: String,
    pub storage_dir: String,
    pub port: u16,
}

impl AppConfig {
    pub fn from_env() -> Self {
        Self {
            database_url: std::env::var("DATABASE_URL")
                .unwrap_or_else(|_| "postgres://doc_user:doc_secure_pass_dev@postgres:5432/trustgrid_document".into()),
            storage_dir: std::env::var("STORAGE_DIR").unwrap_or_else(|_| "/data/documents".into()),
            port: std::env::var("PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(8004),
        }
    }
}