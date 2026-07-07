#!/usr/bin/env python3
"""Railway Template Publish Pipeline Orchestrator."""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from pipeline import main

if __name__ == "__main__":
    main()
