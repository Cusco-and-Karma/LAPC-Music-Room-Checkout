#!/usr/bin/env python3
"""Re-seed index.html from a master Class Schedule workbook.

The workbook has one sheet per weekday, rooms across row 3, and a 5-minute
time grid down column A starting at 8:00 in row 4. A booking is a run of
same-colored cells in a room column; the fill color says what kind of
booking it is, and the text carries its real start and end times.

    python3 import_schedule.py "2027 - SPRING - LAPC-MUSIC - Class Schedule - Master.xlsx" \
        --term "Spring 2027" --start 2027-02-08 --end 2027-06-07

Rewrites the DATA constant in index.html, and the term in config.js when
--term/--start/--end are given. Commit and push to deploy. Checkouts and
per-date changes live in Supabase, not in these files, so re-seeding
leaves them untouched.
"""
import argparse, json, re, sys, unicodedata, pathlib
import openpyxl

STRIPE = {"FFF2F2F2", "FFD9D9D9", "00000000", None}   # empty alternating rows
JUNK   = {"T0:-0.05", "T0:0.00"}                      # stray fills past the last hour
KIND   = {"FFFCF0D1": "class", "T4:0.80": "amp", "T5:0.80": "accomp",
          "T8:0.80": "office", "T9:0.80": "encore"}
DAYNUM = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5}
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[-–—]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.I)


def to24(h, m, ap):
    h, m = int(h), int(m or 0)
    if ap.lower() == "pm" and h != 12: h += 12
    if ap.lower() == "am" and h == 12: h = 0
    return h * 60 + m


def hhmm(x): return f"{x // 60:02d}:{x % 60:02d}"


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fill_of(cell):
    f = cell.fill
    if not f or f.fill_type != "solid": return None
    c = f.start_color
    if isinstance(c.rgb, str): return c.rgb
    if c.type == "theme": return f"T{c.theme}:{c.tint:.2f}"
    return str(c.indexed)


def extract(path):
    wb = openpyxl.load_workbook(path)
    rooms_order, events = [], []
    for ws in wb.worksheets:
        if ws.title not in DAYNUM: continue
        rooms = {}
        for c in range(2, 40):
            v = ws.cell(row=3, column=c).value
            if v:
                name = str(v).strip()
                rooms[c] = name
                if name not in rooms_order: rooms_order.append(name)

        merged = {(m.min_row, m.min_col): m.max_row
                  for m in ws.merged_cells.ranges
                  if m.min_col == m.max_col and m.min_col in rooms}

        for col, room in rooms.items():
            runs, run = [], None
            for r in range(4, ws.max_row + 1):
                fg = fill_of(ws.cell(row=r, column=col))
                if fg in STRIPE or fg in JUNK:
                    if run: runs.append(run); run = None
                    continue
                if run and run["color"] == fg: run["end"] = r
                else:
                    if run: runs.append(run)
                    run = {"color": fg, "start": r, "end": r}
            if run: runs.append(run)

            for b in runs:
                s, e = b["start"], max(b["end"], merged.get((b["start"], col), b["end"]))
                # A merged block keeps its whole label in the anchor cell as one
                # newline-separated string, so split those out into real lines.
                lines = []
                for r in range(s, e + 1):
                    v = ws.cell(row=r, column=col).value
                    if v is None: continue
                    lines += [l.strip() for l in str(v).split("\n") if l.strip()]
                if not lines: continue

                # One colored run can hold several bookings back to back; each
                # embedded "9:35 am - 11:00 am" closes one.
                segs, cur = [], []
                for l in lines:
                    cur.append(l)
                    if TIME_RE.search(l): segs.append(cur); cur = []
                if cur: segs.append(cur)

                prev_end = None
                for seg in segs:
                    tm, body = None, []
                    for l in seg:
                        m = TIME_RE.search(l)
                        if m and l.strip() == m.group(0).strip(): tm = m; continue
                        if m: tm = m
                        body.append(l)
                    if tm:
                        st = to24(tm.group(1), tm.group(2), tm.group(3))
                        en = to24(tm.group(4), tm.group(5), tm.group(6))
                    else:
                        st = prev_end if prev_end is not None else (s - 4) * 5 + 480
                        en = (e - 3) * 5 + 480
                    if en <= st: en = st + 60
                    prev_end = en
                    events.append({"day": ws.title, "room": room, "kind": KIND.get(b["color"], "other"),
                                   "start": hhmm(st), "end": hhmm(en), "lines": body})
    return rooms_order, events


def shape(rooms_order, raw):
    out, seen = [], {}
    for e in raw:
        lines, kind = e["lines"], e["kind"]
        code = title = instr = ""
        if kind in ("class", "encore"):
            code, rest = lines[0], lines[1:]
            if len(rest) >= 2: title, instr = " / ".join(rest[:-1]), rest[-1]
            elif rest: title = rest[0]
        elif kind == "amp":
            title, instr = "AMP Lessons", (lines[1] if len(lines) > 1 else "")
        elif kind == "office":
            title = "Office Hours"
            names = [l for l in lines if "office" not in l.lower()]
            instr = names[0] if names else ""
        else:
            title = " / ".join(lines)
            m = re.match(r"^(\w+)\s+Accomp", lines[0])
            if m: instr = m.group(1)

        stem = f"{e['day'][:3].lower()}-{slug(e['room'])}-{e['start'].replace(':', '')}"
        n = seen.get(stem, 0); seen[stem] = n + 1
        out.append({"id": stem if n == 0 else f"{stem}-{n + 1}", "dow": DAYNUM[e["day"]],
                    "room": e["room"], "kind": kind, "start": e["start"], "end": e["end"],
                    "code": code, "title": title, "instructor": instr})
    out.sort(key=lambda x: (x["dow"], x["room"], x["start"]))
    return {"rooms": rooms_order, "baseline": out}


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def update_term(name, start, end):
    """Point config.js at the new term. All three values are required together."""
    cfg = pathlib.Path(__file__).with_name("config.js")
    text = cfg.read_text()
    new = f'term: {{name: "{name}", start: "{start}", end: "{end}"}}'
    text, n = re.subn(r"term:\s*\{[^}]*\}", lambda _: new, text, count=1)
    if not n:
        sys.exit("Could not find the term entry in config.js.")
    cfg.write_text(text)
    print(f"Term set to {name} ({start} to {end}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Re-seed room-checkout from a Class Schedule workbook.")
    ap.add_argument("workbook", help="path to the .xlsx master schedule")
    ap.add_argument("--term",  help='term name, e.g. "Spring 2027"')
    ap.add_argument("--start", help="first day of instruction, YYYY-MM-DD")
    ap.add_argument("--end",   help="last day of instruction, YYYY-MM-DD")
    args = ap.parse_args()

    term_args = [args.term, args.start, args.end]
    if any(term_args) and not all(term_args):
        sys.exit("Pass --term, --start and --end together, or none of them.")
    for d in (args.start, args.end):
        if d and not DATE_RE.match(d):
            sys.exit(f"Dates must look like 2027-02-08, not {d!r}.")
    if args.start and args.end and args.end < args.start:
        sys.exit("The end date is before the start date.")

    src = args.workbook
    data = shape(*extract(src))
    page = pathlib.Path(__file__).with_name("index.html")
    html = page.read_text()
    new = "const DATA = " + json.dumps(data, separators=(",", ":")) + ";"
    html, n = re.subn(r"const DATA = \{.*?\};", lambda _: new, html, count=1, flags=re.S)
    if not n:
        sys.exit("Could not find the DATA constant in index.html.")
    page.write_text(html)
    print(f"{len(data['baseline'])} blocks across {len(data['rooms'])} rooms from {src}")
    print(f"Updated {page}.")
    if args.term:
        update_term(args.term, args.start, args.end)
    else:
        print("Term dates unchanged. Pass --term/--start/--end to move them.")
    print("Commit and push to deploy.")
