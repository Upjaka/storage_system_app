"""Application directory paths — dev source tree or PyInstaller bundle."""

import sys
from pathlib import Path


def _source_dir() -> Path:
    return Path(__file__).resolve().parent


def app_dir() -> Path:
    """Writable app root — source tree in dev, exe folder when frozen."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return _source_dir()


def resource_dir() -> Path:
    """Read-only bundled resources — config, assets, icons."""
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', app_dir()))
    return _source_dir()
