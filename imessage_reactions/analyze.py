#!/usr/bin/env python3
"""Who gets the most tapbacks? An iMessage reaction leaderboard.

Reads the local Messages database (read-only) and reports which people's
messages attract the most reactions, and who hands them out.

Requires Full Disk Access for whatever runs it (Terminal / iTerm / your editor):
System Settings > Privacy & Security > Full Disk Access.

Usage:
    python3 analyze.py                        # everything, all time
    python3 analyze.py --days 365             # last year only
    python3 analyze.py --chat "Roommates"     # one group chat
    python3 analyze.py --min-messages 50      # drop people with tiny samples
    python3 analyze.py --db /path/to/chat.db  # a copy or a backup
"""

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict

DEFAULT_DB = os.path.expanduser("~/Library/Messages/chat.db")
ADDRESS_BOOK_GLOB = os.path.expanduser(
    "~/Library/Application Support/AddressBook/Sources/*/AddressBook-v22.abcddb"
)

# associated_message_type: 2000-range = tapback added, 3000-range = tapback removed.
# The low digit identifies which tapback it is.
TAPBACK_NAMES = {
    0: "loved",
    1: "liked",
    2: "disliked",
    3: "laughed",
    4: "emphasized",
    5: "questioned",
    6: "emoji",       # iOS 18+ arbitrary-emoji tapback
    7: "sticker",
}
APPLE_EPOCH = 978307200  # 2001-01-01 UTC, in Unix seconds


def connect(db_path):
    """Open the DB read-only. Falls back to a temp copy if the WAL is locked."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.execute("SELECT COUNT(*) FROM message LIMIT 1").fetchone()
        return con, None
    except sqlite3.OperationalError as exc:
        if "unable to open" in str(exc) and not os.path.exists(db_path):
            sys.exit(
                f"No Messages database at {db_path}.\n"
                "On a Mac it lives at ~/Library/Messages/chat.db. If it's there but "
                "unreadable, grant Full Disk Access to your terminal in "
                "System Settings > Privacy & Security."
            )
        # Locked or mid-write: copy the db plus its sidecars and read the copy.
        tmpdir = tempfile.mkdtemp(prefix="chatdb-")
        for suffix in ("", "-wal", "-shm"):
            src = db_path + suffix
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmpdir, "chat.db" + suffix))
        copy = os.path.join(tmpdir, "chat.db")
        return sqlite3.connect(f"file:{copy}?mode=ro", uri=True), tmpdir


def has_column(con, table, column):
    return any(r[1] == column for r in con.execute(f"PRAGMA table_info({table})"))


def load_contacts():
    """Best-effort phone/email -> contact name map from the local AddressBook."""
    import glob
    import re

    names = {}
    for path in glob.glob(ADDRESS_BOOK_GLOB):
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            rows = con.execute(
                """
                SELECT r.ZFIRSTNAME, r.ZLASTNAME, p.ZFULLNUMBER, NULL
                  FROM ZABCDPHONENUMBER p JOIN ZABCDRECORD r ON p.ZOWNER = r.Z_PK
                UNION ALL
                SELECT r.ZFIRSTNAME, r.ZLASTNAME, NULL, e.ZADDRESS
                  FROM ZABCDEMAILADDRESS e JOIN ZABCDRECORD r ON e.ZOWNER = r.Z_PK
                """
            ).fetchall()
            con.close()
        except sqlite3.Error:
            continue
        for first, last, phone, email in rows:
            name = " ".join(p for p in (first, last) if p).strip()
            if not name:
                continue
            if phone:
                names[re.sub(r"\D", "", phone)[-10:]] = name
            if email:
                names[email.lower()] = name
    return names


def make_labeler(contacts):
    import re

    def label(handle, is_from_me):
        if is_from_me:
            return "Me"
        if not handle:
            return "(unknown)"
        key = handle.lower() if "@" in handle else re.sub(r"\D", "", handle)[-10:]
        return contacts.get(key, handle)

    return label


def build_views(con, args):
    """Materialize two temp tables: every message, and every live tapback."""
    emoji_col = (
        "COALESCE(m.associated_message_emoji, '')"
        if has_column(con, "message", "associated_message_emoji")
        else "''"
    )

    where = ["1=1"]
    params = []
    if args.days:
        # message.date is nanoseconds since 2001-01-01 on modern macOS, seconds on
        # very old databases. Normalize before comparing.
        where.append(
            "(CASE WHEN m.date > 100000000000 THEN m.date/1000000000 ELSE m.date END)"
            " >= (strftime('%s','now') - ? * 86400) - ?"
        )
        params += [args.days, APPLE_EPOCH]

    chat_join = ""
    if args.chat:
        chat_join = """
            JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
            JOIN chat c ON c.ROWID = cmj.chat_id
        """
        where.append("(c.display_name LIKE ? OR c.chat_identifier LIKE ?)")
        params += [f"%{args.chat}%", f"%{args.chat}%"]

    con.execute(
        f"""
        CREATE TEMP TABLE msgs AS
        SELECT DISTINCT
            m.ROWID           AS rid,
            m.guid            AS guid,
            m.is_from_me      AS from_me,
            h.id              AS handle,
            m.text            AS text,
            m.date            AS date,
            m.associated_message_type AS amt,
            m.associated_message_guid AS agid,
            {emoji_col}       AS emoji
        FROM message m
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        {chat_join}
        WHERE {' AND '.join(where)}
        """,
        params,
    )

    # A tapback is its own message row pointing at its target's guid.
    # The target guid is prefixed: "p:0/<guid>" for normal messages (the digit is
    # which part of a multi-part message was hit) or "bp:<guid>" for bubble
    # messages like link previews. Strip whichever prefix is present.
    con.execute(
        """
        CREATE TEMP TABLE tapbacks_raw AS
        SELECT
            rid, guid, from_me, handle, date, emoji,
            amt % 1000 AS kind,
            amt < 3000 AS is_add,
            CASE
              WHEN instr(agid, '/') > 0 THEN substr(agid, instr(agid, '/') + 1)
              WHEN instr(agid, ':') > 0 THEN substr(agid, instr(agid, ':') + 1)
              ELSE agid
            END AS target_guid
        FROM msgs
        WHERE amt BETWEEN 2000 AND 3999 AND agid IS NOT NULL
        """
    )

    # A removed tapback is a *new* row, not a deletion, so the same
    # (reactor, target, kind) can appear as add-then-remove-then-add. Keep only
    # the most recent state of each and drop the ones that ended up removed.
    con.execute(
        """
        CREATE TEMP TABLE tapbacks AS
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY from_me, COALESCE(handle,''), target_guid, kind, emoji
                ORDER BY date DESC, rid DESC
            ) AS rn
            FROM tapbacks_raw
        )
        WHERE rn = 1 AND is_add = 1
        """
    )


def report(con, args):
    label = make_labeler({} if args.no_contacts else load_contacts())

    received = con.execute(
        """
        SELECT t.from_me AS sender_me, t.handle AS sender_handle,
               COUNT(*) AS reactions, COUNT(DISTINCT t.guid) AS msgs_reacted_to
        FROM (
            SELECT m.from_me, m.handle, m.guid
            FROM tapbacks tb JOIN msgs m ON m.guid = tb.target_guid
        ) t
        GROUP BY sender_me, sender_handle
        """
    ).fetchall()

    sent_counts = dict(
        (
            (row[0], row[1]),
            row[2],
        )
        for row in con.execute(
            """
            SELECT from_me, handle, COUNT(*)
            FROM msgs
            WHERE amt = 0 OR amt IS NULL
            GROUP BY from_me, handle
            """
        )
    )

    given = con.execute(
        """
        SELECT from_me, handle, COUNT(*) FROM tapbacks GROUP BY from_me, handle
        """
    ).fetchall()

    rows = []
    for from_me, handle, reactions, msgs_hit in received:
        sent = sent_counts.get((from_me, handle), 0)
        if sent < args.min_messages:
            continue
        rows.append(
            {
                "name": label(handle, from_me),
                "reactions": reactions,
                "sent": sent,
                "rate": 100.0 * msgs_hit / sent if sent else 0.0,
            }
        )

    if not rows:
        print("No reactions found in that scope. Try widening --days or --chat.")
        return

    print("\nMOST-REACTED-TO — total tapbacks received")
    print(f"{'person':<28}{'tapbacks':>10}{'sent':>9}{'hit rate':>10}")
    print("-" * 57)
    for r in sorted(rows, key=lambda r: -r["reactions"])[: args.top]:
        print(f"{r['name'][:27]:<28}{r['reactions']:>10}{r['sent']:>9}{r['rate']:>9.1f}%")

    print("\nBEST HIT RATE — % of their messages that drew a reaction")
    print(f"{'person':<28}{'hit rate':>10}{'tapbacks':>10}{'sent':>9}")
    print("-" * 57)
    for r in sorted(rows, key=lambda r: -r["rate"])[: args.top]:
        print(f"{r['name'][:27]:<28}{r['rate']:>9.1f}%{r['reactions']:>10}{r['sent']:>9}")

    print("\nMOST GENEROUS — tapbacks handed out")
    print(f"{'person':<28}{'given':>10}")
    print("-" * 38)
    for from_me, handle, n in sorted(given, key=lambda g: -g[2])[: args.top]:
        print(f"{label(handle, from_me)[:27]:<28}{n:>10}")

    print("\nBREAKDOWN BY TAPBACK TYPE")
    by_kind = defaultdict(int)
    for kind, emoji, n in con.execute(
        "SELECT kind, emoji, COUNT(*) FROM tapbacks GROUP BY kind, emoji"
    ):
        name = TAPBACK_NAMES.get(kind, f"type {kind}")
        by_kind[f"{name} {emoji}".strip()] += n
    for name, n in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<26}{n:>8}")

    print("\nTOP MESSAGES")
    for text, from_me, handle, n in con.execute(
        """
        SELECT m.text, m.from_me, m.handle, COUNT(*) AS n
        FROM tapbacks tb JOIN msgs m ON m.guid = tb.target_guid
        WHERE m.text IS NOT NULL AND m.text != ''
        GROUP BY m.guid ORDER BY n DESC LIMIT ?
        """,
        (args.top,),
    ):
        snippet = " ".join(text.split())[:70]
        print(f"  {n:>3}x  {label(handle, from_me)}: {snippet}")
    print()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=DEFAULT_DB, help="path to chat.db")
    p.add_argument("--days", type=int, help="only look at the last N days")
    p.add_argument("--chat", help="limit to chats matching this name or identifier")
    p.add_argument("--min-messages", type=int, default=20, help="skip people below this many messages sent")
    p.add_argument("--top", type=int, default=15, help="rows per table")
    p.add_argument("--no-contacts", action="store_true", help="show raw phone numbers instead of contact names")
    args = p.parse_args()

    con, tmpdir = connect(args.db)
    try:
        build_views(con, args)
        report(con, args)
    finally:
        con.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
