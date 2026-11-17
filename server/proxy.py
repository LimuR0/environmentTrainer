"""把 HTTP / WebSocket 请求代理到容器里跑的服务（code-server）。

容器端口只绑定在宿主机 127.0.0.1 的随机端口上，外面统一走本服务的 /vscode/<sid>/ 前缀，
这样只需要暴露一个端口，远程访问也能用。
"""
from __future__ import annotations

import http.client
import threading

from ws import WSClosed
from wsclient import WSClient

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def proxy_http(handler, port, method, path, headers, body):
    """同步转发一次 HTTP 请求；响应流式写回浏览器。"""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
    try:
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for k, v in headers.items():
            lk = k.lower()
            if lk in HOP_BY_HOP or lk in ("host", "content-length", "accept-encoding"):
                continue
            conn.putheader(k, v)
        conn.putheader("Host", f"127.0.0.1:{port}")
        if headers.get("Accept-Encoding"):
            conn.putheader("Accept-Encoding", headers["Accept-Encoding"])
        if body:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body if body else None)

        resp = conn.getresponse()
        handler.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() in HOP_BY_HOP:
                continue
            handler.send_header(k, v)
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.close_connection = True

        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            handler.wfile.write(chunk)
            handler.wfile.flush()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def proxy_ws(ws_conn, port, path):
    """把浏览器的 WebSocket 连接桥接到上游 code-server。"""
    try:
        upstream = WSClient("127.0.0.1", port, path, origin=f"http://127.0.0.1:{port}")
    except Exception:
        try:
            ws_conn.close(1011)
        except Exception:
            pass
        return

    stop = threading.Event()

    def upstream_to_browser():
        try:
            while not stop.is_set():
                opcode, data = upstream.recv_message()
                if opcode == 0x1:
                    ws_conn.send_text(data.decode("utf-8", "replace"))
                elif opcode == 0x2:
                    ws_conn.send_binary(data)
        except Exception:
            pass
        stop.set()
        try:
            ws_conn.close()
        except Exception:
            pass

    th = threading.Thread(target=upstream_to_browser, daemon=True)
    th.start()

    try:
        while not stop.is_set():
            opcode, data = ws_conn.recv()
            if opcode == 0x1:
                upstream.send_text(data.decode("utf-8", "replace"))
            elif opcode == 0x2:
                upstream.send_binary(data)
    except WSClosed:
        pass
    except Exception:
        pass
    finally:
        stop.set()
        try:
            upstream.close()
        except Exception:
            pass
