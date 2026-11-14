-- EarthTrend Explorer: schema for NASA Space Apps 2026
-- Challenge: Earth System Trend Detective
-- All writes go through the Next.js API using the service-role key.
-- The anon key may only read the public reference tables.

create extension if not exists pgcrypto;

-- Variables the user can investigate (catalog with plain-language definitions)
create table if not exists public.variables (
  key              text primary key,
  provider         text not null default 'nasa_power',
  provider_param   text not null,
  name             text not null,
  category         text not null check (category in ('atmosphere','land','energy','water')),
  unit             text not null,
  definition       text not null,
  why_it_matters   text not null,
  source_model     text not null,
  higher_means     text not null,
  sort_order       int  not null default 0,
  active           boolean not null default true
);

-- Places: countries (seeded), plus cities/points created when users select them
create table if not exists public.regions (
  id            uuid primary key default gen_random_uuid(),
  key           text unique not null,          -- snapped "lat,lon" grid key (0.5 degree)
  name          text not null,
  country       text,
  country_code  text,
  kind          text not null default 'point' check (kind in ('country','region','city','point')),
  lat           double precision not null check (lat between -90 and 90),
  lon           double precision not null check (lon between -180 and 180),
  population    bigint,
  created_at    timestamptz not null default now()
);
create index if not exists regions_name_idx on public.regions using gin (to_tsvector('simple', name));
create index if not exists regions_kind_idx on public.regions (kind, name);

-- Raw monthly series fetched from NASA, cached to avoid repeat upstream calls
create table if not exists public.timeseries_cache (
  region_key    text not null,
  variable_key  text not null references public.variables(key) on delete cascade,
  start_year    int  not null,
  end_year      int  not null,
  data          jsonb not null,                -- [["YYYY-MM", value], ...]
  fetched_at    timestamptz not null default now(),
  primary key (region_key, variable_key, start_year, end_year)
);

-- Trend analysis results (dashboard + AI assistant read from here)
create table if not exists public.analyses (
  id            uuid primary key default gen_random_uuid(),
  region_key    text not null,
  variable_key  text not null references public.variables(key) on delete cascade,
  start_year    int  not null,
  end_year      int  not null,
  verdict       text not null check (verdict in ('significant','weak_evidence','not_significant')),
  slope_per_year double precision not null,
  p_value_ols   double precision not null,
  p_value_mk    double precision not null,
  result        jsonb not null,                -- full trend object
  created_at    timestamptz not null default now(),
  unique (region_key, variable_key, start_year, end_year)
);
create index if not exists analyses_verdict_idx on public.analyses (verdict);

-- Forecast results
create table if not exists public.forecasts (
  id            uuid primary key default gen_random_uuid(),
  region_key    text not null,
  variable_key  text not null references public.variables(key) on delete cascade,
  start_year    int  not null,
  end_year      int  not null,
  horizon_years int  not null check (horizon_years between 1 and 30),
  result        jsonb not null,
  created_at    timestamptz not null default now(),
  unique (region_key, variable_key, start_year, end_year, horizon_years)
);

-- Guided demo investigations for the "watch an example" flow
create table if not exists public.demo_examples (
  slug          text primary key,
  title         text not null,
  story         text not null,
  region_name   text not null,
  country       text,
  lat           double precision not null,
  lon           double precision not null,
  variable_key  text not null references public.variables(key) on delete cascade,
  start_year    int  not null,
  end_year      int  not null,
  sort_order    int  not null default 0
);

-- Lightweight usage log (which region/variable pairs people investigate)
create table if not exists public.investigations (
  id            bigint generated always as identity primary key,
  session_id    text,
  region_key    text not null,
  variable_key  text not null,
  action        text not null check (action in ('select','analyze','forecast','chat_context')),
  created_at    timestamptz not null default now()
);
create index if not exists investigations_created_idx on public.investigations (created_at desc);

-- Row Level Security: lock everything, expose only public reference data
alter table public.variables         enable row level security;
alter table public.regions           enable row level security;
alter table public.timeseries_cache  enable row level security;
alter table public.analyses          enable row level security;
alter table public.forecasts         enable row level security;
alter table public.demo_examples     enable row level security;
alter table public.investigations    enable row level security;

drop policy if exists "public read variables" on public.variables;
create policy "public read variables" on public.variables for select using (active);
drop policy if exists "public read regions" on public.regions;
create policy "public read regions" on public.regions for select using (true);
drop policy if exists "public read demo_examples" on public.demo_examples;
create policy "public read demo_examples" on public.demo_examples for select using (true);
-- timeseries_cache, analyses, forecasts, investigations: no policies = service role only.
