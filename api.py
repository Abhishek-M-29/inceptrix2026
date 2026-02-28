import subprocess
import sys
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ScanRequest(BaseModel):
    github_url: str
    engagement_id: str


@app.post("/scan")
def start_scan(req: ScanRequest):
    subprocess.Popen([sys.executable, "agent.py", req.github_url])

    return {
        "message": "Scan started",
        "github_url": req.github_url,
        "engagement_id": req.engagement_id,
    }
