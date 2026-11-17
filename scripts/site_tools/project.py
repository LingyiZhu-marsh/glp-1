"""Project paths shared by command entry points and helpers."""
from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parents[2]


def site_base_path(site):
    """404 pages need deployment-root URLs even when served at a missing nested URL."""
    value = os.environ.get('SITE_BASE_PATH', site.get('base_path', '/'))
    if not isinstance(value, str) or (value and not value.startswith('/')) or '//' in value or re.search(r'[\s\\?#]', value) or any(part in ('.', '..') for part in value.split('/')):
        raise ValueError('Site base path must be an absolute URL path, such as / or /project/.')
    return '/' + value.strip('/') + '/' if value.strip('/') else '/'
