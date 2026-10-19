import sqlite3

import pandas as pd

df = pd.read_sql(
    """
    SELECT j.title, j.company, j.created, j.redirect_url, e.seniority
    FROM jobs j JOIN extractions e ON e.job_id = j.id
    """,
    sqlite3.connect("data/jobs.db"),
)

pattern = r"\bgraduate\b|\bgrad\b|\bintern(?:ship)?\b|\bjunior\b|\bentry[- ]level\b|\btrainee\b|\bapprentice\b|\bcadet\b"
hits = df[df.title.str.contains(pattern, case=False, regex=True)].drop_duplicates(
    subset=["title", "company"]
)
missed = hits[~hits.seniority.isin(["graduate", "junior"])]

print(f"title keywords matched {len(hits)} ads; extractor called {len(hits) - len(missed)} graduate/junior")
for _, r in missed.iterrows():
    print(f"{r.created[:10]} | {r.title} | {r.company} | extractor said: {r.seniority}")
    print(f"   {r.redirect_url}")