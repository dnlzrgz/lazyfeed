use chrono::{DateTime, Utc};
use sqlx::prelude::FromRow;

#[derive(Debug, Clone, FromRow)]
pub struct Feed {
    pub id: i64,
    pub title: String,
    pub description: Option<String>,
    pub feed_url: String,
    pub homepage_url: Option<String>,
    pub etag: Option<String>,
    pub last_modified: Option<String>,
    pub updated_at: Option<DateTime<Utc>>,
    pub last_fetched: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, FromRow)]
pub struct Entry {
    pub id: i64,
    pub feed_id: i64,
    pub guid: String,
    pub url: String,
    pub author: Option<String>,
    pub title: String,
    pub summary: Option<String>,
    pub content: Option<String>,
    pub published_at: Option<DateTime<Utc>>,
    pub updated_at: Option<DateTime<Utc>>,
    pub is_read: bool,
    pub is_favorite: bool,
}
