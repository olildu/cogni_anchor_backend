# cogni_anchor_backend

-- 1. Create the known_faces table (for Face Recognition data)
CREATE TABLE known_faces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    relationship VARCHAR(255),
    occupation VARCHAR(255),
    age VARCHAR(255),
    notes TEXT,
    -- PostgreSQL type for array of floats (128-dimensional face encoding)
    face_encoding REAL[] 
);

-- 2. Create the reminders table (for the new Reminder system)
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    -- Use TIMESTAMP WITHOUT TIME ZONE for scheduled date/time
    scheduled_datetime TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Create an index on the scheduled_datetime for faster sorting/querying
CREATE INDEX idx_reminders_scheduled_datetime ON reminders (scheduled_datetime);

-- 3. Quit the psql console
\q