# Session Update — 2026-05-18

## Quick Summary

Landing page fully integrated with FastAPI backend. Videos are scroll-activated with mutual exclusion audio. New user search page. Code pushed to GitHub with full README and env template.

---

## Changes Made

### 1. Landing Page — Video & Audio

| Feature | Before | After |
|---------|--------|-------|
| Video playback | All videos autoplayed simultaneously | Scroll-triggered via IntersectionObserver (≥25% visible threshold) |
| Audio | Browser-blocked unmuted autoplay | Splash screen unlocks audio on first user click/scroll/key |
| Mutual exclusion | Multiple videos could play together | Only one video plays at a time (pauses previous) |
| Sound toggle | Small button | Bigger padding (14×22px), amber glow animation when ON |
| Marquee band | Yellow ticker banner | **Removed** per request |

**Files:** `C:\Users\Aadith\referral-engine\main.js`, `index.html`, `style.css`

### 2. Backend — Landing Page Routes

Added static file serving to `src/referral_engine/main.py`:

| Route | File |
|-------|------|
| `GET /` | `index.html` (landing page) |
| `GET /style.css` | `style.css` |
| `GET /main.js` | `main.js` |
| `GET /assets/{filename}` | Video assets (path-safe, no traversal) |

Landing page directory is configurable via `LANDING_PAGE_DIR` env var (defaults to `C:\Users\Aadith\referral-engine` on Windows).

### 3. Navigation Links Fixed

| Page | Old Link | New Link |
|------|----------|----------|
| Landing page nav | `/curves` | `/dashboard` |
| Landing page nav | `/user` | `/users` |
| Floating tab | `/curves` | `/dashboard` |
| Dashboard header | — | **Added** `Landing` → `/` |

### 4. New User Search Page

**Route:** `GET /users` → `templates/users.html`

- Search bar (filters `/api/user/progress?search={query}`)
- Quick links: `user_123`, `user_456`, "Show all"
- Displays: user ID, archetype badge, referrals, credits
- "View" button links to `/user/{user_id}`

### 5. Server Startup Script

**File:** `start.py` (new)

```powershell
python start.py        # Auto-detects free port (starts at 8000)
DEV=1 python start.py  # Enables --reload
```

- Auto-detects available port via `socket.connect_ex`
- Uses venv Python if `.venv\Scripts\python.exe` exists
- Configurable: `HOST`, `PORT`, `DEV`, `LANDING_PAGE_DIR`
- Removed emojis to fix Windows cp1252 encoding crash

### 6. GitHub Repository

- **Repo:** https://github.com/Aadithkl/referral-engine
- **Initial commit:** 68 files, 14,800 lines
- **README.md:** Comprehensive docs (features, API endpoints, architecture, installation, deployment)
- **.env.example:** Template with all environment variables (no real values)

---

## Files Modified

### Backend (`D:\referral_engine\`)
- `src/referral_engine/main.py` — Added landing page routes, `/users` route
- `templates/users.html` — New user search interface
- `templates/dashboard.html` — Added "Landing" nav link
- `README.md` — Full project documentation
- `.env.example` — Template environment variables (new)
- `start.py` — Server startup script (new)
- `.gitignore` — Added `.venv/`, `*.egg-info/`, etc.

### Landing Page (`C:\Users\Aadith\referral-engine\`)
- `index.html` — Fixed nav links, removed marquee band
- `main.js` — IntersectionObserver, mutual exclusion, splash/audio logic
- `style.css` — Splash screen, sound toggle glow, removed marquee styles

---

## How to Run

```powershell
cd D:\referral_engine
python start.py
```

**Test URLs:**
- Landing: http://localhost:8000/
- User search: http://localhost:8000/users
- Dashboard: http://localhost:8000/dashboard
- Overview: http://localhost:8000/overview
- Health: http://localhost:8000/health

---

## What's Still Separate

The landing page assets (`index.html`, `style.css`, `main.js`, video clips) live in `C:\Users\Aadith\referral-engine\` — **not** in the GitHub repo. They are served by the backend via `FileResponse` routes. To make the project self-contained, copy them into `D:\referral_engine\static\` and update `LANDING_PAGE_DIR`.

---

## Next Steps (If Needed)

| # | Task | Why |
|---|------|-----|
| 1 | Move landing page into repo | Self-contained deployment |
| 2 | Add `Dockerfile` | Containerized deployment |
| 3 | Add API auth middleware | Production security |
| 4 | PostgreSQL migration | Scale beyond SQLite |
| 5 | Re-enable tools on Agent 1 | Full tool-based pipeline |
