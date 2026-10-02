"""Own quota subprocess descendants so inherited pipes cannot outlive a query."""
from __future__ import annotations

import os
import signal
import subprocess


def start(command: list[str], **kwargs):
    if os.name != "nt":
        return subprocess.Popen(command, start_new_session=True, **kwargs), None
    # Suspend before Python returns the process: binding a running node wrapper
    # to a job can race with its native child. No app-server code runs unowned.
    proc = subprocess.Popen(command, creationflags=0x00000004, **kwargs)
    try:
        job = _windows_job(proc)
        return proc, job
    except Exception:
        proc.kill()
        proc.wait(timeout=2)
        for pipe in (proc.stdin, proc.stdout):
            if pipe:
                pipe.close()
        raise


def stop(proc: subprocess.Popen, job) -> None:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        close = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        if not close(job):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=1)
    finally:
        if os.name != "nt":
            # The parent may have exited while a child ignored SIGTERM.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def _windows_job(proc):
    import ctypes
    from ctypes import wintypes as w

    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64), ("flags", w.DWORD),
                    ("min_working_set", ctypes.c_size_t), ("max_working_set", ctypes.c_size_t),
                    ("active_processes", w.DWORD), ("affinity", ctypes.c_size_t),
                    ("priority", w.DWORD), ("scheduling", w.DWORD)]

    class Limits(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", ctypes.c_uint64 * 6),
                    ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                    ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]

    class Thread(ctypes.Structure):
        _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("id", w.DWORD), ("owner", w.DWORD),
                    ("base_priority", w.LONG), ("delta_priority", w.LONG), ("flags", w.DWORD)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "CreateToolhelp32Snapshot": ([w.DWORD, w.DWORD], w.HANDLE),
        "Thread32First": ([w.HANDLE, ctypes.POINTER(Thread)], w.BOOL),
        "Thread32Next": ([w.HANDLE, ctypes.POINTER(Thread)], w.BOOL),
        "OpenThread": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        "ResumeThread": ([w.HANDLE], w.DWORD),
        "CloseHandle": ([w.HANDLE], w.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        limits = Limits()
        limits.basic.flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.AssignProcessToJobObject(job, w.HANDLE(int(proc._handle))):
            raise ctypes.WinError(ctypes.get_last_error())
        snapshot = kernel.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
        if snapshot == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            thread = Thread()
            thread.size = ctypes.sizeof(Thread)
            exists = kernel.Thread32First(snapshot, ctypes.byref(thread))
            while exists:
                if thread.owner == proc.pid:
                    handle = kernel.OpenThread(0x0002, False, thread.id)  # THREAD_SUSPEND_RESUME
                    if not handle:
                        raise ctypes.WinError(ctypes.get_last_error())
                    try:
                        if kernel.ResumeThread(handle) == 0xFFFFFFFF:
                            raise ctypes.WinError(ctypes.get_last_error())
                    finally:
                        kernel.CloseHandle(handle)
                    return job
                exists = kernel.Thread32Next(snapshot, ctypes.byref(thread))
            raise OSError("Could not resume owned app-server process")
        finally:
            kernel.CloseHandle(snapshot)
    except Exception:
        kernel.CloseHandle(job)
        raise
