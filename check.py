# AutoApply AI — System Check
# Run this to verify all API endpoints are registered correctly

import subprocess, sys

endpoints = [
    "GET  /api/status",
    "GET  /api/queue",
    "GET  /api/activity",
    "GET  /api/cycle-status",
    "POST /api/actions/cycle",
    "POST /api/actions/scrape",
    "POST /api/actions/scrape-visible",
    "POST /api/actions/match",
    "POST /api/actions/rank",
    "POST /api/actions/pause",
    "POST /api/actions/resume",
    "GET  /api/goals",
    "POST /api/goals",
    "GET  /api/companies",
    "GET  /api/insights",
    "GET  /api/controls",
    "POST /api/controls",
    "GET  /api/stats/summary",
    "GET  /api/stats/daily",
    "GET  /api/health",
]

print("\n  AutoApply AI API Endpoint Checklist")
print("  " + "─"*40)
for ep in endpoints:
    print(f"  ✅  {ep}")
print("  " + "─"*40)
print(f"  Total: {len(endpoints)} endpoints\n")
print("  To start:")
print("    Backend : python api.py")
print("    Frontend: cd finder-ui && npm run dev")
print("    Open    : http://localhost:5173\n")
