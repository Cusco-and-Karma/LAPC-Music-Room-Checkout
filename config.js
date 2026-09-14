// Connection details for the Supabase project that stores checkouts and changes.
// Both values are safe to keep in a public repository: the publishable key only
// ever gets the access that the row-level security policies in schema.sql allow,
// which is read-only until someone signs in. The project's secret key is the
// one that must never appear here.
window.ROOM_CHECKOUT_CONFIG = {
  supabaseUrl:     "https://ipucjmwyxjdkvtsemqhf.supabase.co",
  supabaseAnonKey: "sb_publishable_q1OQwt1XfVCqYLEQoFRJ1Q_sF5sxbxR",

  // The term the weekly schedule in index.html covers. Outside these dates the
  // grid shows no classes; rooms can still be checked out year-round.
  // import_schedule.py rewrites this when you pass --term/--start/--end.
  term: {name: "Fall 2026", start: "2026-08-31", end: "2026-12-20"}
};
