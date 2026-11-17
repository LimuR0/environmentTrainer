"""极简 WebSocket (RFC6455) 服务端实现，只依赖标准库。

只处理浏览器终端场景需要的：文本/二进制帧、ping/pong、close。
不支持分片（continuation），浏览器对小消息不会分片，教学场景足够。
"""

import base64
import hashlib
import struct
import threading

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA


class WSClosed(Exception):
    pass


def accept_key(client_key: str) -> str:
    return base64.b64encode(hashlib.sha1(client_key.encode() + GUID).digest()).decode()


class WSConn:
    def __init__(self, rfile, wfile):
        self.rfile = rfile
        self.wfile = wfile
        self._lock = threading.Lock()
        self.closed = False

    # ---------- 发送 ----------
    def _frame(self, opcode: int, payload: bytes = b"") -> bytes:
        n = len(payload)
        head = struct.pack("!B", 0x80 | opcode)
        if n < 126:
            head += struct.pack("!B", n)
        elif n < 65536:
            head += struct.pack("!BH", 126, n)
        else:
            head += struct.pack("!BQ", 127, n)
        return head + payload

    def _send(self, opcode: int, payload: bytes) -> None:
        if self.closed:
            raise WSClosed()
        data = self._frame(opcode, payload)
        with self._lock:
            try:
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                self.closed = True
                raise WSClosed() from e

    def send_text(self, text: str) -> None:
        self._send(OP_TEXT, text.encode("utf-8"))

    def send_binary(self, data: bytes) -> None:
        self._send(OP_BINARY, data)

    def ping(self) -> None:
        self._send(OP_PING, b"")

    def close(self, code: int = 1000) -> None:
        try:
            self._send(OP_CLOSE, struct.pack("!H", code))
        except WSClosed:
            pass
        self.closed = True

    # ---------- 接收 ----------
    def _read_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            try:
                chunk = self.rfile.read(n - len(buf))
            except (ConnectionResetError, OSError) as e:
                raise WSClosed() from e
            if not chunk:
                raise WSClosed()
            buf += chunk
        return buf

    def recv(self):
        """返回 (opcode, payload)；控制帧在内部处理掉。"""
        while True:
            b1, b2 = self._read_exact(2)
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            if length > 16 * 1024 * 1024:
                raise WSClosed()
            mask = self._read_exact(4) if masked else None
            data = self._read_exact(length) if length else b""
            if mask:
                data = bytes(b ^ mask[i & 3] for i, b in enumerate(data))

            if opcode == OP_CLOSE:
                raise WSClosed()
            if opcode == OP_PING:
                self._send(OP_PONG, data)
                continue
            if opcode == OP_PONG:
                continue
            return opcode, data
