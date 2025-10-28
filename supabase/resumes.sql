create table public.resumes (
  resume_id bigserial not null PRIMARY KEY,
  resume jsonb not null,
  created_at timestamp with time zone not null default now(),
  name text,
  location text
);