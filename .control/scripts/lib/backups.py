"""Creación de backups completos de .control/ en .control/.backups/."""

import datetime
import shutil
from pathlib import Path

from . import paths


def create_backup(tag=None):
    """Crea un backup completo de .control/ en .control/.backups/.

    El backup es una copia del directorio .control/ (excluyendo .backups/
    y .git) a un subdirectorio con timestamp.
    """
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{tag}" if tag else ""
    dest = paths.BACKUPS_DIR / f"backup_{ts}{suffix}"
    dest.mkdir(parents=True, exist_ok=True)

    def _ignore(src, names):
        rel = Path(src).relative_to(paths.CONTROL_ROOT)
        return [n for n in names if rel == Path(".") and n in (".backups", ".git")]

    shutil.copytree(
        str(paths.CONTROL_ROOT),
        str(dest),
        ignore=_ignore,
        dirs_exist_ok=True,
    )
    return dest
