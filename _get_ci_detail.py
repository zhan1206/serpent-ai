import urllib.request
import json

# Get the job ID for the latest run, then get logs
runs_url = "https://api.github.com/repos/zhan1206/serpent-ai/actions/runs?per_page=1"
req = urllib.request.Request(runs_url)
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
run = data["workflow_runs"][0]
print(f"Latest run: {run['id']} | SHA: {run['head_sha'][:7]}")

# Get jobs
jobs_url = run["jobs_url"]
req2 = urllib.request.Request(jobs_url)
resp2 = urllib.request.urlopen(req2, timeout=10)
jobs_data = json.loads(resp2.read())

for job in jobs_data.get("jobs", []):
    print(f"\nJob: {job['name']} (ID: {job['id']})")
    # Get the log URL
    log_url = job.get("logs_url")
    if log_url:
        print(f"Log URL: {log_url}")
        req3 = urllib.request.Request(log_url)
        try:
            resp3 = urllib.request.urlopen(req3, timeout=15)
            log_text = resp3.read().decode("utf-8", errors="replace")
            # Print last 3000 chars (usually where errors are)
            print(f"--- LOG END ({len(log_text)} chars total) ---")
            print(log_text[-3000:])
        except Exception as e:
            print(f"Log fetch error: {e}")
