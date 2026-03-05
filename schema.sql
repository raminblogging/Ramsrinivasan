-- Run this once with:
-- wrangler d1 execute ramsrinivasan-db --remote --file=schema.sql

CREATE TABLE IF NOT EXISTS blogs (
  id             TEXT PRIMARY KEY,
  title          TEXT NOT NULL,
  slug           TEXT NOT NULL UNIQUE,
  description    TEXT DEFAULT '',
  content        TEXT DEFAULT '',
  tags           TEXT DEFAULT '[]',
  featured_image TEXT DEFAULT '',
  status         TEXT DEFAULT 'draft',
  publish_date   TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  custom_url     TEXT DEFAULT '',
  sort_order     INTEGER DEFAULT 0,
  ga_id          TEXT DEFAULT 'G-ZH170NH9GW'
);

CREATE INDEX IF NOT EXISTS idx_blogs_slug       ON blogs(slug);
CREATE INDEX IF NOT EXISTS idx_blogs_status     ON blogs(status);
CREATE INDEX IF NOT EXISTS idx_blogs_sort_order ON blogs(sort_order);

CREATE TABLE IF NOT EXISTS messages (
  id         TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  email      TEXT NOT NULL,
  message    TEXT DEFAULT '',
  type       TEXT DEFAULT 'contact',
  status     TEXT DEFAULT 'unread',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);

-- ── If you ALREADY ran the old schema, run these two migration commands: ──
-- wrangler d1 execute ramsrinivasan-db --remote --command="ALTER TABLE blogs ADD COLUMN sort_order INTEGER DEFAULT 0"
-- wrangler d1 execute ramsrinivasan-db --remote --command="ALTER TABLE blogs ADD COLUMN ga_id TEXT DEFAULT 'G-ZH170NH9GW'"
