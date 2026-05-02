-- Module 1: minimal schema. Module 2 replaces this with messages/chunks/embeddings.

create extension if not exists pgcrypto;

create table if not exists public.user_settings (
    user_id uuid primary key references auth.users(id) on delete cascade,
    vector_store_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.chat_threads (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text,
    last_response_id text,
    vector_store_id text,
    created_at timestamptz not null default now()
);
create index if not exists chat_threads_user_idx on public.chat_threads(user_id, created_at desc);

create table if not exists public.uploaded_files (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    openai_file_id text not null,
    openai_vector_store_id text not null,
    filename text,
    bytes bigint,
    status text not null default 'in_progress',
    created_at timestamptz not null default now()
);
create index if not exists uploaded_files_user_idx on public.uploaded_files(user_id, created_at desc);

alter table public.user_settings enable row level security;
alter table public.chat_threads enable row level security;
alter table public.uploaded_files enable row level security;

drop policy if exists "user_settings owner" on public.user_settings;
create policy "user_settings owner" on public.user_settings
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "chat_threads owner" on public.chat_threads;
create policy "chat_threads owner" on public.chat_threads
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "uploaded_files owner" on public.uploaded_files;
create policy "uploaded_files owner" on public.uploaded_files
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
