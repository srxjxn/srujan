# iMessage reaction leaderboard

Yes, this is real. Every tapback you've ever sent or received is sitting in a
plain SQLite database on your Mac, and you can query it.

```
python3 imessage_reactions/analyze.py --days 365
```

## Where the data lives

`~/Library/Messages/chat.db` — an ordinary SQLite file. On a Mac it holds your
full iMessage history (iPhone-only history lives in encrypted backups instead;
Messages in iCloud syncs it down to the Mac). Nothing leaves your machine here:
the script opens the file read-only and prints to your terminal.

You need to grant **Full Disk Access** to whatever runs the script
(System Settings → Privacy & Security → Full Disk Access → add Terminal/iTerm).
Without it you get "unable to open database file" even though the file is right
there.

## How tapbacks are actually stored

The non-obvious part: a tapback is not a field on the message you reacted to.
It is **its own row in the `message` table**, with:

| column | meaning |
| --- | --- |
| `associated_message_type` | `2000`–`2007` = tapback added, `3000`–`3007` = tapback removed. `0` = an ordinary message. |
| `associated_message_guid` | the `guid` of the message being reacted to, prefixed |
| `associated_message_emoji` | the emoji, for iOS 18+ arbitrary-emoji tapbacks |
| `handle_id` / `is_from_me` | who did the reacting |

The low digit of the type is the reaction: `0` loved, `1` liked, `2` disliked,
`3` laughed, `4` emphasized, `5` questioned, `6` emoji, `7` sticker.

Two details that trip people up:

1. **The target guid is prefixed.** Normal messages come through as
   `p:0/<guid>`; the digit says *which part* of a multi-part message was hit, so
   in a message with three photos and a caption, `p:2/` is the third photo.
   Bubble messages (link previews, app messages) use `bp:<guid>` instead. Strip
   the prefix before joining back to `message.guid`.
2. **Removing a tapback doesn't delete anything.** It writes a *new* row in the
   3000-range. So the same person can add, remove, and re-add on one message,
   and a naive `COUNT(*)` over the 2000-range overcounts. This script keeps only
   the latest state of each (reactor, target, reaction type) and drops the ones
   that ended up removed.

Timestamps are nanoseconds since 2001-01-01 (`date/1000000000 + 978307200` for
Unix seconds); very old databases store plain seconds, which the script handles.

## What it reports

- **Most-reacted-to** — raw tapback totals received
- **Best hit rate** — share of a person's messages that drew a reaction. This is
  the more honest ranking; raw totals just reward whoever texts the most.
- **Most generous** — who hands tapbacks out
- **Breakdown by type**, and your **top individual messages**

Options: `--days N`, `--chat "Group Name"`, `--min-messages N` (default 20, to
keep tiny samples out of the hit-rate table), `--top N`, `--no-contacts`,
`--db PATH`.

Contact names are resolved best-effort from the local AddressBook; anyone not in
your contacts shows as a phone number or email.

## Caveats

- **Green bubbles.** Reactions from Android peers only land as real tapbacks
  over RCS on iOS 18+. Older SMS reactions arrive as literal text
  (`Liked "sounds good"`), which is a separate message, not a tapback row, and
  is not counted here.
- **Group chats dominate.** More people in a thread means more chances to react,
  so hit rates aren't comparable across a group chat and a 1:1. Use `--chat` to
  compare like with like.
- **`--days` windows both sides.** A tapback inside the window on a message from
  outside it has no target to attribute, so it counts in "most generous" but not
  in anyone's received total.
- **Message text can be NULL** on macOS Ventura and later — the body moved into
  a binary `attributedBody` blob. That only affects the "top messages" table,
  which skips rows with no plain text; all the counts are unaffected.
