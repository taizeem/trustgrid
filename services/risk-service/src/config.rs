#[derive(Clone)]
pub struct AppConfig {
    pub port: u16,
}

impl AppConfig {
    pub fn from_env() -> Self {
        Self {
            port: std::env::var("PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(8005),
        }
    }
}