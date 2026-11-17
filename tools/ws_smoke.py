"""极简 WebSocket 客户端测试：连上 /ws/term，输入命令，打印输出。"""
import base64
import json
import os
import socket
import struct
import sys
import time

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8181"))
PATH = "/ws/term?cols=100&rows=30"


def main():
    s = socket.create_connection((HOST, PORT), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {PATH} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n"
        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode())
    resp = s.recv(4096)
    head = resp.split(b"\r\n\r\n")[0].decode(errors="replace")
    print("HANDSHAKE:", head.splitlines()[0])
    assert "101" in head, head

    def send(obj):
        data = json.dumps(obj).encode()
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            hdr = struct.pack("!BB", 0x81, 0x80 | n)
        else:
            hdr = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        s.sendall(hdr + mask + masked)

    def read_frame(timeout=6):
        s.settimeout(timeout)
        buf = b""

        def exact(n):
            nonlocal buf
            while len(buf) < n:
                chunk = s.recv(65536)
                if not chunk:
                    raise EOFError
                buf += chunk
            out, buf = buf[:n], buf[n:]
            return out

        b1, b2 = exact(2)
        ln = b2 & 0x7F
        if ln == 126:
            ln = struct.unpack("!H", exact(2))[0]
        elif ln == 127:
            ln = struct.unpack("!Q", exact(8))[0]
        op = b1 & 0x0F
        payload = exact(ln)
        return op, payload

    send({"t": "i", "d": "echo WS_OK_MARKER\r"})
    deadline = time.time() + 8
    collected = ""
    while time.time() < deadline:
        try:
            op, payload = read_frame(timeout=4)
        except (socket.timeout, EOFError):
            break
        if op == 0x1:
            msg = json.loads(payload)
            if msg.get("t") == "o":
                collected += msg["d"]
            elif msg.get("t") == "exit":
                collected += "\n<EXIT>"
                break
        if "WS_OK_MARKER" in collected.replace("echo WS_OK_MARKER", ""):
            break
    print("=== 终端输出 ===")
    print(collected.replace("\r\n", "\n")[-1200:])
    ok = "WS_OK_MARKER" in collected
    print("=== 结果:", "OK" if ok else "FAIL", "===")
    s.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
