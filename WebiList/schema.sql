PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE participants (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),
 email TEXT NOT NULL COLLATE NOCASE UNIQUE
   CHECK(email = trim(email) AND email LIKE '%_@_%._%')
);
CREATE TABLE speakers (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120)
);
CREATE TABLE categories (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(trim(name)) > 0)
);
CREATE TABLE webinars (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id)) > 0),
 title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 250),
 speaker_id INTEGER NOT NULL REFERENCES speakers(id) ON DELETE RESTRICT,
 category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
 starts_at TEXT NOT NULL CHECK(length(starts_at) = 19 AND datetime(starts_at) IS NOT NULL)
);
CREATE TABLE registrations (
 id INTEGER PRIMARY KEY,
 participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE RESTRICT,
 webinar_id TEXT NOT NULL REFERENCES webinars(id) ON DELETE RESTRICT,
 registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 attended INTEGER NOT NULL DEFAULT 0 CHECK(attended IN (0, 1)),
 UNIQUE(participant_id, webinar_id)
);
CREATE INDEX idx_webinars_starts_at ON webinars(starts_at);
CREATE INDEX idx_webinars_speaker ON webinars(speaker_id);
CREATE INDEX idx_webinars_category_date ON webinars(category_id, starts_at);
CREATE INDEX idx_registrations_webinar ON registrations(webinar_id);
COMMIT;
