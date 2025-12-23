-- CogniAnchor Database Setup Script for Supabase
-- Run this in Supabase SQL Editor to set up all required tables

-- Enable pgvector extension for face embeddings (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- ===== PAIRS TABLE =====
-- Stores patient-caretaker relationships
CREATE TABLE IF NOT EXISTS pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    caretaker_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_pairs_patient ON pairs(patient_user_id);
CREATE INDEX IF NOT EXISTS idx_pairs_caretaker ON pairs(caretaker_user_id);

-- ===== REMINDERS TABLE =====
-- Stores reminders for patients
CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    pair_id UUID NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    date TEXT NOT NULL,  -- Format: 'dd MMM yyyy' (e.g., '25 Dec 2024')
    time TEXT NOT NULL,  -- Format: 'hh:mm a' (e.g., '02:30 PM')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_reminders_pair ON reminders(pair_id);
CREATE INDEX IF NOT EXISTS idx_reminders_date ON reminders(date);

-- ===== PEOPLE TABLE =====
-- Stores people enrolled in face recognition
CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    pair_id UUID NOT NULL REFERENCES pairs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    occupation TEXT NOT NULL,
    age INTEGER,
    notes TEXT,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_people_pair ON people(pair_id);
CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);

-- ===== FACE_EMBEDDINGS TABLE =====
-- Stores face embedding vectors for recognition
CREATE TABLE IF NOT EXISTS face_embeddings (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    embedding vector(512),  -- 512 dimensions for Facenet512 model
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_face_embeddings_person ON face_embeddings(person_id);

-- Add vector similarity search index (optional, for faster searches)
-- CREATE INDEX ON face_embeddings USING ivfflat (embedding vector_cosine_ops);

-- ===== STORAGE BUCKET =====
-- Create storage bucket for face images (run this manually in Supabase Dashboard or via API)
-- Go to Storage > Create Bucket > Name: "face-images" > Public: true

-- ===== ROW LEVEL SECURITY (RLS) POLICIES =====
-- Enable RLS on all tables
ALTER TABLE pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_embeddings ENABLE ROW LEVEL SECURITY;

-- ===== PAIRS POLICIES =====
-- Users can read their own pairs
CREATE POLICY "Users can read own pairs" ON pairs
    FOR SELECT
    USING (auth.uid() = patient_user_id OR auth.uid() = caretaker_user_id);

-- Patients can create pairs (during signup)
CREATE POLICY "Patients can create pairs" ON pairs
    FOR INSERT
    WITH CHECK (auth.uid() = patient_user_id);

-- Caretakers can update pairs (when connecting)
CREATE POLICY "Caretakers can update pairs" ON pairs
    FOR UPDATE
    USING (auth.uid() = caretaker_user_id OR auth.uid() = patient_user_id);

-- ===== REMINDERS POLICIES =====
-- Users can read reminders for their pair
CREATE POLICY "Users can read pair reminders" ON reminders
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = reminders.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can create reminders for their pair
CREATE POLICY "Users can create pair reminders" ON reminders
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = reminders.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can update reminders for their pair
CREATE POLICY "Users can update pair reminders" ON reminders
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = reminders.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can delete reminders for their pair
CREATE POLICY "Users can delete pair reminders" ON reminders
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = reminders.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- ===== PEOPLE POLICIES =====
-- Users can read people for their pair
CREATE POLICY "Users can read pair people" ON people
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = people.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can create people for their pair
CREATE POLICY "Users can create pair people" ON people
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = people.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can update people for their pair
CREATE POLICY "Users can update pair people" ON people
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = people.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can delete people for their pair
CREATE POLICY "Users can delete pair people" ON people
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM pairs
            WHERE pairs.id = people.pair_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- ===== FACE_EMBEDDINGS POLICIES =====
-- Users can read embeddings for people in their pair
CREATE POLICY "Users can read pair embeddings" ON face_embeddings
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM people
            JOIN pairs ON people.pair_id = pairs.id
            WHERE people.id = face_embeddings.person_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can create embeddings for people in their pair
CREATE POLICY "Users can create pair embeddings" ON face_embeddings
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM people
            JOIN pairs ON people.pair_id = pairs.id
            WHERE people.id = face_embeddings.person_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can update embeddings for people in their pair
CREATE POLICY "Users can update pair embeddings" ON face_embeddings
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM people
            JOIN pairs ON people.pair_id = pairs.id
            WHERE people.id = face_embeddings.person_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- Users can delete embeddings for people in their pair
CREATE POLICY "Users can delete pair embeddings" ON face_embeddings
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM people
            JOIN pairs ON people.pair_id = pairs.id
            WHERE people.id = face_embeddings.person_id
            AND (pairs.patient_user_id = auth.uid() OR pairs.caretaker_user_id = auth.uid())
        )
    );

-- ===== COMPLETED =====
-- Database setup complete!
-- Next steps:
-- 1. Create storage bucket "face-images" in Supabase Dashboard
-- 2. Update .env with SUPABASE_SERVICE_KEY for admin operations
-- 3. Test API endpoints
