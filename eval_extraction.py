import json 
import sqlite3
import pandas as pd 

#small synonym map sp LLM vs LIM isnt counted as an error 

SYNONYMS = {
    "llms": "llm", "artificial intelligence": "ai", "k8s": "kubernetes",
    "golang": "go", "node": "node.js", "nodejs": "node.js", "js": "javascript",
}

def norm(s): 
    s = s.strip().lower()
    return SYNONYMS.get(s,s)

labels = pd.read_csv("data/labelset.csv", encoding="utf-8-sig", dtype={"job_id": str}).fillna("")
labels = labels[labels.true_seniority.str.strip() != ""]

preds = pd.read_sql(
    "SELECT job_id, skills, seniority, work_mode, role_family FROM extractions",
    sqlite3.connect("data/jobs.db"),
)

df = labels.merge(preds, on="job_id")
print(f"scoring {len(df)} labelled ads\n")

#categorical fields :simple accuracy 
for field in ["seniority","work_mode", "role_family"]:
    acc = (df[f"true_{field}"].str.strip().str.lower() == df[field]).mean()
    print(f"{field} accuracy: {acc:.0%}")

print("\nseniority (rows = your label, columns = model):")
print(pd.crosstab(df.true_seniority.str.strip().str.lower(), df.seniority))

# Skills: precision / recall over all ads, plus the individual mistakes
tp = fp = fn = 0
print("\nskill mistakes:")
for _, row in df.iterrows():
    true = {norm(s) for s in row.true_skills.split(";") if s.strip()}
    pred = {norm(s) for s in json.loads(row.skills)}
    tp += len(true & pred)
    fp += len(pred - true)
    fn += len(true - pred)
    if pred != true:
        print(f"  {row.title[:45]} | missed: {sorted(true - pred)} | extra: {sorted(pred - true)}")

precision = tp / (tp + fp) if tp + fp else 0
recall = tp / (tp + fn) if tp + fn else 0
f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
print(f"\nskills precision: {precision:.0%}  recall: {recall:.0%}  F1: {f1:.0%}")