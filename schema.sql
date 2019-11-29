--
-- PostgreSQL database dump
--

-- Dumped from database version 11.5 (Debian 11.5-1+deb10u1)
-- Dumped by pg_dump version 11.5 (Debian 11.5-1+deb10u1)

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
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: get_row(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_row(par_guid text) RETURNS TABLE(guid text, code text, bearer text, private_key text, installation_token text, session_token text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$begin
return query
    select  t.guid
    ,       t.code
    ,       t.bearer
    ,       t.private_key
    ,       t.installation_token
    ,       t.session_token
    from    tokens t
    where   t.guid = par_guid
;
end$$;


ALTER FUNCTION public.get_row(par_guid text) OWNER TO postgres;

--
-- Name: put_row(text, text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.put_row(par_guid text, par_code text, par_bearer text, par_private_key text, par_installation_token text, par_session_token text) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
declare
    token record;
    break boolean;
begin
    select * into token from tokens where guid = par_guid;
    if token.guid is null then
        insert into tokens
                (guid, code, bearer, private_key, installation_token,
                 session_token, created, updated)
        values  (par_guid, par_code, par_bearer, par_private_key,
                 par_installation_token, par_session_token, now(), now());
        return 2;
    end if;

    -- Only session token can be overwritten
    if token.code <> par_code or
       token.bearer <> par_bearer or
       token.private_key <> par_private_key or
       token.installation_token <> par_installation_token then
        return -1;
    end if;

    -- Accept updates only if previous step was set as well
    if token.code is null then
        token.code = par_code;
    end if;
    if token.bearer is null and par_code is not null then
        token.bearer = par_bearer;
    end if;
    if token.private_key is null and par_bearer is not null then
        token.private_key = par_private_key;
    end if;
    if token.installation_token is null and par_private_key is not null then
        token.installation_token = par_installation_token;
    end if;
    if par_installation_token is not null then
        token.session_token = par_session_token;
    end if;

    update  tokens
    set     updated = now()
    ,       code = token.code
    ,       bearer = token.bearer
    ,       private_key = token.private_key
    ,       installation_token = token.installation_token
    ,       session_token = token.session_token
    where   guid = par_guid
    ;
    return 1
    ;
end$$;


ALTER FUNCTION public.put_row(par_guid text, par_code text, par_bearer text, par_private_key text, par_installation_token text, par_session_token text) OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: tokens; Type: TABLE; Schema: public; Owner: wessel
--

CREATE TABLE public.tokens (
    id integer NOT NULL,
    guid text NOT NULL,
    bearer text,
    private_key text,
    installation_token text,
    session_token text,
    created timestamp without time zone,
    updated timestamp without time zone,
    code text
);


ALTER TABLE public.tokens OWNER TO wessel;

--
-- Name: tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: wessel
--

CREATE SEQUENCE public.tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tokens_id_seq OWNER TO wessel;

--
-- Name: tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wessel
--

ALTER SEQUENCE public.tokens_id_seq OWNED BY public.tokens.id;


--
-- Name: tokens id; Type: DEFAULT; Schema: public; Owner: wessel
--

ALTER TABLE ONLY public.tokens ALTER COLUMN id SET DEFAULT nextval('public.tokens_id_seq'::regclass);


--
-- Name: tokens tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: wessel
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_pkey PRIMARY KEY (guid);


--
-- Name: TABLE tokens; Type: ACL; Schema: public; Owner: wessel
--

REVOKE ALL ON TABLE public.tokens FROM wessel;


--
-- PostgreSQL database dump complete
--

