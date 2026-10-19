import sqlite3

import pandas as pd

df = pd.read_sql(
    """
    SELECT j.title, j.company, j.location, j.description, j.created, j.redirect_url,
           e.seniority, e.role_family
    FROM jobs j JOIN extractions e ON e.job_id = j.id
    """,
    sqlite3.connect("data/jobs.db"),
)
df = df[~df.title.str.contains("translator|linguist", case=False)]
df = df.drop_duplicates(subset=["title", "company", "description"])
df["created"] = pd.to_datetime(df.created, utc=True)
df = df[df.created >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)]

print(pd.crosstab(df.role_family, df.seniority, margins=True))

entry = df[df.seniority.isin(["graduate", "junior"])].sort_values("created", ascending=False)
print(f"\n{len(entry)} entry-level ads out of {len(df)} ({len(entry) / len(df):.0%}):\n")
for _, r in entry.iterrows():
    print(f"{r.created:%Y-%m-%d} | {r.title} | {r.company} | {r.location} | {r.role_family}")
    print(f"   {r.redirect_url}")
    