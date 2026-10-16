---
description: how to run datavex locally (backend + frontend)
---

## Prerequisites (one-time, on a fresh device)

```bash
# Python 3.10+ required
python3 --version

# Node 20+ required
node --version
```

## 1. Clone / copy the project

If transferring via Git:
```bash
git clone <your-repo-url>
cd datavex
```

## 2. Set up the Python environment (backend + pipeline)

```bash
# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install backend deps
pip install -r backend/requirements.txt

# Install pipeline deps
pip install -r datavex_pipeline/requirements.txt

# Seed the database with all companies (run once after install)
python3 seed_db.py
```

> NOTE: If psycopg2-binary fails to install, that's fine — the app falls back to local SQLite automatically.

## 3. Environment variables (optional)

Create a `.env` file in the project root if you want LLM support:
```
BYTEZ_API_KEY=your_key_here
```

Without this, the pipeline runs in OFFLINE mode (rule-based, no LLM calls). Everything still works.

## 4. Run the backend

```bash
# From project root, with virtualenv active
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend is ready when you see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## 5. Run the frontend

Open a NEW terminal tab (keep the backend running):

```bash
# From project root
npm install      # first time only
npm run dev
```

Frontend is ready when you see:
```
  ➜  Local:   http://localhost:5173/
```

## 6. Open the app

Go to: **http://localhost:5173**

Login with: `admin` / `admin`

---

## Quick re-run (after first setup)

Terminal 1:
```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2:
```bash
npm run dev
```

---

## Notes

- The SQLite DB (`backend/datavex.db`) stores all company data. Copy this file to the new device to keep existing companies.
- `datavex_pipeline/search_cache.json` stores signal data. Copy this too.
- If you want a fresh DB, just delete `backend/datavex.db` — it will be recreated on next startup.
