-- Create the feeds table
CREATE TABLE IF NOT EXISTS feeds (
  id INTEGER PRIMARY KEY,

  title TEXT NOT NULL,
  description TEXT,

  feed_url TEXT NOT NULL UNIQUE,
  homepage_url TEXT,

  etag TEXT,
  last_modified TEXT,
  updated_at DATETIME,

  last_fetched DATETIME,
);

-- CREATE the entries table
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,

  feed_id INTEGER NOT NULL,

  guid TEXT NOT NULL,
  url TEXT NOT NULL,

  author TEXT,
  title TEXT NOT NULL,
  summary TEXT,
  content TEXT,

  published_at DATETIME,
  updated_at DATETIME,

  is_read BOOLEAN NOT NULL DEFAULT 0,
  is_favorite BOOLEAN NOT NULL DEFAULT 0,

  FOREIGN KEY (feed_id) REFERENCES feeds (id) ON DELETE CASCADE,

  UNIQUE(feed_id, guid),
  UNIQUE(feed_id, url)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entries_feed_id ON entries(feed_id);
