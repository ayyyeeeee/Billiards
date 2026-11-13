"""Project layout defaults; explicit roots retain the legacy fixture layout."""
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARTICIPANT_ROOT = PROJECT_ROOT / 'data' / 'participants'
OUTPUT_ROOT = PROJECT_ROOT / 'results'
ASSIGNMENTS_PATH = PROJECT_ROOT / 'data' / 'group_assignments.json'

def assignments_path(root):
    root = Path(root).resolve()
    return ASSIGNMENTS_PATH if root == PARTICIPANT_ROOT.resolve() else root / 'group_assignments.json'

def output_path(root, name):
    root = Path(root).resolve()
    return (OUTPUT_ROOT if root == PARTICIPANT_ROOT.resolve() else root) / name
