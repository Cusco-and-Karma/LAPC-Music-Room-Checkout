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

The site is at **https://cusco-and-karma.github.io/LAPC-Music-Room-Checkout/**

Renaming the repository moves that URL, and GitHub does **not** redirect old
Pages addresses — the previous one returns 404. Re-share the link if you
rename it again.

---

## Running it

**Viewing.** Open the link. Nothing to sign into.

**Editing.** Click **Sign in to edit** and use the shared account. Browsers stay
signed in for weeks. The badge reads *Can edit* and **+ Check out rooms**
appears.

**Finding a free room.** *Find a room* answers "what's open Thursdays from 2:15
to 3:30?" — give it a time, the weekdays, and a date range, and it lists the
rooms free on every matching date, the ones free on only some (with what's in
the way and how often), and the ones never free. Clicking a result jumps to that
date so you can see the conflict. Editors get a button straight through to the
checkout form with the search already filled in. Hidden rooms are still
searched, since hiding is only about your own view.

**Checking out rooms.** *+ Check out rooms* → pick rooms, a category, a date
range, a time range, and optionally specific weekdays. Tick **All day** to hold the room for
the whole day instead of naming times — it fills the room's column and counts as
busy at any hour, so the room finder and the overlap warning both treat it as
taken. The category sets the
block's colour and lets people filter by it: checkout, event, tutoring, AMP
lesson, accompanist, office hours, Encore, or blocked. It can be changed later
from the block itself, and applies to every date in that checkout. Classes are
not offered, since those come from the spreadsheet. Overlaps with existing classes are
listed before saving; they don't block the checkout, they just warn.

**Changing a lesson.** Click any block: cancel it, move it to another room or
time, or leave a note. A repeating block asks what the change applies to, the
way Outlook does:

| | |
|---|---|
| **This date** | just this one occurrence |
| **This and later** | this date through the end of the series |
| **Every date** | the whole series |

The panel says how many dates are affected and which weekdays before you
commit, and anything touching more than one date asks to confirm. A class the
spreadsheet lists on two weekdays counts as one series, so cancelling MUSIC
216-3 catches both its Tuesday and Thursday sittings.

Editing a **checkout** across more than one date changes the checkout itself
rather than stamping a pile of per-date exceptions — *This and later* splits it
into two, exactly as Outlook does, leaving earlier dates alone. *Reset* undoes
per-date changes at whatever scope is selected.

**Changes panel.** Everything layered on top of the master, in date order. Click
an entry to jump to it.

**Month view.** *Month* has four modes, because twenty rooms across thirty days
will not fit on a screen and each mode picks a different thing to give up:

| mode | answers |
|---|---|
| **Room** | "when is 3422 free in October?" — one room, every day |
| **Categories** | "what events are on this month?" — all rooms, filtered by the colour keys |
| **Agenda** | everything in the month in order, as a list — the one that prints |
| **Occupancy** | which days and weeks are busy, shaded by how much of the building is spoken for |

Clicking a day opens it; clicking an agenda row opens that booking. The search
box and colour keys narrow all four. On a phone the grid modes drop the text and
show one coloured bar per booking, so a day still reads as busy or quiet at a
glance; Agenda stays fully readable.

**Searching.** Type a course number (`216-3`), a room, or an instructor into the
search box and the grid narrows to just that — other classes and any room with
no match drop out. A bar above the grid says where the match sits in the week,
so `216-3` answers "Tue & Thu, 11:10am–12:35pm, 3422, Anthony Wardzinski"
without paging through days. Partial numbers work: `216` shows all three
sections. Clear the box to get everything back.

**Filtering by type.** The colour keys along the bottom are buttons — click
Event, or Tutoring, or several at once, to show only those. *Cancelled* filters
too. This stacks with the search box.

**On a phone.** The toolbar and colour keys scroll sideways as single rows, the
grid scrolls both ways with the time column and room names pinned, and panels
open as bottom sheets.

**Showing and hiding rooms.** *Rooms* lists every room as a toggle. Switching one
off drops it from the grid — useful for trimming 21 columns down to the handful
you care about. This is a per-person view setting saved in your own browser, not
a change anyone else sees, and it never affects checkouts: a hidden room can
still be booked from the checkout form. The toolbar button shows how many are
hidden. Anyone can use this; no sign-in needed.

**Adding rooms.** *Rooms* lets editors add rooms the spreadsheet doesn't carry —
adjunct offices, a storage room, anything bookable. Enter a number and an
optional label ("3416-B" + "Adjunct Office"). Added rooms sort into place by
number, have no recurring classes, and are available for checkout like any
other. They live in Supabase rather than in `index.html`, so importing a new
term never loses them.

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

## Branding

`assets/` holds the department mark and the icons derived from it:

| file | used for |
|---|---|
| `logo.svg` | the master, as supplied |
| `logo-160.png` | the masthead (shown at 42px, so 4x for sharp screens) |
| `apple-touch-icon.png` | a phone home-screen shortcut |
| `favicon-32.png`, `favicon-16.png` | the browser tab |

The supplied SVG is a raster image in an SVG wrapper — six embedded PNGs and
a set of filters, 322 KB — so the PNGs above were rendered from it once rather
than shipping the SVG to every visitor. Its square canvas is opaque white, and
the mark is a disc, so each PNG is masked to a circle and sits correctly on a
light or dark background.

To regenerate after a logo change, replace `assets/logo.svg` and run:

```bash
qlmanage -t -s 1024 -o . assets/logo.svg     # renders logo.svg.png
python3 - <<'PY'
from PIL import Image, ImageDraw
src = Image.open("logo.svg.png").convert("RGBA"); S = src.size[0]
m = Image.new("L", (S*4, S*4), 0); ImageDraw.Draw(m).ellipse((0,0,S*4-1,S*4-1), fill=255)
src.putalpha(m.resize((S,S), Image.LANCZOS))
for name, size in {"logo-512":512,"apple-touch-icon":180,"logo-160":160,
                   "favicon-32":32,"favicon-16":16}.items():
    src.resize((size,size), Image.LANCZOS).save(f"assets/{name}.png", optimize=True)
PY
```

The brand red is `#FF6C50`. The interface accent is deliberately a different,
quieter colour so it does not compete with the category colours on the grid.

## Backups and version history

A GitHub Action runs every night at about 4am Los Angeles time and saves the
database to `backups/` as an Excel workbook. It needs no secrets: it reads with
the same public key the site uses, which the access rules limit to reading.

- `backups/latest.xlsx` — always the most recent snapshot
- `backups/room-checkout-YYYY-MM-DD.xlsx` — one per day the data actually
  changed, so the history is a list of real versions rather than 365 identical
  files
- the git history of `backups/` is the version log; every restore point is a
  commit you can browse on GitHub

Each workbook has Monday–Friday sheets showing the class schedule as a readable
grid, plus **Checkouts**, **Changes** and **Rooms** — the three data sheets that
a restore actually reads.

To run one now rather than waiting for tonight: **Actions → Daily backup → Run
workflow**.

### Restoring

Preview first. This never writes anything without `--apply`:

```bash
python3 restore.py backups/room-checkout-2026-09-15.xlsx
```

It prints exactly what would change — what gets restored, what gets altered,
and what gets deleted. When it looks right:

```bash
python3 restore.py backups/room-checkout-2026-09-15.xlsx --apply
```

You will be asked to type `restore` to confirm, then to sign in with the shared
department account, since writing requires an editor. The password is not
echoed and is never stored.

Restoring makes the database **match the backup exactly**: anything created
after that backup was taken is deleted. To recover one deleted checkout without
rolling everything back, open the backup, read the row, and re-enter it in the
site by hand.

The class schedule is not part of a restore — it lives in `index.html` and is
recovered with git, or by re-running the importer.

### What is not covered

These backups cover the database. They do not cover the Supabase project
itself: if the project were deleted, you would recreate it with `schema.sql`,
create the editor account again, update `config.js`, and then restore.

## Housekeeping

Cancellations and changes accumulate one row per changed occurrence. It is not a
volume worth worrying about, but if you ever want to clear out old terms:

```sql
delete from public.exceptions   where (data->>'date') < '2027-01-01';
delete from public.reservations where (data->>'dateEnd') < '2027-01-01';
```
