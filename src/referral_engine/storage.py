"""storage.py -- SQLite persistence for referral curves, progress, and confirmations.

DB location: data/referral_engine.db
Auto-creates tables on first use.

Tables:
  curves               — generated referral reward curves
  user_progress        — live referral progress per user
  confirmed_referrals  — deduplication log for inbound confirms
"""

from __future__ import annotations

import json
import os
import aiosqlite
from datetime import datetime, timezone

from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
DB_PATH = os.environ.get("DB_PATH", os.path.join(_PROJECT_ROOT, "data", "referral_engine.db"))

SQL_CREATE = """
CREATE TABLE IF NOT EXISTS curves (
    user_id TEXT PRIMARY KEY,
    archetype TEXT NOT NULL,
    reach_score INTEGER NOT NULL,
    advocacy_score INTEGER NOT NULL,
    pcu INTEGER NOT NULL,
    base_reward REAL NOT NULL,
    total_budget REAL NOT NULL,
    step_count INTEGER NOT NULL,
    milestones_json TEXT NOT NULL,
    urgency REAL NOT NULL,
    penalty_factor REAL NOT NULL DEFAULT 1.0,
    should_ask INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'completed',
    channel TEXT,
    tone TEXT,
    generated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_archetype ON curves(archetype);
CREATE INDEX IF NOT EXISTS idx_generated_at ON curves(generated_at);
"""


SQL_CREATE_PROGRESS = """
CREATE TABLE IF NOT EXISTS user_progress (
    user_id TEXT PRIMARY KEY,
    referrals_completed INTEGER NOT NULL DEFAULT 0,
    referrals_target INTEGER NOT NULL DEFAULT 0,
    total_earned REAL NOT NULL DEFAULT 0.0,
    current_step INTEGER NOT NULL DEFAULT 0,
    curve_step_rewards TEXT NOT NULL DEFAULT '{}',
    archetype TEXT NOT NULL DEFAULT 'Unknown',
    friendly_label TEXT NOT NULL DEFAULT '',
    penalty_factor REAL NOT NULL DEFAULT 1.0,
    reward_unit TEXT NOT NULL DEFAULT 'points',
    status TEXT NOT NULL DEFAULT 'active',
    reasoning TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_progress_status ON user_progress(status);
"""

SQL_CREATE_CONFIRMED = """
CREATE TABLE IF NOT EXISTS confirmed_referrals (
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    confirmed_at TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_confirmed_user ON confirmed_referrals(user_id);
"""


async def _ensure_table():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SQL_CREATE)
        await db.executescript(SQL_CREATE_PROGRESS)
        await db.executescript(SQL_CREATE_CONFIRMED)
        await db.commit()


async def save_curve(user_id: str, data: dict[str, Any]) -> None:
    """Persist a generated curve for a user. Upserts if user_id exists."""
    await _ensure_table()
    milestones = json.dumps(data.get("milestones", []))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO curves
            (user_id, archetype, reach_score, advocacy_score, pcu,
             base_reward, total_budget, step_count, milestones_json,
             urgency, penalty_factor, should_ask, status, channel, tone, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("archetype", "Unknown"),
            data.get("reach_score", 0),
            data.get("advocacy_score", 0),
            data.get("pcu", 0),
            data.get("base_reward", 10),
            data.get("total_budget", 0),
            data.get("step_count", 0),
            milestones,
            data.get("urgency", 0.0),
            data.get("penalty_factor", 1.0),
            1 if data.get("should_ask") else 0,
            data.get("status", "completed"),
            data.get("channel"),
            data.get("tone"),
            data.get("generated_at", ""),
        ))
        await db.commit()


async def load_curve(user_id: str) -> dict[str, Any] | None:
    """Load a saved curve for a user. Returns None if not found."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM curves WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_dict(row)


async def list_curves(archetype: str | None = None) -> list[dict[str, Any]]:
    """List all saved curves, optionally filtered by archetype."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if archetype:
            async with db.execute(
                "SELECT * FROM curves WHERE archetype = ? ORDER BY generated_at DESC", (archetype,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute("SELECT * FROM curves ORDER BY generated_at DESC") as cursor:
                rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]


async def get_stats() -> dict[str, Any]:
    """Return aggregate stats across all saved curves."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        stats: dict[str, Any] = {"total": 0, "by_archetype": {}}
        async with db.execute("SELECT COUNT(*) as n FROM curves") as cursor:
            row = await cursor.fetchone()
            stats["total"] = row["n"] if row else 0
        async with db.execute(
            "SELECT archetype, COUNT(*) as n, AVG(total_budget) as avg_budget, AVG(step_count) as avg_steps FROM curves GROUP BY archetype"
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                stats["by_archetype"][r["archetype"]] = {
                    "count": r["n"],
                    "avg_budget": round(r["avg_budget"], 2) if r["avg_budget"] else 0,
                    "avg_steps": round(r["avg_steps"], 1) if r["avg_steps"] else 0,
                }
        return stats


async def delete_curve(user_id: str) -> bool:
    """Delete a saved curve. Returns True if deleted."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("DELETE FROM curves WHERE user_id = ?", (user_id,)) as cursor:
            deleted = cursor.rowcount > 0
        await db.commit()
        return deleted


async def save_progress(user_id: str, data: dict[str, Any]) -> None:
    """Upsert user progress row."""
    await _ensure_table()
    now = data.get("updated_at", "") or data.get("created_at", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_progress
            (user_id, referrals_completed, referrals_target, total_earned,
             current_step, curve_step_rewards, archetype, friendly_label,
             penalty_factor, reward_unit, status, reasoning, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("referrals_completed", 0),
            data.get("referrals_target", 0),
            data.get("total_earned", 0.0),
            data.get("current_step", 0),
            json.dumps(data.get("curve_step_rewards", {})),
            data.get("archetype", "Unknown"),
            data.get("friendly_label", ""),
            data.get("penalty_factor", 1.0),
            data.get("reward_unit", "points"),
            data.get("status", "active"),
            data.get("reasoning", ""),
            data.get("created_at", now),
            now,
        ))
        await db.commit()


async def load_progress(user_id: str) -> dict[str, Any] | None:
    """Load user progress. Returns None if not found."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            d = dict(row)
            try:
                d["curve_step_rewards"] = json.loads(d.get("curve_step_rewards", "{}"))
            except (json.JSONDecodeError, TypeError):
                d["curve_step_rewards"] = {}
            return d


async def update_referral_progress(user_id: str, count: int, reward: float, step: int) -> dict[str, Any]:
    """Increment referral count and earned amount. Returns updated progress."""
    await _ensure_table()
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE user_progress
            SET referrals_completed = referrals_completed + ?,
                total_earned = total_earned + ?,
                current_step = current_step + ?,
                updated_at = ?
            WHERE user_id = ?
        """, (count, reward, count, now, user_id))
        await db.commit()
    return await load_progress(user_id)


async def list_progress(status: str | None = None, archetype: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    """List all user progress rows with optional filters."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        where = []
        params: list[Any] = []
        if status:
            where.append("status = ?")
            params.append(status)
        if archetype:
            where.append("archetype = ?")
            params.append(archetype)
        if search:
            where.append("user_id LIKE ?")
            params.append(f"%{search}%")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        sql = f"SELECT * FROM user_progress {clause} ORDER BY updated_at DESC"
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["curve_step_rewards"] = json.loads(d.get("curve_step_rewards", "{}"))
            except (json.JSONDecodeError, TypeError):
                d["curve_step_rewards"] = {}
            results.append(d)
        return results


async def get_referral_history(user_id: str) -> list[dict[str, Any]]:
    """Get all confirmed referral events for a user, sorted by timestamp desc."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM confirmed_referrals WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def is_duplicate_referral(user_id: str, timestamp: str) -> bool:
    """Check if a referral for (user_id, timestamp) was already confirmed."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM confirmed_referrals WHERE user_id = ? AND timestamp = ?",
            (user_id, timestamp),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def mark_referral_confirmed(user_id: str, timestamp: str, count: int = 1) -> None:
    """Record a confirmed referral for deduplication."""
    await _ensure_table()
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO confirmed_referrals (user_id, timestamp, count, confirmed_at) VALUES (?, ?, ?, ?)",
            (user_id, timestamp, count, now),
        )
        await db.commit()


async def get_recent_confirmations(limit: int = 10) -> list[dict[str, Any]]:
    """Get most recent confirmed referral events across all users."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM confirmed_referrals ORDER BY confirmed_at DESC LIMIT ?", (limit,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_overview_stats() -> dict[str, Any]:
    """Aggregate stats across all tables for birds-eye overview."""
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as n FROM curves") as cur:
            row = await cur.fetchone()
            total_users = row["n"]

        async with db.execute(
            "SELECT COUNT(*) as n, SUM(referrals_completed) as total_refs, SUM(total_earned) as total_earned FROM user_progress"
        ) as cur:
            row = await cur.fetchone()
            active_users = row["n"] or 0
            total_referrals = row["total_refs"] or 0
            total_earned = row["total_earned"] or 0.0

        async with db.execute("SELECT COUNT(*) as n FROM user_progress WHERE status='active'") as cur:
            row = await cur.fetchone()
            currently_active = row["n"] or 0

        async with db.execute("SELECT COUNT(*) as n FROM confirmed_referrals") as cur:
            row = await cur.fetchone()
            total_confirmations = row["n"] or 0

        async with db.execute(
            "SELECT archetype, COUNT(*) as n FROM user_progress GROUP BY archetype ORDER BY n DESC"
        ) as cur:
            archetype_dist = [dict(r) for r in await cur.fetchall()]

    return {
        "total_users": total_users,
        "total_referrals_completed": total_referrals,
        "total_credits_earned": round(total_earned, 2),
        "active_users": currently_active,
        "total_users_tracked": active_users,
        "total_confirmations": total_confirmations,
        "archetype_distribution": archetype_dist,
    }


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    d = dict(row)
    try:
        d["milestones"] = json.loads(d.get("milestones_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["milestones"] = []
    d.pop("milestones_json", None)
    d["should_ask"] = bool(d.get("should_ask"))
    return d
