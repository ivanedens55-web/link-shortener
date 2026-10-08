-- Link Shortener schema.
-- Apply ONCE as the database owner (Supabase SQL editor, or psql as postgres).
-- The app never runs this file: it connects as the restricted shortener_app role.
-- After applying, set the app role's password separately (see README):
--   alter role shortener_app with login password '<a long random password>';

begin;

-- ---------- Tables ----------

create table if not exists shortener_users (
    id            bigint generated always as identity primary key,
    email         text        not null unique,          -- UNIQUE also creates the index used by login lookups
    password_hash text        not null,
    created_at    timestamptz not null default now(),
    constraint shortener_users_email_lower check (email = lower(email)),
    constraint shortener_users_email_len   check (char_length(email) between 3 and 254)
);

create table if not exists shortener_links (
    id         bigint generated always as identity primary key,
    user_id    bigint      not null references shortener_users(id) on delete cascade,
    code       text        not null unique,             -- UNIQUE index makes the redirect lookup by code fast
    target_url text        not null,
    created_at timestamptz not null default now(),
    constraint shortener_links_code_format check (code ~ '^[A-Za-z0-9_-]{3,32}$'),
    constraint shortener_links_url_scheme  check (target_url ~* '^https?://'),
    constraint shortener_links_url_len     check (char_length(target_url) <= 2048)
);

create table if not exists shortener_clicks (
    id            bigint generated always as identity primary key,
    link_id       bigint      not null references shortener_links(id) on delete cascade,
    clicked_at    timestamptz not null default now(),
    referrer_host text,                                  -- host only (e.g. "news.ycombinator.com"), never the full URL
    constraint shortener_clicks_referrer_len check (referrer_host is null or char_length(referrer_host) <= 255)
);

-- ---------- Indexes ----------

-- Dashboard: "this user's links, newest first". Also covers the user_id foreign key.
create index if not exists shortener_links_user_created_idx
    on shortener_links (user_id, created_at desc);

-- Click counts and stats: "clicks for this link in a date range". Also covers the link_id
-- foreign key, so deleting a link doesn't scan the whole clicks table.
create index if not exists shortener_clicks_link_time_idx
    on shortener_clicks (link_id, clicked_at);

-- ---------- Restricted app role ----------

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'shortener_app') then
        create role shortener_app nologin;  -- login + password are set separately, never stored in this file
    end if;
end
$$;

grant usage on schema public to shortener_app;

-- Only what the app actually does. No UPDATE, no TRUNCATE, no CREATE/DROP.
grant select, insert         on shortener_users  to shortener_app;
grant select, insert, delete on shortener_links  to shortener_app;
grant select, insert         on shortener_clicks to shortener_app;
-- Identity columns use sequences; inserts need USAGE on them (only our three tables' sequences).
grant usage on sequence shortener_users_id_seq, shortener_links_id_seq, shortener_clicks_id_seq to shortener_app;

-- ---------- Row-level security ----------
-- RLS on: Supabase's Data API roles (anon, authenticated) have no policies, so they see nothing.
-- The app role has a policy for its own operations; per-user ownership is enforced in the backend
-- (every query on links filters by user_id).

alter table shortener_users  enable row level security;
alter table shortener_links  enable row level security;
alter table shortener_clicks enable row level security;

drop policy if exists shortener_app_all on shortener_users;
drop policy if exists shortener_app_all on shortener_links;
drop policy if exists shortener_app_all on shortener_clicks;
create policy shortener_app_all on shortener_users  for all to shortener_app using (true) with check (true);
create policy shortener_app_all on shortener_links  for all to shortener_app using (true) with check (true);
create policy shortener_app_all on shortener_clicks for all to shortener_app using (true) with check (true);

-- Belt and braces: remove Supabase's default grants to the Data API roles (skipped if they don't exist).
do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        revoke all on shortener_users, shortener_links, shortener_clicks from anon;
    end if;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        revoke all on shortener_users, shortener_links, shortener_clicks from authenticated;
    end if;
end
$$;

commit;
