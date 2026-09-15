#!/usr/bin/env python3
"""Snapshot the room-checkout database to an Excel workbook.

Reads the live data with the same public key the website uses, which is
read-only, so this needs no secrets and runs unattended in CI.

    python3 backup.py [--out backups]

The workbook holds two kinds of sheet:

  Monday..Friday  the weekly class schedule as a grid, in the same shape as
                  the department's Class Schedule master, for reading
  Checkouts       every booking, one row each
  Changes         every cancelled or moved lesson, one row each
  Rooms           rooms added on top of the spreadsheet
  About           when it was taken and what it holds

The three data sheets are what `restore.py` reads back; the weekday grids are
there so a person can open a backup and see the schedule.
"""
import argparse, datetime as dt, hashlib, json, pathlib, re, sys, urllib.request

HERE = pathlib.Path(__file__).parent
TABLES = ["reservations", "exceptions", "rooms"]
DAYS = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday"}
# Checkouts may fall on a weekend even though classes never do.
DAYNAMES = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
            4: "Thursday", 5: "Friday", 6: "Saturday"}

# Block colours, matching the categories the site uses.
FILL = {"class": "FCF0D1", "amp": "DCE9F2", "accomp": "E2EFE1", "office": "FBEAE0",
        "encore": "EFE9F5", "event": "DFF0EF", "tutoring": "F8E6EF",
        "checkout": "F7E7E9", "blocked": "ECEAEA"}
STRIPE = ("FFFFFF", "F7F7F6")


def config():
    """Read the project URL and public key out of config.js."""
    text = (HERE / "config.js").read_text()
    url = re.search(r'supabaseUrl:\s*"([^"]+)"', text).group(1)
    key = re.search(r'supabaseAnonKey:\s*"([^"]+)"', text).group(1)
    term = re.search(r'term:\s*\{name:\s*"([^"]+)",\s*start:\s*"([^"]+)",\s*end:\s*"([^"]+)"', text)
    return url.rstrip("/"), key, (term.groups() if term else ("", "", ""))


def fetch(url, key, table):
    req = urllib.request.Request(f"{url}/rest/v1/{table}?select=*",
                                 headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def baseline():
    """The weekly class schedule compiled into the page."""
    m = re.search(r"const DATA = (\{.*?\});", (HERE / "index.html").read_text(), re.S)
    return json.loads(m.group(1))


def to_min(hm):
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def fmt12(mins):
    h, m = divmod(mins, 60)
    ap = "pm" if h >= 12 else "am"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12}:{m:02d} {ap}"


def build(rows, data, term, taken):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    rooms = data["rooms"] + sorted(
        {r["data"].get("name") for r in rows["rooms"] if r["data"].get("name")})
    wrap = Alignment(wrap_text=True, vertical="top")
    head = Font(bold=True, size=11)

    # ---- weekday grids, 8:00 to 22:00 in five-minute rows ----
    LO, HI, STEP = 8 * 60, 22 * 60, 5
    for dow, day in DAYS.items():
        ws = wb.create_sheet(day)
        ws["A1"] = f"PIERCE COLLEGE - MUSIC - {day.upper()}"
        ws["A1"].font = Font(bold=True, size=13)
        ws.cell(row=3, column=1, value="Time").font = head
        for i, room in enumerate(rooms):
            c = ws.cell(row=3, column=2 + i, value=room)
            c.font, c.alignment = head, wrap
            ws.column_dimensions[get_column_letter(2 + i)].width = 22
        ws.column_dimensions["A"].width = 10
        for r, m in enumerate(range(LO, HI + 1, STEP)):
            cell = ws.cell(row=4 + r, column=1, value=fmt12(m) if m % 60 == 0 else None)
            cell.font = Font(size=9, color="808080")
            for i in range(len(rooms)):
                ws.cell(row=4 + r, column=2 + i).fill = PatternFill(
                    "solid", start_color=STRIPE[(m // 30) % 2])

        for b in data["baseline"]:
            if b["dow"] != dow:
                continue
            col = 2 + rooms.index(b["room"])
            r0 = 4 + (to_min(b["start"]) - LO) // STEP
            r1 = 4 + (to_min(b["end"]) - LO) // STEP - 1
            if r1 < r0:
                r1 = r0
            text = "\n".join(x for x in [b["code"], b["title"], b["instructor"],
                                         f'{fmt12(to_min(b["start"]))} - {fmt12(to_min(b["end"]))}'] if x)
            cell = ws.cell(row=r0, column=col, value=text)
            cell.alignment, cell.font = wrap, Font(size=9)
            for r in range(r0, r1 + 1):
                ws.cell(row=r, column=col).fill = PatternFill(
                    "solid", start_color=FILL.get(b["kind"], "EEEEEE"))
            if r1 > r0:
                ws.merge_cells(start_row=r0, start_column=col, end_row=r1, end_column=col)
        ws.freeze_panes = "B4"

    # ---- data sheets: the restorable part ----
    def sheet(name, cols, records):
        ws = wb.create_sheet(name)
        ws.append(cols)
        for c in ws[1]:
            c.font = head
        for rec in records:
            ws.append(rec)
        for i, col in enumerate(cols, 1):
            ws.column_dimensions[get_column_letter(i)].width = max(12, min(34, len(col) + 8))
        ws.freeze_panes = "A2"
        return ws

    res = sorted(rows["reservations"], key=lambda r: (r["data"].get("dateStart", ""), r["id"]))
    sheet("Checkouts",
          ["id", "title", "category", "person", "rooms", "weekdays", "date start", "date end",
           "time start", "time end", "note", "cancelled"],
          [[r["id"], d.get("title", ""), d.get("kind", ""), d.get("person", ""),
            "; ".join(d.get("rooms") or []),
            "; ".join(DAYNAMES.get(x, str(x)) for x in (d.get("days") or [])) or "every day",
            d.get("dateStart", ""), d.get("dateEnd", ""), d.get("timeStart", ""),
            d.get("timeEnd", ""), d.get("note", ""), "yes" if d.get("cancelled") else ""]
           for r in res for d in [r["data"]]])

    exc = sorted(rows["exceptions"], key=lambda r: (r["data"].get("date", ""), r["id"]))
    sheet("Changes",
          ["id", "block id", "date", "status", "new room", "new start", "new end", "note"],
          [[r["id"], d.get("baseId", ""), d.get("date", ""), d.get("status", ""),
            d.get("room", ""), d.get("start", ""), d.get("end", ""), d.get("note", "")]
           for r in exc for d in [r["data"]]])

    rms = sorted(rows["rooms"], key=lambda r: r["id"])
    sheet("Rooms", ["id", "name", "number", "label"],
          [[r["id"], d.get("name", ""), d.get("number", ""), d.get("label", "")]
           for r in rms for d in [r["data"]]])

    about = wb.create_sheet("About")
    for row in [["Room Checkout backup", ""],
                ["Taken", taken],
                ["Term", f"{term[0]} ({term[1]} to {term[2]})"],
                ["Checkouts", len(res)],
                ["Changes", len(exc)],
                ["Added rooms", len(rms)],
                ["Weekly class blocks", len(data["baseline"])],
                ["", ""],
                ["Restoring", "python3 restore.py <this file>  (see README)"],
                ["Note", "Checkouts, Changes and Rooms are the restorable data. "
                         "The weekday sheets are a readable copy of the class schedule."]]:
        about.append(row)
    about.column_dimensions["A"].width = 22
    about.column_dimensions["B"].width = 70
    about["A1"].font = Font(bold=True, size=13)

    del wb["Sheet"]
    return wb


def fingerprint(rows):
    """Hash of the data only, so unchanged days do not create new versions."""
    blob = json.dumps({t: sorted(([r["id"], r["data"]] for r in rows[t]), key=lambda x: x[0])
                       for t in TABLES}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="backups", help="directory for backups (default: backups)")
    args = ap.parse_args()

    url, key, term = config()
    rows = {t: fetch(url, key, t) for t in TABLES}
    data = baseline()
    taken = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    out = HERE / args.out
    out.mkdir(exist_ok=True)
    print(f"{len(rows['reservations'])} checkouts, {len(rows['exceptions'])} changes, "
          f"{len(rows['rooms'])} added rooms")

    fp = fingerprint(rows)
    marker = out / ".fingerprint"
    unchanged = marker.exists() and marker.read_text().strip() == fp

    wb = build(rows, data, term, taken)
    wb.save(out / "latest.xlsx")
    if unchanged:
        print("Data unchanged since the last backup; refreshed latest.xlsx only.")
    else:
        dated = out / f"room-checkout-{stamp}.xlsx"
        wb.save(dated)
        marker.write_text(fp + "\n")
        print(f"Wrote {dated.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
