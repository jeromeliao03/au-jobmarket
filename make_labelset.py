import sqlite3
import pandas as pd

df = pd.read_sql(
    "SELECT id AS job_id, title, company, description FROM jobs WHERE title NOT LIKE '%Translator%'",
    sqlite3.connect("data/jobs.db"),
)

# same add posted severel times would be labelled twice so dedupe first 
df = df.drop_duplicates(subset=["title" , "company", "description"])

sample = df.sample(n=50, random_state=42).copy()
for col in ["true_seniority", "true_work_mode", "true_role_family", "true_skills"]:
    sample[col] = ""

sample.to_csv("data/labelset.csv", index=False, encoding="utf-8-sig")
print(f"wrote {len(sample)} ads to data/labelset.csv (from {len(df)} unique)")