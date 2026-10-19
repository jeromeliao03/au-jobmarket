"""extract.py - use an LLM to turn job-ad snippets into structured fields."""
import argparse
import json
import os
import sqlite3

from anthropic import Anthropic 
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/jobs.db"
MODEL = os.getenv("EXTRACT_MODEL", "claude-haiku-4-5-20251001")
client = Anthropic()

SENIORITY = {"graduate", "junior", "mid", "senior", "lead", "unknown"}
WORK_MODE = {"onsite", "hybrid", "remote", "unknown"}
ROLE_FAMILY = {
    "software_engineering", "data_science", "ml_ai",
    "data_engineering", "devops_cloud", "other",
}

SYSTEM = """You extract structured data from a job ad snippet (about 500 characters, often cut off).
Return ONLY a JSON object with these keys:
- "skills": specific technologies the candidate is expected to know or use: languages, frameworks, databases, cloud services, tools (e.g. "python", "react", "terraform", "azure devops"). Do NOT include what the company does, what the team works on, or the general field of the role (e.g. "ai", "cloud", "devops", "software", "hardware", "robotics"). Do NOT include service-model acronyms (iaas, paas, saas, caas). Generic methods such as "machine learning" or "data analysis" count only when listed as required expertise for the role.
- "seniority": one of "graduate", "junior", "mid", "senior", "lead", "unknown"
- "work_mode": one of "onsite", "hybrid", "remote", "unknown"
- "role_family": one of "software_engineering", "data_science", "ml_ai", "data_engineering", "devops_cloud", "other"
- "min_years_experience": integer or null
Only use what the text actually says. If something is not stated, use "unknown", null or an empty list. Never guess."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS extractions (
    job_id TEXT PRIMARY KEY,
    skills TEXT, seniority TEXT, work_mode TEXT, role_family TEXT,
    min_years INTEGER, model TEXT
);
"""


def parse(text):
    """Pull the JSON object out of the reply, tolerating code fences or extra text."""
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def clean(d):
    """Validate against the allowed values so one bad reply can't pollute the data."""
    years = d.get("min_years_experience")
    return {
        "skills": sorted({s.strip().lower() for s in d.get("skills", [])
                          if isinstance(s, str) and s.strip()}),
        "seniority": d.get("seniority") if d.get("seniority") in SENIORITY else "unknown",
        "work_mode": d.get("work_mode") if d.get("work_mode") in WORK_MODE else "unknown",
        "role_family": d.get("role_family") if d.get("role_family") in ROLE_FAMILY else "other",
        "min_years": years if isinstance(years, int) else None,
    }


def extract(title, description):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Title: {title}\n\nSnippet: {description}"}],
    )
    return clean(parse(resp.content[0].text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only process this many jobs")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    # Only jobs we haven't extracted yet, so re-runs are cheap and safe
    query = ("SELECT id, title, description FROM jobs "
             "WHERE id NOT IN (SELECT job_id FROM extractions)")
    if args.limit:
        query += f" LIMIT {int(args.limit)}"
    rows = conn.execute(query).fetchall()

    for i, (job_id, title, description) in enumerate(rows, 1):
        try:
            r = extract(title, description)
        except Exception as e:  # bad JSON, API hiccup: skip it, retry on the next run
            print(f"[{i}/{len(rows)}] SKIPPED {job_id}: {e}")
            continue
        conn.execute(
            "INSERT INTO extractions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, json.dumps(r["skills"]), r["seniority"], r["work_mode"],
             r["role_family"], r["min_years"], MODEL),
        )
        conn.commit()
        print(f"[{i}/{len(rows)}] {title[:50]} -> {r['seniority']}, {r['role_family']}, {r['skills'][:5]}")


if __name__ == "__main__":
    main()