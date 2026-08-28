-- WEBPLAY 2.0 canonical PostgreSQL schema.
-- Safe to run repeatedly on a fresh database.
CREATE TABLE IF NOT EXISTS media_items (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  source_name TEXT NOT NULL,
  youtube_video_id TEXT NOT NULL UNIQUE,
  youtube_channel_id TEXT,
  media_type TEXT NOT NULL CHECK (media_type IN ('Filme','Serie','Audiolivro','TV')),
  category TEXT NOT NULL DEFAULT 'Geral',
  country TEXT NOT NULL DEFAULT 'Global',
  language TEXT NOT NULL DEFAULT 'Português',
  duration TEXT NOT NULL DEFAULT 'Completo',
  thumbnail_url TEXT,
  source_url TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS media_items_type_idx ON media_items(media_type);
CREATE INDEX IF NOT EXISTS media_items_country_idx ON media_items(country);
CREATE INDEX IF NOT EXISTS media_items_language_idx ON media_items(language);
CREATE INDEX IF NOT EXISTS media_items_active_idx ON media_items(is_active);
CREATE INDEX IF NOT EXISTS media_items_title_idx ON media_items(title);

CREATE TABLE IF NOT EXISTS tv_channels (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  youtube_channel_id TEXT NOT NULL UNIQUE,
  country TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'Mundial',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tv_channels_country_idx ON tv_channels(country);
CREATE INDEX IF NOT EXISTS tv_channels_active_idx ON tv_channels(is_active);

CREATE TABLE IF NOT EXISTS vertical_series (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  book_title TEXT,
  author TEXT,
  description TEXT,
  price_total NUMERIC(10,2) NOT NULL DEFAULT 19.90,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vertical_episodes (
  id BIGSERIAL PRIMARY KEY,
  series_id BIGINT NOT NULL REFERENCES vertical_series(id) ON DELETE CASCADE,
  episode_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  youtube_video_id TEXT NOT NULL UNIQUE,
  release_at TIMESTAMPTZ,
  free_at TIMESTAMPTZ,
  access_mode TEXT NOT NULL DEFAULT 'premium' CHECK (access_mode IN ('free','premium')),
  price NUMERIC(10,2) NOT NULL DEFAULT 2.99,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(series_id, episode_number)
);

CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  provider_payment_id TEXT UNIQUE,
  status TEXT NOT NULL,
  amount NUMERIC(10,2) NOT NULL,
  currency TEXT NOT NULL DEFAULT 'BRL',
  user_ref TEXT,
  series_id BIGINT REFERENCES vertical_series(id) ON DELETE SET NULL,
  episode_id BIGINT REFERENCES vertical_episodes(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS episode_access (
  id BIGSERIAL PRIMARY KEY,
  user_ref TEXT NOT NULL,
  episode_id BIGINT NOT NULL REFERENCES vertical_episodes(id) ON DELETE CASCADE,
  order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL,
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_ref, episode_id)
);

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  subscribed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS newsletter_subscribers_active_idx ON newsletter_subscribers(active);

CREATE TABLE IF NOT EXISTS discovery_runs (
  id BIGSERIAL PRIMARY KEY,
  run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  country TEXT,
  channels_found INTEGER NOT NULL DEFAULT 0,
  media_found INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_rights (
  id BIGSERIAL PRIMARY KEY,
  youtube_video_id TEXT UNIQUE NOT NULL,
  rights_status TEXT NOT NULL DEFAULT 'unknown',
  evidence_url TEXT,
  reviewed_at TIMESTAMPTZ,
  reviewer TEXT
);

CREATE TABLE IF NOT EXISTS acervo_livres (
  id BIGSERIAL PRIMARY KEY,
  titulo TEXT NOT NULL,
  autor TEXT NOT NULL,
  pais TEXT NOT NULL,
  idioma TEXT NOT NULL,
  genero TEXT NOT NULL,
  ano_publicacao INTEGER,
  fonte_oficial TEXT NOT NULL,
  jurisdicao_verificada TEXT NOT NULL DEFAULT 'requer_verificacao_por_edicao',
  status_direitos TEXT NOT NULL DEFAULT 'candidato_dominio_publico',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(titulo, autor, idioma)
);
