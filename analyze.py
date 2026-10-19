import json 
import sqlite3 
from collections import Counter 

import pandas as pd 

RECENT_DAYS = 90

SYNONYMS = {
    "llms": "llm", "artificial intelligence": "ai", "k8s": "kubernetes",
    "golang": "go", "node": "node.js", "nodejs": "node.js", "js": "javascript",
    "iac": "infrastructure as code", "microsoft azure": "azure",
    "powershell dsc": "dsc", "amazon web services": "aws",
}

SYNONYMS.update({"large language models": "llm", "natural language processing": "nlp"})
STOPLIST = {"ai", "devops", "automation", "cloud", "software", "hardware", "data", "infrastructure"}

def norm(s):
    s = s.strip().lower()
    return SYNONYMS.get(s,s)

df = pd.read_sql(
    """
    SELECT j.id, j.title, j.company, j.description, j.created,
           e.skills, e.seniority, e.work_mode, e.role_family
    FROM jobs j JOIN extractions e ON e.job_id = j.id
    """,
    sqlite3.connect("data/jobs.db"),
)

print("extracted ads: ", len(df))

df = df[~df.title.str.contains("translator|linguist", case=False)]
print("after removing translator/linguist junk:", len(df))

df = df.drop_duplicates(subset=["title", "company", "description"])
print("after dropping reposts:", len(df))

df["created"] = pd.to_datetime(df.created, utc=True)
print("\nads by month posted:")
print(df.created.dt.to_period("M").value_counts().sort_index())

recent = df[df.created >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=RECENT_DAYS)].copy()
print(f"\nposted in the last {RECENT_DAYS} days: {len(recent)}")

print("\nrole family:\n", recent.role_family.value_counts())
print("\nseniority:\n", recent.seniority.value_counts())
print("\nwork mode:\n", recent.work_mode.value_counts())

recent["skill_list"] = recent.skills.apply(
    lambda s: sorted({norm(x) for x in json.loads(s)} - STOPLIST)
)

print("\nads with at least one skill:", (recent.skill_list.str.len() > 0).sum(), "of", len(recent))

print("\ntop skills overall:")
for skill, n in Counter(s for lst in recent.skill_list for s in lst).most_common(20):
    print(f"  {skill:<28}{n}")

for family, group in recent.groupby("role_family"):
    if len(group) < 5:
        continue
    print(f"\n{family} ({len(group)} ads), top skills:")
    for skill, n in Counter(s for lst in group.skill_list for s in lst).most_common(8):
        print(f"  {skill:<28}{n} ({n / len(group):.0%} of ads)")
