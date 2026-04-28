#!/usr/bin/env python3
"""
AutoApply AI — Cleanup Script
Removes dead legacy component files that are no longer imported anywhere.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
COMPONENTS = os.path.join(ROOT, "finder-ui", "src", "components")

# These are the OLD v1 component-based files that were replaced by page-based architecture.
# None of these are imported in App.jsx or any active page.
DEAD_FILES = [
    os.path.join(COMPONENTS, "Dashboard.jsx"),
    os.path.join(COMPONENTS, "Controls.jsx"),
    os.path.join(COMPONENTS, "Queue.jsx"),
    os.path.join(COMPONENTS, "Goals.jsx"),
    os.path.join(COMPONENTS, "Intelligence.jsx"),
    os.path.join(COMPONENTS, "CycleTimer.jsx"),
    os.path.join(COMPONENTS, "Skeleton.jsx"),
    os.path.join(COMPONENTS, "Shared.jsx"),
    os.path.join(ROOT, "cleanup_dead_files.py"),  # self-delete
]

print("\n  AutoApply AI — Dead File Cleanup")
print("  " + "─" * 40)
removed = 0
for f in DEAD_FILES:
    if os.path.exists(f):
        os.remove(f)
        print(f"  ✅ Removed: {os.path.relpath(f, ROOT)}")
        removed += 1
    else:
        print(f"  ⚠️  Not found: {os.path.relpath(f, ROOT)}")

print("  " + "─" * 40)
print(f"  Done. Removed {removed} file(s).\n")
