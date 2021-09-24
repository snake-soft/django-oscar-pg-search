import os
from pathlib import Path


def get_version():
    path = Path(str(Path(__file__).parent.parent.parent) + os.sep + 'VERSION')
    if path.is_file():
        with open(path) as f:
            return f.read().strip()
    return '0.0.0'


__version__ = get_version()
