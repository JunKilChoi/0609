create extension if not exists pgcrypto;

create table if not exists app_users (
  id uuid primary key default gen_random_uuid(),
  username text unique not null,
  display_name text not null,
  password_hash text not null,
  role text not null default 'member'
    check (role in ('admin', 'member')),
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'blocked')),
  created_at timestamptz not null default now()
);

create table if not exists posts (
  id bigint generated always as identity primary key,
  title text not null,
  body text not null,
  author_id uuid references app_users(id) on delete set null,
  created_at timestamptz not null default now()
);
