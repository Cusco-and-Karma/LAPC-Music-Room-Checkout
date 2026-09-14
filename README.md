# Room Checkout — LA Pierce College, Music

Room scheduling for the music department. The weekly master schedule comes from
the department's Class Schedule spreadsheet; on top of it, staff mark rooms out
for date ranges and record lessons that were moved or cancelled.

Anyone with the link can view. Editing requires signing in with the shared
department account.

- **Site:** static, hosted on GitHub Pages
- **Data:** Supabase (free tier) — checkouts, changes, live sync, and the editor login

---

## Setup

Roughly fifteen minutes, once.

### 1. Create the Supabase project

1. Sign up at [supabase.com](https://supabase.com) and create a project.
   Any region near Los Angeles is fine. Save the database password it gives you.
2. Open **SQL Editor**, paste in all of [`schema.sql`](schema.sql), and run it.
   That creates the two tables and the access rules.

### 2. Create the shared editor account

1. Go to **Authentication → Users → Add user**.
2. Use a department address rather than a personal one, so it outlives whoever
   set it up — something like `music-scheduler@piercecollege.edu`.
3. Set a password and tick **Auto Confirm User** so it works immediately.
4. Under **Authentication → Sign In / Providers**, turn **off** "Allow new users
   to sign up". Without this, anyone could register themselves an editor account.

That single account is what both editors use.

### 3. Point the site at the project

In Supabase, open **Project Settings → API** and copy the **Project URL** and
the **anon public** key into [`config.js`](config.js).

Both values belong in the repository. The anon key is a public identifier, not a
secret — it can only do what the policies in `schema.sql` permit, which is
read-only until someone signs in. The database password and the `service_role`
key are the real secrets: never put those in this repo.

### 4. Publish

Push to `main`, then in the repository go to **Settings → Pages** and set the
source to **Deploy from a branch**, branch `main`, folder `/ (root)`.
The site appears at `https://<user>.github.io/<repo>/` within a minute or two.

---

## Running it

**Viewing.** Open the link. Nothing to sign into.

**Editing.** Click **Sign in to edit** and use the shared account. Browsers stay
signed in for weeks. The badge reads *Can edit* and **+ Check out rooms**
appears.

**Checking out rooms.** *+ Check out rooms* → pick rooms, a date range, a time
range, and optionally specific weekdays. Overlaps with existing classes are
listed before saving; they don't block the checkout, they just warn.

**Changing a lesson.** Click any block: cancel that date, move it to another room
or time, or leave a note. Changes apply to that one date and leave the weekly
master intact. *Reset to master* undoes them.

**Changes panel.** Everything layered on top of the master, in date order. Click
an entry to jump to it.

---

## Each new term

The weekly schedule is compiled into `index.html`, so a new term means
re-importing it along with the term's dates:

```bash
python3 import_schedule.py "2027 - SPRING - LAPC-MUSIC - Class Schedule - Master.xlsx" \
    --term "Spring 2027" --start 2027-02-08 --end 2027-06-07
```

`--start` is the first day of instruction and `--end` the last. Outside those
dates the grid shows no classes, which is intended: the weekly pattern only
means something during the term. Rooms can still be checked out year-round.

Then commit and push:

```bash
git add -A && git commit -m "Spring 2027 schedule" && git push
```

GitHub Pages redeploys on its own, usually within a minute.

Checkouts and per-date changes live in Supabase, not in these files, so
re-importing never disturbs them.

Leave off `--term/--start/--end` to refresh the schedule without moving the
term — useful mid-semester when the master spreadsheet changes.

The importer expects the spreadsheet's existing layout: one sheet per weekday,
rooms across row 3, five-minute rows from 8:00 in row 4, and colour-coded
blocks. If that layout changes, the importer needs updating too.

## Housekeeping

Cancellations and changes accumulate one row per changed occurrence. It is not a
volume worth worrying about, but if you ever want to clear out old terms:

```sql
delete from public.exceptions   where (data->>'date') < '2027-01-01';
delete from public.reservations where (data->>'dateEnd') < '2027-01-01';
```
