-- Room Checkout — database setup.
-- Paste this whole file into the Supabase SQL Editor and run it once.
--
-- Two tables, each storing its records whole as jsonb so the app's own data
-- shapes survive a round trip untouched. The weekly master schedule is NOT
-- here: it is compiled into index.html from the department spreadsheet.

create table if not exists public.exceptions (
  id          text primary key,          -- "<block id>__<date>", one per changed occurrence
  data        jsonb not null,
  updated_at  timestamptz not null default now()
);

create table if not exists public.reservations (
  id          uuid primary key default gen_random_uuid(),
  data        jsonb not null,
  updated_at  timestamptz not null default now()
);

-- Rooms added by staff, on top of the ones compiled in from the spreadsheet.
-- Kept here rather than in index.html so re-importing a term does not lose them.
create table if not exists public.rooms (
  id          text primary key,          -- slug of the room name
  data        jsonb not null,
  updated_at  timestamptz not null default now()
);

alter table public.rooms        enable row level security;
alter table public.exceptions   enable row level security;
alter table public.reservations enable row level security;

-- Anyone with the link may read the schedule.
drop policy if exists read_rooms        on public.rooms;
create policy read_rooms on public.rooms for select to anon, authenticated using (true);
drop policy if exists write_rooms on public.rooms;
create policy write_rooms on public.rooms for all to authenticated using (true) with check (true);

drop policy if exists read_exceptions   on public.exceptions;
drop policy if exists read_reservations on public.reservations;
create policy read_exceptions   on public.exceptions   for select to anon, authenticated using (true);
create policy read_reservations on public.reservations for select to anon, authenticated using (true);

-- Only a signed-in editor may change anything. This is the real gate: it is
-- enforced by Postgres, so it holds no matter what the browser sends.
drop policy if exists write_exceptions   on public.exceptions;
drop policy if exists write_reservations on public.reservations;
create policy write_exceptions   on public.exceptions   for all to authenticated using (true) with check (true);
create policy write_reservations on public.reservations for all to authenticated using (true) with check (true);

-- Table privileges, stated explicitly so this schema does not depend on the
-- project's "automatically expose new tables" setting being on. anon gets read
-- only; writing is reserved to signed-in editors at the SQL level as well as
-- through the policies above.
grant usage on schema public to anon, authenticated;
grant select on public.exceptions, public.reservations, public.rooms to anon, authenticated;
grant insert, update, delete on public.exceptions, public.reservations, public.rooms to authenticated;

-- Push changes to everyone who has the page open.
alter publication supabase_realtime add table public.rooms;
alter publication supabase_realtime add table public.exceptions;
alter publication supabase_realtime add table public.reservations;
