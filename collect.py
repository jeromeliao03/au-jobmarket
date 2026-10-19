"""collect.py - fetch Adzuna AU job ads and store them in SQLite."""
import argparse
import json
import os
import pathlib
import sqlite3
import time
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/jobs.db"
BASE_URL = "https://api.adzuna.com/v1/api/jobs/au/search/{page}"
RESULTS_PER_PAGE = 50
PAGES_PER_SEARCH = 1
DAILY_CALL_BUDGET = 5  # raise once the Adzuna account is activated

SEARCHES = [
    ("software engineer", "melbourne"),
    ("data scientist", "melbourne"),
    ("machine learning engineer", "melbourne"),
    ("backend developer", "melbourne"),
    ("cloud engineer", "melbourne"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT, company TEXT, location TEXT, category TEXT,
    contract_type TEXT, contract_time TEXT,
    salary_min REAL, salary_max REAL, salary_is_predicted INTEGER,
    description TEXT, created TEXT, redirect_url TEXT,
    first_seen TEXT, last_seen TEXT, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS api_calls (
    day TEXT PRIMARY KEY,
    calls INTEGER NOT NULL DEFAULT 0
);
"""

def connect():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn

def calls_today(conn):
    row = conn.execute(
        "SELECT calls FROM api_calls WHERE day = ?", (date.today().isoformat(),)
    ).fetchone()
    return row[0] if row else 0

def record_call(conn):
    conn.execute(
        "INSERT INTO api_calls (day, calls) VALUES (?, 1)"
        "ON CONFLICT(day) DO UPDATE SET calls = calls + 1",
        (date.today().isoformat(),),
    )
    conn.commit()

def parse_job(job):
    """Flatten one Adzuna result into a DB row. Pure function, so it's easy to test."""
    predicted = job.get("salary_is_predicted")
    return {
        "id": str(job["id"]),
        "title": job.get("title"),
        "company": (job.get("company") or {}).get("display_name"),
        "location": (job.get("location") or {}).get("display_name"),
        "category": (job.get("category") or {}).get("label"),
        "contract_type": job.get("contract_type"),
        "contract_time": job.get("contract_time"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        # Adzuna may send 0/1 or "0"/"1", so normalise to int (None if absent)
        "salary_is_predicted": None if predicted is None else int(str(predicted) == "1"),
        "description": job.get("description"),
        "created": job.get("created"),
        "redirect_url": job.get("redirect_url"),
        "raw_json": json.dumps(job),
    }

def save_jobs(conn, jobs):
    """Upsert jobs. Returns how many were new. Re-seen jobs only update last_seen."""
    today = date.today().isoformat()
    new = 0
    for job in jobs:
        row = parse_job(job)
        row["today"] = today
        exists = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (row["id"],)).fetchone()
        conn.execute(
            """
            INSERT INTO jobs (id, title, company, location, category, contract_type,
                              contract_time, salary_min, salary_max, salary_is_predicted,
                              description, created, redirect_url, first_seen, last_seen,
                              raw_json)
            VALUES (:id, :title, :company, :location, :category, :contract_type,
                    :contract_time, :salary_min, :salary_max, :salary_is_predicted,
                    :description, :created, :redirect_url, :today, :today, :raw_json)
            ON CONFLICT(id) DO UPDATE SET last_seen = :today
            """,
            row,
        )
        new += 0 if exists else 1
    conn.commit()
    return new

def fetch_page(what, where, page):
    params = {
        "app_id": os.environ["ADZUNA_APP_ID"],
        "app_key": os.environ["ADZUNA_APP_KEY"],
        "what": what,
        "where": where,
        "results_per_page": RESULTS_PER_PAGE,
        "content-type": "application/json",
    }
    r = requests.get(BASE_URL.format(page=page), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", help="load a saved API response instead of calling the API")
    args = ap.parse_args()
    conn = connect()

    if args.from_file:
        data = json.loads(pathlib.Path(args.from_file).read_text(encoding="utf-8"))
        new = save_jobs(conn, data["results"])
        print(f"loaded {len(data['results'])} jobs from file ({new} new)")
        return

    for what, where in SEARCHES:
        for page in range(1, PAGES_PER_SEARCH + 1):
            if calls_today(conn) >= DAILY_CALL_BUDGET:
                print("daily call budget reached, stopping")
                return
            record_call(conn)  # count it before the request, so failures still count
            data = fetch_page(what, where, page)
            results = data.get("results", [])
            new = save_jobs(conn, results)
            print(f"{what} / {where} / page {page}: {len(results)} fetched, {new} new")
            if not results:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()