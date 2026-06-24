use crate::constants::APP_NAME;
use color_eyre::eyre::Result;
use serde::{Deserialize, Serialize};

/// Main configuration structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    /// SQLite connection URI.
    #[serde(default = "default_db_uri")]
    pub db_uri: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            db_uri: default_db_uri(),
        }
    }
}

impl Config {
    pub fn load() -> Result<Self> {
        let _ = dotenvy::dotenv();
        let mut config = Config::default();

        if let Ok(uri) = dotenvy::var("DATABASE_URL") {
            config.db_uri = uri;
        }

        Ok(config)
    }
}

fn default_db_uri() -> String {
    let path = dirs::config_dir()
        .unwrap_or_default()
        .join(APP_NAME)
        .join("db.sqlite3");
    format!("sqlite://{}", path.display())
}
