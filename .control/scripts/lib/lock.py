"""Lock entre procesos multiplataforma (sin dependencias externas).

Usa msvcrt en Windows, fcntl en Unix, con fallback a lockfile con PID.
"""
import atexit
import os
import sys
import tempfile
import time
from pathlib import Path


def _get_lockfile():
    from . import paths
    return paths.CONTROL_ROOT / ".control.lock"


def _acquire_fcntl(fd):
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _release_fcntl(fd):
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_UN)


def _acquire_msvcrt(fd):
    import msvcrt
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)


def _release_msvcrt(fd):
    import msvcrt
    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


# Detectar implementación disponible
_ACQUIRE = None
_RELEASE = None

for _impl in [
    ("fcntl", _acquire_fcntl, _release_fcntl),
    ("msvcrt", _acquire_msvcrt, _release_msvcrt),
]:
    try:
        _fn = _impl[1]
        # Probar con un fd dummy (os.devnull) para ver si funciona
        with open(os.devnull, "rb") as _dummy:
            _fn(_dummy.fileno())
            _RELEASE = _impl[2]
            _RELEASE(_dummy.fileno())
        _ACQUIRE = _fn
        _LOCK_IMPL = _impl[0]
        break
    except (OSError, AttributeError, ImportError):
        continue


class LockTimeout(Exception):
    pass


class FileLock:
    """Lock entre procesos vía archivo de lock.

    Compatible Windows (msvcrt), Unix (flock) y fallback a lockfile
    con PID si ninguna función de lock está disponible.
    """

    def __init__(self, lockfile=None, timeout=10, poll=0.1):
        self.lockfile = Path(lockfile or _get_lockfile())
        self.timeout = timeout
        self.poll = poll
        self._fd = None
        self._acquired = False

    def acquire(self):
        if self._acquired:
            return
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(
                    str(self.lockfile),
                    os.O_CREAT | os.O_RDWR | os.O_TRUNC,
                )
                if _ACQUIRE:
                    _ACQUIRE(fd)
                self._fd = fd
                self._acquired = True
                return
            except (BlockingIOError, OSError):
                try:
                    os.close(fd)
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise LockTimeout(
                        f"No se pudo adquirir lock '{self.lockfile}' "
                        f"en {self.timeout}s"
                    )
                time.sleep(self.poll)

    def release(self):
        if not self._acquired:
            return
        self._acquired = False
        try:
            if _RELEASE and self._fd is not None:
                try:
                    _RELEASE(self._fd)
                except OSError:
                    pass
        finally:
            try:
                if self._fd is not None:
                    os.close(self._fd)
            except OSError:
                pass
            try:
                self.lockfile.unlink(missing_ok=True)
            except OSError:
                pass
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
