#!/usr/bin/env python3
"""Enforce the project runtime on Python 3.11.9."""
import sys

EXPECTED_VERSION = (3, 11, 9)

if sys.version_info[:3] != EXPECTED_VERSION:
    print(
        f"ERROR: This project requires Python {EXPECTED_VERSION[0]}.{EXPECTED_VERSION[1]}.{EXPECTED_VERSION[2]}, "
        f"but the current interpreter is {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"Python runtime verified: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
