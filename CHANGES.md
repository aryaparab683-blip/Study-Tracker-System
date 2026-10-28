# QA fix pass: what changed

Verified with a 95-check backend regression suite plus real-browser checks at 1366 / 768 / 375 px.

## Bugs fixed
- **Calendar**: weekday off-by-one fixed; "No sessions" only on empty days; now a real Sun-Sat week with dates, today highlighted, Prev/Next navigation.
- **Dashboard**: Total Sessions was capped at 5 (now a real count); "Latest time" is now "Total time" (all sessions).
- **Streak**: now computed from logged sessions (consecutive days); previously never updated.
- **Cross-user data leak**: subject IDs on sessions/tasks are validated against the current user.
- **500 errors**: huge numbers, missing form fields, blank durations, missing login password all handled; styled 400/404/405/500 pages.

## Security
- CSRF tokens on every POST; all deletes, task toggle and logout are now POST-only.
- SECRET_KEY from `SECRET_KEY` env var, else a random key persisted in `instance/secret_key`.
- Debug mode only with `FLASK_DEBUG=1`. Demo account only with `STUDY_TRACKER_SEED_DEMO=1`.
- Login throttling (5 failures / 10 min per IP+email), safe `?next=` redirect, case-insensitive emails.
- Pinned Chart.js version; session cookie SameSite=Lax; optional `SESSION_COOKIE_SECURE=1`.

## Validation (server-side)
- Duration 1-1440 min; goal target 1-1,000,000 and 0 <= progress <= target; max lengths; whitespace-only names rejected;
  valid email, 8+ char passwords, valid hex colors, unique subject names (case-insensitive).
- Forms keep typed values after an error.

## Features / logic
- Sessions can be backdated (Date studied field); dates shown with year.
- Goals can be deleted; deleting a subject says how many items become unassigned.
- Pomodoro: timestamp-based (no drift), persists across pages, auto-advances focus/break, shows mode, tab-title countdown.
- Chart: empty state, offline fallback, includes unassigned "General", follows dark mode.

## UI/UX
- Mobile: scrollable one-row nav, Sessions table becomes cards, no horizontal overflow on any page, 44px touch targets.
- Long unbroken text wraps (notes, dashboard, calendar); note line breaks preserved.
- Usable color pickers, styled inline edit controls, linked labels, visible focus rings, AA contrast for delete links,
  active-nav state, per-page titles, favicon, flash messages with ARIA roles, dark-mode calendar.

## Still open (not done in this pass)
- Tasks/notes can't be edited; no UI to create or dismiss reminders; goals are still manual numbers.
- Login throttle is in-memory (use Redis/Flask-Limiter for multi-worker deploys).
- No DB migrations (schema changes still need a fresh DB) and no automated tests committed.
- "Email already exists" on register still reveals account existence.


## Design pass (round 2)
- `static/css/style.css` fully replaced: design tokens, warm paper + ink-blue accent, serif headings, solid cards, no gradients or text-shadows, proper dark mode.
- Dashboard rebuilt: time-aware greeting, This week / Streak / Sessions / Open tasks tiles, recent sessions, open tasks, notes, goals, chart, timer.
- Page headers with short descriptions; forms laid out in a grid with grouped label+field; subject chips with color dots; helpful empty states.
- Top bar with active-page underline; theme + log out grouped on the right.