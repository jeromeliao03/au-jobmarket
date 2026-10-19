import sqlite3

import pandas as pd

df = pd.read_sql("SELECT * FROM jobs", sqlite3.connect("data/jobs.db"))

print("jobs:", len(df))
print("has salary:", df.salary_min.notna().sum())
print("predicted salary:", (df.salary_is_predicted == 1).sum())
print("predicted flag missing:", df.salary_is_predicted.isna().sum())

real = df[(df.salary_is_predicted == 0) & df.salary_min.notna()]
print("real (non-predicted) salaries:", len(real))
print(real[["salary_min", "salary_max"]].describe().round(0))

print("description chars:", df.description.str.len().describe().round(0).to_dict())
print(df.category.value_counts().head(8))
print(df.contract_time.value_counts(dropna=False))
print("created range:", df.created.min(), "to", df.created.max())