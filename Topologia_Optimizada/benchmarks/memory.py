"""Medición de memoria pico por RSS del proceso (Fase 3).

``tracemalloc`` solo ve las allocaciones de Python; Kratos hace la mayor parte de
su memoria (nodos, elementos, matrices sparse y vectores en C++/nativo), que
``tracemalloc`` no mide (por eso en la Fase 0 ``peak_memory_kb`` infraestimaba y
no capturaba el consumo real del solve). Además ``tracemalloc`` añade overhead a
cada allocación de Python.

Aquí se muestrea el **Working Set Size (WSS / RSS)** del proceso con ``ctypes``
(sin dependencia externa; en Windows vía ``psapi``, en Unix vía ``/proc``) y se
reporta el pico alcanzado durante la corrida. Devuelve bytes; el caller convierte
a kB.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import threading
import time
from typing import Optional

_WIN_PSAPI = None
if os.name == "nt":
    # psapi: K32GetProcessMemoryInfo / GetProcessMemoryInfo
    _WIN_PSAPI = ctypes.WinDLL("psapi") if hasattr(ctypes, "WinDLL") else None

    class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wt.DWORD),
            ("PageFaultCount", wt.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    if _WIN_PSAPI is not None:
        _WIN_PSAPI.GetProcessMemoryInfo.restype = wt.BOOL
        _WIN_PSAPI.GetProcessMemoryInfo.argtypes = [
            wt.HANDLE,
            ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
            wt.DWORD,
        ]


def _current_rss_bytes() -> Optional[int]:
    """RSS (Working Set) en bytes del proceso actual, o None si no se puede medir."""
    if os.name == "nt" and _WIN_PSAPI is not None:
        try:
            counters = _PROCESS_MEMORY_COUNTERS()
            handles = ctypes.windll.kernel32.GetCurrentProcess()
            ok = _WIN_PSAPI.GetProcessMemoryInfo(
                handles, ctypes.byref(counters), ctypes.sizeof(counters)
            )
            if ok:
                return int(counters.WorkingSetSize)
        except Exception:
            return None
        return None

    # Unix (Linux): /proc/self/statm -> rss en páginas * page_size
    try:
        page = os.sysconf("SC_PAGESIZE")
        with open("/proc/self/statm", "r") as fh:
            fields = fh.read().split()
        return int(fields[1]) * page  # rss (resident) en páginas
    except Exception:
        return None


class PeakRSS:
    """Muestrea el RSS del proceso en un hilo en segundo plano y guarda el pico.

    Uso:
        mon = PeakRSS()
        mon.start()
        ... ejecutar el trabajo ...
        mon.stop()
        peak_bytes = mon.peak
    """

    def __init__(self, interval: float = 0.05) -> None:
        self.interval = interval
        self._peak = 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def peak(self) -> int:
        return self._peak

    def _run(self) -> None:
        while not self._stop.is_set():
            rss = _current_rss_bytes()
            if rss is not None and rss > self._peak:
                self._peak = rss
            self._stop.wait(self.interval)

    def start(self) -> "PeakRSS":
        if self._thread is None:
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name="peak-rss", daemon=True
            )
            self._thread.start()
        return self

    def stop(self) -> int:
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=self.interval * 2)
            self._thread = None
        rss = _current_rss_bytes()
        if rss is not None and rss > self._peak:
            self._peak = rss
        return self._peak
