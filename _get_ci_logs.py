import urllib.request
import json

# Get the latest runs first to find the correct run ID
url = "https://api.github.com/repos/zhan1206/serpent-ai/actions/runs?per_page=5"
req = urllib.request.Request(url)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    for run in data.get("workflow_runs", []):
        print(f"Run ID: {run['id']}")
        print(f"  Status: {run['conclusion']} | Branch: {run['head_branch']} | SHA: {run['head_sha'][:7]}")
        print(f"  Created: {run['created_at']}")
        # Get jobs for this run
        jobs_url = run["jobs_url"]
        req2 = urllib.request.Request(jobs_url)
        try:
            resp2 = urllib.request.urlopen(req2, timeout=10)
            jobs_data = json.loads(resp2.read())
            for job in jobs_data.get("jobs", []):
                print(f"  Job: {job['name']} -> {job['conclusion']}")
                for step in job.get("steps", []):
                    if step["conclusion"] == "failure":
                        print(f"    FAILED: {step['name']}")
        except Exception as e2:
            print(f"  Jobs error: {e2}")
        print()
except Exception as e:
    print(f"Error: {e}")
