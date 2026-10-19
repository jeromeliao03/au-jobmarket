import os 
import json 
import pathlib

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.adzuna.com/v1/api/jobs/au/search/1"
params = {
    "app_id": os.environ["ADZUNA_APP_ID"],
    "app_key": os.environ["ADZUNA_APP_KEY"],
    "what": "software engineer",
    "where": "melbourne",
    "results_per_page": 5,
    "content-type": "application/json",
}

r = requests.get(URL, params=params, timeout = 30)
print("status: ", r.status_code)
print("rate-limit headers:", {k: v for k, v in r.headers.items() if "limit" in k.lower()})

if r.status_code !=200:
    print("response body:", r.text[:500])
    raise SystemExit(1)

data = r.json()

# save the full response so we never need to re-fetch it 
pathlib.Path("data").mkdir(exist_ok=True)
pathlib.Path("data/smoke_raw.txt").write_text(r.text, encoding="utf-8")

print("total matches:", data.get("count"))
for job in data.get("results", []):
    print(
        job["title"], "|", job["company"]["display_name"], "|",
        job.get("salary_min"), "-", job.get("salary_max"),
        "| predicted:", job.get("salary_is_predicted"),
        "| desc chars:", len(job["description"]),
    )