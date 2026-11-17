"""WebSocket 客户端（用于把浏览器连接代理到容器里的 code-server）。

和 ws.py 的区别：ws.py 是服务端（接受浏览器连接），这里是客户端（连上游服务），
所以发出的帧必须带 mask，收到的帧不带。
"""
from __future__ import annotations

import base64
import os
import socket
import struct
import threading

from ws import OP_BINARY, OP_CLOSE, OP_PING, OP_PONG, OP_TEXT, WSClosed


class WSClient:
    def __init__(self, host, port, path, origin=None, timeout=10):
        self.host = host
        self.port = port
        self.path = path
        self.origin = origin
        self._buf = b""
        self._lock = threading.Lock()
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(None)
        self._handshake()

    def _handshake(self):
        key = base64.b64encode(os.urandom(16)).decode()
        host_hdr = f"{self.host}:{self.port}"
        lines = [
            f"GET {self.path} HTTP/1.1",
            f"Host: {host_hdr}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
        ]
        if self.origin:
            lines.append(f"Origin: {self.origin}")
        req = "\r\n".join(lines) + "\r\n\r\n"
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WSClosed()
            buf += chunk
        head, buf = buf.split(b"\r\n\r\n", 1)
        self._buf = buf
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status and not status.endswith(b" 101"):
            raise WSClosed()

    # ---------- 发送（客户端必须 mask） ----------
    def _send_frame(self, opcode, payload=b""):
        mask = os.urandom(4)
        n = len(payload)
        head = struct.pack("!B", 0x80 | opcode)
        if n < 126:
            head += struct.pack("!B", 0x80 | n)
        elif n < 65536:
            head += struct.pack("!BH", 0x80 | 126, n)
        else:
            head += struct.pack("!BQ", 0x80 | 127, n)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        with self._lock:
            self.sock.sendall(head + mask + masked)

    def send_text(self, text):
        self._send_frame(OP_TEXT, text.encode("utf-8"))

    def send_binary(self, data):
        self._send_frame(OP_BINARY, data)

    def close(self, code=1000):
        try:
            self._send_frame(OP_CLOSE, struct.pack("!H", code))
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    # ---------- 接收 ----------
    def _read_exact(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise WSClosed()
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _read_frame(self):
        b1, b2 = self._read_exact(2)
        fin = bool(b1 & 0x80)
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if masked else None
        data = self._read_exact(length) if length else b""
        if mask:
            data = bytes(b ^ mask[i & 3] for i, b in enumerate(data))
        return fin, opcode, data

    def recv_message(self):
        """返回 (opcode, payload)，自动处理分片和 ping/pong。"""
        opcode = None
        data = b""
        while True:
            fin, op, payload = self._read_frame()
            if op == 0x0:  # continuation
                data += payload
            elif op in (OP_TEXT, OP_BINARY):
                opcode = op
                data = payload
            elif op == OP_CLOSE:
                raise WSClosed()
            elif op == OP_PING:
                self._send_frame(OP_PONG, payload)
                continue
            elif op == OP_PONG:
                continue
            else:
                continue
            if fin:
                return opcode, data
