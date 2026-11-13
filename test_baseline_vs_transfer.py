"""Compatibility entry; implementation lives in the named package."""
import importlib
import runpy
import sys
from pathlib import Path
for _parent in Path(__file__).resolve().parents:
    if (_parent / 'common' / 'paths.py').is_file():
        sys.path.insert(0, str(_parent))
        break
if __name__ == '__main__':
    runpy.run_module('tests.plots.test_baseline_vs_transfer', run_name='__main__')
else:
    sys.modules[__name__] = importlib.import_module('tests.plots.test_baseline_vs_transfer')
