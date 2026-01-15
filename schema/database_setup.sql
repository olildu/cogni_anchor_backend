-- 1. Enable Crypto Extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- 2. USERS TABLE (Updated)
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL CHECK (role IN ('patient', 'caretaker')),
    fcm_token VARCHAR, -- ✅ Added FCM Token Column
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ==========================================
-- 3. PAIRS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS pairs (
    id VARCHAR PRIMARY KEY,
    patient_user_id VARCHAR UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caretaker_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pairs_patient ON pairs(patient_user_id);
CREATE INDEX idx_pairs_caretaker ON pairs(caretaker_user_id);

-- ==========================================
-- 4. REMINDERS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    pair_id VARCHAR NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    title VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    time VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_reminders_pair ON reminders(pair_id);

-- ==========================================
-- 5. EMERGENCY ALERTS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS emergency_alerts (
    id SERIAL PRIMARY KEY,
    pair_id VARCHAR NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    alert_type VARCHAR NOT NULL,
    reason VARCHAR,
    status VARCHAR DEFAULT 'pending',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alerts_pair ON emergency_alerts(pair_id);

-- ==========================================
-- 6. PEOPLE TABLE (Face Recognition Metadata)
-- ==========================================
CREATE TABLE IF NOT EXISTS people (
    id VARCHAR PRIMARY KEY,
    pair_id VARCHAR NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    relationship VARCHAR,
    occupation VARCHAR,
    age INTEGER,
    notes TEXT,
    image_url VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_people_pair ON people(pair_id);

-- ==========================================
-- 7. FACE EMBEDDINGS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS face_embeddings (
    id SERIAL PRIMARY KEY,
    person_id VARCHAR NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    embedding FLOAT8[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_embeddings_person ON face_embeddings(person_id);

-- ==========================================
-- 8. PATIENT STATUS TABLE (Fixed Type Mismatch)
-- ==========================================
DROP TABLE IF EXISTS patient_status;

CREATE TABLE patient_status (
    id SERIAL PRIMARY KEY,
    -- Changed UUID to VARCHAR to match users.id type
    patient_user_id VARCHAR UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    location_permission BOOLEAN DEFAULT FALSE,
    mic_permission BOOLEAN DEFAULT FALSE,
    location_toggle_on BOOLEAN DEFAULT FALSE,
    mic_toggle_on BOOLEAN DEFAULT FALSE,
    is_logged_in BOOLEAN DEFAULT FALSE,
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- 9. LIVE LOCATION TABLE (Fixed Type Mismatch)
-- ==========================================
DROP TABLE IF EXISTS live_location;

CREATE TABLE live_location (
    id SERIAL PRIMARY KEY,
    -- Changed UUID to VARCHAR to match pairs.id
    pair_id VARCHAR, 
    -- Changed UUID to VARCHAR to match users.id
    patient_user_id VARCHAR UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    latitude FLOAT,
    longitude FLOAT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_live_location_pair_id ON live_location(pair_id);