CREATE TABLE IF NOT EXISTS tv_channels (id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,youtube_channel_id TEXT NOT NULL UNIQUE,country TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'Mundial',is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS tv_channels_country_idx ON tv_channels(country);
CREATE INDEX IF NOT EXISTS tv_channels_active_idx ON tv_channels(is_active);
