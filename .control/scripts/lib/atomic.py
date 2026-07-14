"""Escrituras atómicas + backups automáticos.

- write(): escribe a un temporal y hace rename atómico.
- write_with_backup(): igual pero guarda copia previa en .control/.backups/
"""
import datetime
import os
import tempfile
from pathlib import Path


def _backup_dir():
    from . import paths
    d = paths.CONTROL_ROOT / ".backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write(path, content, encoding="utf-8"):
    """Escribe content al archivo path de forma atómica.

    1. Escribe a un archivo temporal en el mismo directorio.
    2. Hace os.replace (rename atómico) al destino final.

    Esto evita que otro proceso lea un archivo a medio escribir.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write_with_backup(path, content, encoding="utf-8"):
    """Escribe atómicamente, guardando backup del contenido anterior."""
    path = Path(path)
    if path.exists():
        _backup(path)
    write(path, content, encoding=encoding)


def _backup(path):
    """Copia path a .control/.backups/YYYY-MM-DD/HHMMSS-nombre."""
    bdir = _backup_dir() / datetime.date.today().isoformat()
    bdir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().strftime("%H%M%S")
    bak = bdir / f"{now}-{path.name}"
    try:
        bak.write_bytes(path.read_bytes())
    except (OSError, FileNotFoundError):
        pass
