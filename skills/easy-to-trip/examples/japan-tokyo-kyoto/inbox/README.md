# Inbox

Drop links, screenshots, saved posts, or short `.txt` / `.md` notes here.
A short text file may contain several links.

When the trip is next updated, each item is read, identified, checked (still open, current hours and prices, recent reviews, dietary fit, a map link, and a check for duplicates) and written into the right destination file — or into `inbox_items.json` if the destination or category is unclear.

Processed files are **moved** to `sources/` (they are not deleted) and the archive path is stored on the JSON entry as `source`. The inbox is then empty apart from this README.

If an item cannot be identified confidently, it stays here with a sidecar file named `<original>.unresolved.txt` that says what is missing.

Video links (TikTok, Instagram Reels and similar) often only expose a title or caption. A screenshot of the place name, or a one-line note, helps a lot.

Booking confirmations can also be dropped here during onboarding; the model will turn them into bookings.json rows and (for stays) destination stay fields.
