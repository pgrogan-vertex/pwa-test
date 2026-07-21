Adding habit fields
=====================

How to add/change what the daily check-in tracks. daily_entries is a wide
table: one row per day (entry_date PRIMARY KEY), one real column per
field. init_habits_db() in main.py runs an ALTER TABLE ADD COLUMN for any
HABIT_FIELDS key that doesn't already have a column, every time the app
starts - so adding a field is just a config edit, no manual migration,
and existing rows automatically get NULL for the new column.

(Earlier version of this file described an EAV/long-format table
(metric_entries: one row per metric per day). That was restructured on
2026-07-20 into today's wide table specifically so "today's entry" reads
back as one row instead of needing a join/pivot across N rows.)

1. Adding a new numeric field
-------------------------------
Just add an entry to HABIT_FIELDS in main.py:

    HABIT_FIELDS = [
        {"key": "sleep_hours", "label": "Sleep (hours)", "type": "number"},
        {"key": "steps", "label": "Steps", "type": "number"},
    ]

That's it. /api/habits/fields, the modal in templates/index.html, and
save_habits() all read HABIT_FIELDS dynamically. On next deploy,
init_habits_db() sees "steps" has no column yet and runs
`ALTER TABLE daily_entries ADD COLUMN "steps" NUMERIC` automatically -
existing rows get NULL for it. Verified this works locally: added a test
field, restarted the app, confirmed the column appeared and the one
existing row showed NULL for it, no data loss.

Removing a field: delete its entry from the list. The column stays in
the table (SQLite's ADD COLUMN has no matching auto-drop) with old data
intact - harmless, just unused going forward.

2. Adding a text field
------------------------
Same as above, but set "type": "text". Add "required": False if it's
optional (defaults to required if omitted):

    {"key": "notes", "label": "Notes", "type": "text", "required": False}

Gets a TEXT column instead of NUMERIC. The frontend renders a <textarea>
for text fields and only marks required ones as required. The backend
validates type-appropriately (str for text, int/float for number) via
HABIT_FIELDS_BY_KEY in main.py.

3. Renaming a field's key
---------------------------
Changing "key" in HABIT_FIELDS does NOT rename the underlying column -
init_habits_db() only adds missing columns, it doesn't rename or drop.
You'd end up with a new (empty) column under the new name and the old
column orphaned with the historical data. To actually rename and keep
history, run a one-off ALTER TABLE against the live db (see "running
one-off queries" below):

    ALTER TABLE daily_entries RENAME COLUMN "old_key" TO "new_key";

4. Other structural changes (indexes, constraints, dropping a column, etc.)
---------------------------------------------------------------------------
init_habits_db() only ever adds columns - anything beyond that (indexes,
constraints, actually dropping a column) needs a manual one-off script,
same pattern as the rename above:

  1. Write the DDL as a one-off script, same shape as scripts/dump_habits.py.
  2. Run it once against production (see below).
  3. If it's something init_habits_db() should also do for a fresh/local
     db, update that function in main.py to match.

Running one-off queries against the live database
-----------------------------------------------------
The Railway volume backing /data/habits.db isn't reachable except via SSH
into the running container (railway ssh keys already registered as of
2026-07-20). Pattern: write a small python script using stdlib sqlite3
(same DATA_DIR env var pattern as main.py), then pipe it in over stdin -
passing code inline via `python3 -c "..."` breaks because railway ssh
rejoins argv with plain spaces and loses your local shell's quoting:

    railway ssh --service pleasing-nurturing -- python3 < scripts/your_script.py

To just read every row, scripts/dump_habits.sh already does this:

    ./scripts/dump_habits.sh

After any change, remember to bump the CACHE version string in
static/sw.js if templates/index.html changed (it usually will, since the
modal is built from HABIT_FIELDS) - the service worker caches '/' and
clients won't see the new modal until the cache name changes. See the
"Architecture" section of CLAUDE.md for why.
