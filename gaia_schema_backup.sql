--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13 (Debian 15.13-1.pgdg120+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

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
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: create_kb_document_history(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.create_kb_document_history() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Insert into history when document is updated
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO kb_document_history (path, version, document, change_type, changed_by, change_message)
        VALUES (NEW.path, NEW.version, NEW.document, 'update', 
                COALESCE(NEW.document->>'changed_by', 'system'),
                COALESCE(NEW.document->>'change_message', 'Updated via API'));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO kb_document_history (path, version, document, change_type, changed_by, change_message)
        VALUES (NEW.path, NEW.version, NEW.document, 'create',
                COALESCE(NEW.document->>'changed_by', 'system'),
                COALESCE(NEW.document->>'change_message', 'Created via API'));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO kb_document_history (path, version, document, change_type, changed_by, change_message)
        VALUES (OLD.path, OLD.version, OLD.document, 'delete',
                COALESCE(OLD.document->>'changed_by', 'system'),
                COALESCE(OLD.document->>'change_message', 'Deleted via API'));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.create_kb_document_history() OWNER TO postgres;

--
-- Name: update_kb_document_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_kb_document_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_kb_document_timestamp() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: conversations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title character varying(255),
    preview text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.conversations OWNER TO postgres;

--
-- Name: kb_activity_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kb_activity_log (
    id integer NOT NULL,
    action text NOT NULL,
    resource_path text,
    resource_type text DEFAULT 'file'::text,
    actor_id text,
    actor_type text DEFAULT 'user'::text,
    details jsonb DEFAULT '{}'::jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT action_valid CHECK ((action = ANY (ARRAY['create'::text, 'read'::text, 'update'::text, 'delete'::text, 'search'::text, 'share'::text, 'move'::text])))
);


ALTER TABLE public.kb_activity_log OWNER TO postgres;

--
-- Name: TABLE kb_activity_log; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.kb_activity_log IS 'Activity log for monitoring and analytics';


--
-- Name: kb_activity_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kb_activity_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.kb_activity_log_id_seq OWNER TO postgres;

--
-- Name: kb_activity_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kb_activity_log_id_seq OWNED BY public.kb_activity_log.id;


--
-- Name: kb_context_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kb_context_cache (
    context_name text NOT NULL,
    file_paths text[] NOT NULL,
    total_size integer DEFAULT 0,
    keywords text[],
    entities jsonb,
    last_accessed timestamp without time zone DEFAULT now(),
    last_modified timestamp without time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT context_name_not_empty CHECK ((length(context_name) > 0))
);


ALTER TABLE public.kb_context_cache OWNER TO postgres;

--
-- Name: TABLE kb_context_cache; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.kb_context_cache IS 'Cached context metadata for fast context loading';


--
-- Name: kb_document_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kb_document_history (
    id integer NOT NULL,
    path text NOT NULL,
    version integer NOT NULL,
    document jsonb NOT NULL,
    change_type text NOT NULL,
    changed_by text,
    change_message text,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT change_type_valid CHECK ((change_type = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'move'::text]))),
    CONSTRAINT version_positive_history CHECK ((version > 0))
);


ALTER TABLE public.kb_document_history OWNER TO postgres;

--
-- Name: TABLE kb_document_history; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.kb_document_history IS 'Version history and audit trail for all document changes';


--
-- Name: kb_document_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kb_document_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.kb_document_history_id_seq OWNER TO postgres;

--
-- Name: kb_document_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kb_document_history_id_seq OWNED BY public.kb_document_history.id;


--
-- Name: kb_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kb_documents (
    path text NOT NULL,
    document jsonb NOT NULL,
    version integer DEFAULT 1,
    locked_by text,
    locked_until timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT path_not_empty CHECK ((length(path) > 0)),
    CONSTRAINT version_positive CHECK ((version > 0))
);


ALTER TABLE public.kb_documents OWNER TO postgres;

--
-- Name: TABLE kb_documents; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.kb_documents IS 'Main KB document storage with JSONB content and versioning';


--
-- Name: kb_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kb_permissions (
    id integer NOT NULL,
    resource_path text NOT NULL,
    resource_type text DEFAULT 'file'::text NOT NULL,
    principal_id text NOT NULL,
    principal_type text DEFAULT 'user'::text NOT NULL,
    permissions text[] DEFAULT ARRAY['read'::text] NOT NULL,
    granted_by text,
    granted_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone,
    CONSTRAINT permissions_valid CHECK ((permissions <@ ARRAY['read'::text, 'write'::text, 'share'::text, 'admin'::text])),
    CONSTRAINT principal_type_valid CHECK ((principal_type = ANY (ARRAY['user'::text, 'team'::text, 'public'::text]))),
    CONSTRAINT resource_type_valid CHECK ((resource_type = ANY (ARRAY['file'::text, 'directory'::text, 'context'::text])))
);


ALTER TABLE public.kb_permissions OWNER TO postgres;

--
-- Name: TABLE kb_permissions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.kb_permissions IS 'Access control and sharing permissions for multi-user support';


--
-- Name: kb_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kb_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.kb_permissions_id_seq OWNER TO postgres;

--
-- Name: kb_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kb_permissions_id_seq OWNED BY public.kb_permissions.id;


--
-- Name: kb_search_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kb_search_index (
    path text NOT NULL,
    line_number integer NOT NULL,
    content_excerpt text,
    search_vector tsvector,
    keywords text[],
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.kb_search_index OWNER TO postgres;

--
-- Name: TABLE kb_search_index; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.kb_search_index IS 'Optimized search index for fast full-text queries';


--
-- Name: kb_activity_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_activity_log ALTER COLUMN id SET DEFAULT nextval('public.kb_activity_log_id_seq'::regclass);


--
-- Name: kb_document_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_document_history ALTER COLUMN id SET DEFAULT nextval('public.kb_document_history_id_seq'::regclass);


--
-- Name: kb_permissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_permissions ALTER COLUMN id SET DEFAULT nextval('public.kb_permissions_id_seq'::regclass);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: kb_activity_log kb_activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_activity_log
    ADD CONSTRAINT kb_activity_log_pkey PRIMARY KEY (id);


--
-- Name: kb_context_cache kb_context_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_context_cache
    ADD CONSTRAINT kb_context_cache_pkey PRIMARY KEY (context_name);


--
-- Name: kb_document_history kb_document_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_document_history
    ADD CONSTRAINT kb_document_history_pkey PRIMARY KEY (id);


--
-- Name: kb_documents kb_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_documents
    ADD CONSTRAINT kb_documents_pkey PRIMARY KEY (path);


--
-- Name: kb_permissions kb_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_permissions
    ADD CONSTRAINT kb_permissions_pkey PRIMARY KEY (id);


--
-- Name: kb_permissions kb_permissions_resource_path_principal_id_principal_type_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_permissions
    ADD CONSTRAINT kb_permissions_resource_path_principal_id_principal_type_key UNIQUE (resource_path, principal_id, principal_type);


--
-- Name: kb_search_index kb_search_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_search_index
    ADD CONSTRAINT kb_search_index_pkey PRIMARY KEY (path, line_number);


--
-- Name: idx_kb_activity_actor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_activity_actor ON public.kb_activity_log USING btree (actor_id, created_at DESC);


--
-- Name: idx_kb_activity_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_activity_created ON public.kb_activity_log USING btree (created_at DESC);


--
-- Name: idx_kb_activity_resource; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_activity_resource ON public.kb_activity_log USING btree (resource_path, action);


--
-- Name: idx_kb_content_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_content_search ON public.kb_documents USING gin (to_tsvector('english'::regconfig, (document ->> 'content'::text)));


--
-- Name: idx_kb_context_accessed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_context_accessed ON public.kb_context_cache USING btree (last_accessed DESC);


--
-- Name: idx_kb_context_keywords; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_context_keywords ON public.kb_context_cache USING gin (keywords);


--
-- Name: idx_kb_history_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_history_created ON public.kb_document_history USING btree (created_at DESC);


--
-- Name: idx_kb_history_path; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_history_path ON public.kb_document_history USING btree (path, version DESC);


--
-- Name: idx_kb_history_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_history_user ON public.kb_document_history USING btree (changed_by, created_at DESC);


--
-- Name: idx_kb_keywords; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_keywords ON public.kb_documents USING gin (((document -> 'keywords'::text)));


--
-- Name: idx_kb_locked; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_locked ON public.kb_documents USING btree (locked_by, locked_until) WHERE (locked_by IS NOT NULL);


--
-- Name: idx_kb_metadata; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_metadata ON public.kb_documents USING gin (((document -> 'metadata'::text)));


--
-- Name: idx_kb_path_pattern; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_path_pattern ON public.kb_documents USING btree (path text_pattern_ops);


--
-- Name: idx_kb_permissions_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_permissions_expires ON public.kb_permissions USING btree (expires_at) WHERE (expires_at IS NOT NULL);


--
-- Name: idx_kb_permissions_principal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_permissions_principal ON public.kb_permissions USING btree (principal_id, principal_type);


--
-- Name: idx_kb_permissions_resource; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_permissions_resource ON public.kb_permissions USING btree (resource_path, resource_type);


--
-- Name: idx_kb_search_keywords; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_search_keywords ON public.kb_search_index USING gin (keywords);


--
-- Name: idx_kb_search_vector; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_search_vector ON public.kb_search_index USING gin (search_vector);


--
-- Name: idx_kb_updated_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_updated_at ON public.kb_documents USING btree (updated_at DESC);


--
-- Name: idx_kb_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_kb_version ON public.kb_documents USING btree (version);


--
-- Name: kb_documents trigger_kb_document_history; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_kb_document_history AFTER INSERT OR DELETE OR UPDATE ON public.kb_documents FOR EACH ROW EXECUTE FUNCTION public.create_kb_document_history();


--
-- Name: kb_documents trigger_kb_document_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_kb_document_updated_at BEFORE UPDATE ON public.kb_documents FOR EACH ROW EXECUTE FUNCTION public.update_kb_document_timestamp();


--
-- Name: kb_document_history kb_document_history_path_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_document_history
    ADD CONSTRAINT kb_document_history_path_fkey FOREIGN KEY (path) REFERENCES public.kb_documents(path) ON DELETE CASCADE;


--
-- Name: kb_search_index kb_search_index_path_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kb_search_index
    ADD CONSTRAINT kb_search_index_path_fkey FOREIGN KEY (path) REFERENCES public.kb_documents(path) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

