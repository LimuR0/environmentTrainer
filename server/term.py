"""跨平台终端后端。

三种实现，按平台/能力自动选择：

  * PosixPTY  —— macOS / Linux，用 pty.openpty() + setsid，最完整
  * WinConPTY —— Windows 10 1809+ / 11 / Server 2019+，用 ConPTY（kernel32!CreatePseudoConsole）
  * PipeFallback —— 任何平台都能用的兜底：docker exec -i + 管道

统一接口：start() / read() / write() / resize() / terminate() / mode
`read()` 是阻塞的，读到 EOF 返回 b""；调用 terminate() 会打断阻塞的 read()。
"""
from __future__ import annotations

import os
import subprocess
import sys

from platform_util import IS_WIN, NO_WINDOW

PTY = "pty"
CONPTY = "conpty"
PIPE = "pipe"

_MODE_LABEL = {
    PTY: "pty",
    CONPTY: "conpty",
    PIPE: "兼容模式（无 TTY）",
}


class TerminalError(RuntimeError):
    pass


class TerminalBase:
    mode = "base"

    def __init__(self, argv, cols=100, rows=30, env=None, cwd=None):
        self.argv = list(argv)
        self.cols = max(20, int(cols))
        self.rows = max(6, int(rows))
        self.env = env if env is not None else dict(os.environ)
        self.cwd = cwd
        self.proc = None

    # --- 子类实现 ---
    def start(self):
        raise NotImplementedError

    def read(self, n=65536):
        raise NotImplementedError

    def write(self, data):
        raise NotImplementedError

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows

    def terminate(self):
        raise NotImplementedError


# ---------------------------------------------------------------- POSIX
class PosixPTY(TerminalBase):
    mode = PTY

    def start(self):
        import fcntl
        import pty
        import struct
        import termios

        self._fcntl = fcntl
        self._struct = struct
        self._termios = termios

        master, slave = pty.openpty()
        self._set_winsize(master, self.cols, self.rows)
        try:
            self.proc = subprocess.Popen(
                self.argv,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                preexec_fn=os.setsid,
                close_fds=True,
                env=self.env,
                cwd=self.cwd,
            )
        finally:
            os.close(slave)
        self.master = master

    def _set_winsize(self, fd, cols, rows):
        self._fcntl.ioctl(
            fd, self._termios.TIOCSWINSZ, self._struct.pack("HHHH", rows, cols, 0, 0)
        )

    def read(self, n=65536):
        try:
            return os.read(self.master, n)
        except OSError:
            return b""

    def write(self, data):
        if not data:
            return
        view = memoryview(data)
        while view:
            try:
                written = os.write(self.master, view)
            except OSError:
                return
            view = view[written:]

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows
        try:
            self._set_winsize(self.master, cols, rows)
        except Exception:
            pass

    def terminate(self):
        import signal

        if self.proc is not None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    self.proc.terminate()
                except Exception:
                    pass
            try:
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        try:
            os.close(self.master)
        except Exception:
            pass


# ---------------------------------------------------------------- Windows ConPTY
class WinConPTY(TerminalBase):
    mode = CONPTY

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._k32 = None
        self._hpcon = None
        self._hprocess = None
        self._in_fd = None
        self._out_fd = None

    def start(self):
        import ctypes
        import msvcrt
        from ctypes import wintypes as wt

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._ctypes = ctypes
        self._k32 = k32

        if not hasattr(k32, "CreatePseudoConsole"):
            raise TerminalError("当前系统没有 ConPTY（需要 Windows 10 1809+）")

        HANDLE = wt.HANDLE
        DWORD = wt.DWORD
        WORD = wt.WORD

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ("cb", DWORD),
                ("lpReserved", wt.LPWSTR),
                ("lpDesktop", wt.LPWSTR),
                ("lpTitle", wt.LPWSTR),
                ("dwX", DWORD),
                ("dwY", DWORD),
                ("dwXSize", DWORD),
                ("dwYSize", DWORD),
                ("dwXCountChars", DWORD),
                ("dwYCountChars", DWORD),
                ("dwFillAttribute", DWORD),
                ("dwFlags", DWORD),
                ("wShowWindow", WORD),
                ("cbReserved2", WORD),
                ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
                ("hStdInput", HANDLE),
                ("hStdOutput", HANDLE),
                ("hStdError", HANDLE),
            ]

        class STARTUPINFOEXW(ctypes.Structure):
            _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", HANDLE),
                ("hThread", HANDLE),
                ("dwProcessId", DWORD),
                ("dwThreadId", DWORD),
            ]

        self._COORD = COORD

        k32.CreatePseudoConsole.argtypes = [COORD, HANDLE, HANDLE, DWORD, ctypes.POINTER(HANDLE)]
        k32.CreatePseudoConsole.restype = ctypes.c_long
        k32.ResizePseudoConsole.argtypes = [HANDLE, COORD]
        k32.ResizePseudoConsole.restype = ctypes.c_long
        k32.ClosePseudoConsole.argtypes = [HANDLE]
        k32.CreatePipe.argtypes = [
            ctypes.POINTER(HANDLE),
            ctypes.POINTER(HANDLE),
            ctypes.c_void_p,
            DWORD,
        ]
        k32.CreatePipe.restype = wt.BOOL
        k32.InitializeProcThreadAttributeList.argtypes = [
            ctypes.c_void_p,
            DWORD,
            DWORD,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        k32.InitializeProcThreadAttributeList.restype = wt.BOOL
        k32.UpdateProcThreadAttribute.argtypes = [
            ctypes.c_void_p,
            DWORD,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        k32.UpdateProcThreadAttribute.restype = wt.BOOL
        k32.CreateProcessW.argtypes = [
            wt.LPCWSTR,
            wt.LPWSTR,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wt.BOOL,
            DWORD,
            ctypes.c_void_p,
            wt.LPCWSTR,
            ctypes.POINTER(STARTUPINFOEXW),
            ctypes.POINTER(PROCESS_INFORMATION),
        ]
        k32.CreateProcessW.restype = wt.BOOL

        # 64 位下必须显式声明指针参数类型，否则 ctypes 会按 int 截断句柄
        k32.CloseHandle.argtypes = [HANDLE]
        k32.CloseHandle.restype = wt.BOOL
        k32.TerminateProcess.argtypes = [HANDLE, ctypes.c_uint]
        k32.TerminateProcess.restype = wt.BOOL
        k32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
        k32.DeleteProcThreadAttributeList.restype = None

        h_in_r, h_in_w = HANDLE(), HANDLE()
        h_out_r, h_out_w = HANDLE(), HANDLE()
        if not k32.CreatePipe(ctypes.byref(h_in_r), ctypes.byref(h_in_w), None, 0):
            raise TerminalError(f"CreatePipe 失败: {ctypes.get_last_error()}")
        if not k32.CreatePipe(ctypes.byref(h_out_r), ctypes.byref(h_out_w), None, 0):
            raise TerminalError(f"CreatePipe 失败: {ctypes.get_last_error()}")

        hpcon = HANDLE()
        hr = k32.CreatePseudoConsole(
            COORD(self.cols, self.rows), h_in_r, h_out_w, 0, ctypes.byref(hpcon)
        )
        if hr != 0:
            raise TerminalError(f"CreatePseudoConsole 失败: 0x{hr & 0xFFFFFFFF:08X}")
        k32.CloseHandle(h_in_r)
        k32.CloseHandle(h_out_w)

        size = ctypes.c_size_t(0)
        k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        attr = ctypes.create_string_buffer(size.value)
        attr_ptr = ctypes.cast(attr, ctypes.c_void_p)
        if not k32.InitializeProcThreadAttributeList(attr_ptr, 1, 0, ctypes.byref(size)):
            raise TerminalError(f"InitializeProcThreadAttributeList 失败: {ctypes.get_last_error()}")
        try:
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
            if not k32.UpdateProcThreadAttribute(
                attr_ptr,
                0,
                PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                ctypes.byref(hpcon),
                ctypes.sizeof(HANDLE),
                None,
                None,
            ):
                raise TerminalError(f"UpdateProcThreadAttribute 失败: {ctypes.get_last_error()}")

            si = STARTUPINFOEXW()
            si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            si.lpAttributeList = attr_ptr
            pi = PROCESS_INFORMATION()
            cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(self.argv))
            EXTENDED_STARTUPINFO_PRESENT = 0x00080000
            if not k32.CreateProcessW(
                None,
                cmdline,
                None,
                None,
                False,
                EXTENDED_STARTUPINFO_PRESENT,
                None,
                self.cwd,
                ctypes.byref(si),
                ctypes.byref(pi),
            ):
                raise TerminalError(f"CreateProcessW 失败: {ctypes.get_last_error()}")
        except Exception:
            k32.ClosePseudoConsole(hpcon)
            raise
        finally:
            try:
                k32.DeleteProcThreadAttributeList(attr_ptr)
            except Exception:
                pass

        k32.CloseHandle(pi.hThread)
        self._hpcon = hpcon
        self._hprocess = pi.hProcess
        # O_BINARY 必须有：否则 CRT 会把 \n 转成 \r\n，终端输出全乱
        binary = getattr(os, "O_BINARY", 0)
        self._in_fd = msvcrt.open_osfhandle(int(h_in_w.value), os.O_WRONLY | binary)
        self._out_fd = msvcrt.open_osfhandle(int(h_out_r.value), os.O_RDONLY | binary)

    def read(self, n=65536):
        if self._out_fd is None:
            return b""
        try:
            return os.read(self._out_fd, n)
        except OSError:
            return b""

    def write(self, data):
        if not data or self._in_fd is None:
            return
        view = memoryview(data)
        while view:
            try:
                written = os.write(self._in_fd, view)
            except OSError:
                return
            if written <= 0:
                return
            view = view[written:]

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows
        if self._hpcon is None:
            return
        try:
            self._k32.ResizePseudoConsole(self._hpcon, self._COORD(cols, rows))
        except Exception:
            pass

    def terminate(self):
        k32, ctypes = self._k32, self._ctypes
        try:
            if self._hprocess is not None:
                k32.TerminateProcess(self._hprocess, 1)
                k32.CloseHandle(self._hprocess)
        except Exception:
            pass
        for fd_attr in ("_in_fd", "_out_fd"):
            fd = getattr(self, fd_attr)
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
                setattr(self, fd_attr, None)
        try:
            if self._hpcon is not None:
                k32.ClosePseudoConsole(self._hpcon)
        except Exception:
            pass
        self._hpcon = None


# ---------------------------------------------------------------- 兜底：纯管道
class PipeFallback(TerminalBase):
    mode = PIPE

    def start(self):
        self.proc = subprocess.Popen(
            self.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            env=self.env,
            cwd=self.cwd,
            creationflags=NO_WINDOW,
        )
        self._out_fd = self.proc.stdout.fileno()
        self._in_fd = self.proc.stdin.fileno()

    def read(self, n=65536):
        try:
            chunk = os.read(self._out_fd, n)
        except (OSError, ValueError):
            return b""
        if not chunk:
            return b""
        # 没有 TTY 时程序只输出 \n，xterm 需要 \r\n 才会回到行首
        return chunk.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")

    def write(self, data):
        if not data:
            return
        view = memoryview(data)
        while view:
            try:
                written = os.write(self._in_fd, view)
            except (OSError, ValueError):
                return
            if written <= 0:
                return
            view = view[written:]

    def resize(self, cols, rows):
        self.cols, self.rows = cols, rows

    def terminate(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        for fd_attr in ("_in_fd", "_out_fd"):
            fd = getattr(self, fd_attr, None)
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
                setattr(self, fd_attr, None)


# ---------------------------------------------------------------- 工厂
def build_argv(docker_bin, cid, workdir, cols, rows, mode):
    """按终端模式拼 docker exec 参数：只有真 TTY 模式才加 -t。"""
    argv = [docker_bin, "exec", "-i"]
    if mode in (PTY, CONPTY):
        argv.append("-t")
    argv += [
        "-w",
        workdir,
        "-e",
        "TERM=" + ("xterm-256color" if mode in (PTY, CONPTY) else "dumb"),
        "-e",
        f"COLUMNS={cols}",
        "-e",
        f"LINES={rows}",
        cid,
    ]
    if mode == PIPE:
        # 无 TTY 时 bash -i 会刷两行 job control 警告，这里直接吞掉
        argv += ["sh", "-c", "exec bash -i 2>/dev/null"]
    else:
        argv += ["bash", "-i"]
    return argv


def _preferred_order(want):
    if want == PTY:
        return [PosixPTY, PipeFallback]
    if want == CONPTY:
        return [WinConPTY, PipeFallback]
    if want == PIPE:
        return [PipeFallback]
    return [WinConPTY, PipeFallback] if IS_WIN else [PosixPTY, PipeFallback]


def create_terminal(docker_bin, cid, workdir, cols, rows, env=None, want=None):
    """返回已启动的终端；按优先级尝试，失败自动降级。

    环境变量 ENVTRAINER_TERM=pty|conpty|pipe 可强制指定模式（调试用）。
    """
    want = (want or os.environ.get("ENVTRAINER_TERM") or "").strip().lower() or None
    errors = []
    for cls in _preferred_order(want):
        argv = build_argv(docker_bin, cid, workdir, cols, rows, cls.mode)
        term = cls(argv, cols, rows, env=env)
        try:
            term.start()
            term.degrade_reason = None
            return term
        except Exception as e:  # noqa: BLE001
            errors.append(f"{cls.__name__}: {e}")
            try:
                term.terminate()
            except Exception:
                pass
    raise TerminalError("终端启动失败：\n  " + "\n  ".join(errors))


def mode_label(mode):
    return _MODE_LABEL.get(mode, mode)
