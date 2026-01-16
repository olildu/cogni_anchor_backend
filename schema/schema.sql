--
-- PostgreSQL database dump
--

\restrict YmXR6MGiLweWr66H1OKqnPiNfqVydvNORjGNSEQJ5rDVPVrpwel3H1jt2jjfP3x

-- Dumped from database version 15.15 (Homebrew)
-- Dumped by pg_dump version 15.15 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: emergency_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.emergency_alerts (
    id integer NOT NULL,
    pair_id character varying NOT NULL,
    alert_type character varying,
    reason character varying,
    status character varying DEFAULT 'pending'::character varying,
    "timestamp" timestamp with time zone DEFAULT now()
);


--
-- Name: emergency_alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.emergency_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: emergency_alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.emergency_alerts_id_seq OWNED BY public.emergency_alerts.id;


--
-- Name: face_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.face_embeddings (
    id integer NOT NULL,
    person_id character varying NOT NULL,
    embedding double precision[] NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: face_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.face_embeddings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: face_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.face_embeddings_id_seq OWNED BY public.face_embeddings.id;


--
-- Name: live_location; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.live_location (
    id integer NOT NULL,
    pair_id uuid,
    patient_user_id uuid,
    latitude double precision,
    longitude double precision,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: live_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.live_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: live_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.live_location_id_seq OWNED BY public.live_location.id;


--
-- Name: pairs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pairs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    patient_user_id uuid NOT NULL,
    caretaker_user_id uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: patient_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_status (
    id integer NOT NULL,
    patient_user_id uuid,
    location_permission boolean DEFAULT false,
    mic_permission boolean DEFAULT false,
    location_toggle_on boolean DEFAULT false,
    mic_toggle_on boolean DEFAULT false,
    is_logged_in boolean DEFAULT false,
    last_active_at timestamp with time zone DEFAULT now()
);


--
-- Name: patient_status_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_status_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_status_id_seq OWNED BY public.patient_status.id;


--
-- Name: people; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people (
    id character varying NOT NULL,
    pair_id character varying NOT NULL,
    name character varying,
    relationship character varying,
    occupation character varying,
    age integer,
    notes text,
    image_url character varying,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: reminders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reminders (
    id integer NOT NULL,
    pair_id character varying NOT NULL,
    title character varying,
    date character varying,
    "time" character varying,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: reminders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reminders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reminders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reminders_id_seq OWNED BY public.reminders.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email text NOT NULL,
    hashed_password text NOT NULL,
    role text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    fcm_token character varying,
    name character varying,
    contact character varying,
    gender character varying,
    date_of_birth timestamp with time zone,
    CONSTRAINT users_role_check CHECK ((role = ANY (ARRAY['patient'::text, 'caretaker'::text])))
);


--
-- Name: emergency_alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emergency_alerts ALTER COLUMN id SET DEFAULT nextval('public.emergency_alerts_id_seq'::regclass);


--
-- Name: face_embeddings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.face_embeddings ALTER COLUMN id SET DEFAULT nextval('public.face_embeddings_id_seq'::regclass);


--
-- Name: live_location id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_location ALTER COLUMN id SET DEFAULT nextval('public.live_location_id_seq'::regclass);


--
-- Name: patient_status id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_status ALTER COLUMN id SET DEFAULT nextval('public.patient_status_id_seq'::regclass);


--
-- Name: reminders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reminders ALTER COLUMN id SET DEFAULT nextval('public.reminders_id_seq'::regclass);


--
-- Name: emergency_alerts emergency_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emergency_alerts
    ADD CONSTRAINT emergency_alerts_pkey PRIMARY KEY (id);


--
-- Name: face_embeddings face_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.face_embeddings
    ADD CONSTRAINT face_embeddings_pkey PRIMARY KEY (id);


--
-- Name: live_location live_location_patient_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_location
    ADD CONSTRAINT live_location_patient_user_id_key UNIQUE (patient_user_id);


--
-- Name: live_location live_location_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_location
    ADD CONSTRAINT live_location_pkey PRIMARY KEY (id);


--
-- Name: pairs pairs_patient_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs
    ADD CONSTRAINT pairs_patient_user_id_key UNIQUE (patient_user_id);


--
-- Name: pairs pairs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs
    ADD CONSTRAINT pairs_pkey PRIMARY KEY (id);


--
-- Name: patient_status patient_status_patient_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_status
    ADD CONSTRAINT patient_status_patient_user_id_key UNIQUE (patient_user_id);


--
-- Name: patient_status patient_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_status
    ADD CONSTRAINT patient_status_pkey PRIMARY KEY (id);


--
-- Name: people people_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_pkey PRIMARY KEY (id);


--
-- Name: reminders reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_alerts_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_alerts_pair ON public.emergency_alerts USING btree (pair_id);


--
-- Name: idx_pairs_caretaker; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pairs_caretaker ON public.pairs USING btree (caretaker_user_id);


--
-- Name: idx_pairs_patient; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pairs_patient ON public.pairs USING btree (patient_user_id);


--
-- Name: idx_people_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_people_pair ON public.people USING btree (pair_id);


--
-- Name: idx_reminders_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reminders_pair ON public.reminders USING btree (pair_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: ix_emergency_alerts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_emergency_alerts_id ON public.emergency_alerts USING btree (id);


--
-- Name: ix_emergency_alerts_pair_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_emergency_alerts_pair_id ON public.emergency_alerts USING btree (pair_id);


--
-- Name: ix_live_location_pair_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_live_location_pair_id ON public.live_location USING btree (pair_id);


--
-- Name: ix_reminders_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reminders_id ON public.reminders USING btree (id);


--
-- Name: ix_reminders_pair_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reminders_pair_id ON public.reminders USING btree (pair_id);


--
-- Name: face_embeddings face_embeddings_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.face_embeddings
    ADD CONSTRAINT face_embeddings_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE CASCADE;


--
-- Name: live_location live_location_patient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_location
    ADD CONSTRAINT live_location_patient_user_id_fkey FOREIGN KEY (patient_user_id) REFERENCES public.users(id);


--
-- Name: pairs pairs_caretaker_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs
    ADD CONSTRAINT pairs_caretaker_user_id_fkey FOREIGN KEY (caretaker_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: pairs pairs_patient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs
    ADD CONSTRAINT pairs_patient_user_id_fkey FOREIGN KEY (patient_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: patient_status patient_status_patient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_status
    ADD CONSTRAINT patient_status_patient_user_id_fkey FOREIGN KEY (patient_user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict YmXR6MGiLweWr66H1OKqnPiNfqVydvNORjGNSEQJ5rDVPVrpwel3H1jt2jjfP3x

