import sys
import os
from pathlib import Path

# Add project root to sys.path so backend modules (models, core, memory, etc.) are importable
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
