-- Goalkeeper AI PostgreSQL Schema

-- Users and auth
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT, -- only if storing credentials
  role TEXT NOT NULL, -- 'admin','club_admin','coach','viewer'
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE clubs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  city TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE coaches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  club_id UUID REFERENCES clubs(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE goalkeepers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id UUID REFERENCES clubs(id),
  name TEXT NOT NULL,
  birth_date DATE,
  dominant_hand TEXT,
  height_cm INT,
  weight_kg INT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goalkeeper_id UUID REFERENCES goalkeepers(id),
  coach_id UUID REFERENCES coaches(id),
  title TEXT,
  session_date TIMESTAMPTZ,
  category TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  training_session_id UUID REFERENCES training_sessions(id),
  uploader_id UUID REFERENCES users(id),
  r2_key TEXT NOT NULL, -- object key in R2
  r2_bucket TEXT NOT NULL,
  duration_seconds FLOAT,
  status TEXT NOT NULL DEFAULT 'uploaded', -- uploaded, queued, processing, done, failed
  width INT,
  height INT,
  fps FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  worker_id TEXT, -- optional identifier of AI worker
  status TEXT NOT NULL DEFAULT 'queued', -- queued, running, completed, failed
  progress INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE detected_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  timestamp_seconds FLOAT NOT NULL,
  event_type TEXT NOT NULL,
  category TEXT,
  confidence FLOAT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  indexed_at TIMESTAMPTZ
);

CREATE INDEX idx_detected_events_video_ts ON detected_events(video_id, timestamp_seconds);
CREATE INDEX idx_detected_events_type ON detected_events(event_type);

CREATE TABLE evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goalkeeper_id UUID REFERENCES goalkeepers(id),
  coach_id UUID REFERENCES coaches(id),
  category TEXT,
  score FLOAT,
  comments TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goalkeeper_id UUID REFERENCES goalkeepers(id),
  report_type TEXT,
  r2_key TEXT,
  generated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE coach_corrections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  detected_event_id UUID REFERENCES detected_events(id) ON DELETE SET NULL,
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  coach_id UUID REFERENCES coaches(id),
  action TEXT NOT NULL, -- confirm, edit, reject
  corrected_payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RAG/embeddings table (uses pgvector or external vector DB)
CREATE TABLE rag_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT,
  source_id UUID,
  content TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Simple audit logs
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  action TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Note: enable pgcrypto extension for gen_random_uuid() and pgvector extension when available.
