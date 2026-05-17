# Setup Guide

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | ≥3.11 | `python --version` |
| CrewAI CLI | ≥1.14.4 | `python -m crewai --version` (or use `.venv`) |
| PostgreSQL | 14+ | Required for production; optional for dev testing |
| Twitter Developer Account | — | Required for Twitter OAuth; optional for dev testing |

## Quick Start (Development)

```bash
# 1. Navigate to project
cd D:\referral_engine

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Set your OpenAI API key
# Edit .env and replace sk-... with your actual key:
#   OPENAI_API_KEY=sk-your-key-here

# 4. Run the flow (CLI mode)
crewai run
# OR: python src/referral_engine/main.py

# 5. Start FastAPI server
uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration (.env)

All parameters are in `.env`. Critical ones:

```bash
# REQUIRED for LLM agents
OPENAI_API_KEY=sk-your-key-here

# Optional: use any OpenAI-compatible endpoint
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o

# Required for production
DATABASE_URL=postgresql://user:pass@localhost/referral_engine

# Required for Twitter features
TWITTER_CLIENT_ID=...
TWITTER_CLIENT_SECRET=...
TWITTER_REDIRECT_URI=https://your-app.com/auth/twitter/callback

# Required for webhooks
WEBHOOK_SECRET=whsec_...
```

Full `.env` reference: 50+ parameters documented in the file itself with commented sections.

## Database Setup (Production)

```sql
-- Run these migrations to create the required tables

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    account_age_days INT,
    last_active_at TIMESTAMP
);

CREATE TABLE user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    event_type VARCHAR(100),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    platform VARCHAR(50),
    handle VARCHAR(255),
    followers INT,
    following INT,
    tweet_count INT,
    engagement_rate DECIMAL(5,4),
    oauth_token_encrypted TEXT,
    oauth_refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    connected_at TIMESTAMP DEFAULT NOW(),
    last_synced_at TIMESTAMP
);

CREATE TABLE referral_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    reach_score INT,
    advocacy_score INT,
    tier VARCHAR(50),
    target_number INT,
    should_ask BOOLEAN,
    urgency DECIMAL(3,2),
    curve_payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(100) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'queued',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Dependency Management

```bash
# Install all dependencies
crewai install

# Lock dependencies (required for deployment)
uv lock

# Add a new dependency
uv add package-name

# Sync after pulling changes
uv sync
```

## Project Commands

| Command | What it does |
|---------|-------------|
| `crewai run` | Auto-detects Flow, runs `kickoff()` |
| `crewai flow kickoff` | Legacy flow runner |
| `uv run kickoff` | Direct Python entrypoint |
| `crewai deploy create` | Prepare for CrewAI Enterprise deployment |

## Development Workflow

1. **Modify `.env`** to tune parameters — no code changes needed for curve shape, budgets, thresholds
2. **Edit `core/`** for deterministic math changes (pure Python, fast iteration)
3. **Edit `tools/`** to change what the LLM sees or how core functions are called
4. **Edit `agents/`** to change role, goal, backstory, or PlanningConfig
5. **Edit `main.py`** to change Flow sequencing, error handling, or API endpoints
6. **Run tests** after changes: `python src/referral_engine/tests/test_core.py`
