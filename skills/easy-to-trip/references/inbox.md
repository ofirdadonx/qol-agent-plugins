# Inbox workflow

`inbox/` is the drop folder for links, screenshots, saved posts, short `.txt` / `.md` notes (a note may contain several links), and booking confirmations. `init_trip.py` creates it, together with `sources/` and an empty `inbox_items.json`.

## What the model does

1. List pending files with `python3 scripts/inbox_status.py <data-dir>` (the README is ignored).
2. Read each item. Identify the place or fact. Assign it to a destination and a category (food, sights, shopping, daytrips, or a booking / transfer / note).
3. **Verify before writing:** the place is still open; hours, prices and reviews are current (prefer the last 6–12 months); `diet_fit` is judged against the **union** of `travelers[].dietary`; a map link is added; duplicates are merged into the existing entry rather than added twice.
4. Write the structured entry to the destination JSON file, or to `inbox_items.json` when the destination or category is unclear. Record `source` (the archive path), `source_url` when there is a link, `added_by`, `added_date`, and `raw_note`.
5. **Move** the original file to `sources/` — never delete it. `python3 scripts/archive_inbox.py <data-dir> <file>` moves it to `sources/YYYY-MM-DD-slug` and prints the path to store as `source`. It refuses to archive the README, and refuses to archive a file that still has an unresolved sidecar unless you pass `--with-sidecar`.

The inbox is then empty apart from its README, ready for the next batch.

## Unresolved items

If the place cannot be identified confidently, leave the file in `inbox/` and write a sidecar `<filename>.unresolved.txt` that says what is missing. `validate_trip.py` warns when the inbox is not empty. Nothing is dropped on the floor.

## Video links

TikTok, Instagram Reels and similar links often expose only a title or caption. A screenshot of the place name, or a one-line note next to the link, helps a lot.

## Confirmations

Booking confirmations can be dropped here during onboarding. After they are recorded in `bookings.json` (and stay fields, when relevant), archive them like any other inbox file. Do not copy confirmation codes into a public repository; link to a private Drive file or a mailbox search instead.
