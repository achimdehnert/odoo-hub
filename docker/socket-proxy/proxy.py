#!/usr/bin/env python3
"""
Docker Socket API Version Proxy
Rewrites /v1.{x}/ where x < 44 to /v1.44/ before forwarding to Docker socket.
Supports streaming (chunked transfer / longpoll) for /events endpoint.
"""
import re
import socket
import threading
import sys

LISTEN_PORT = 2375
DOCKER_SOCK = "/var/run/docker.sock"
MIN_VERSION = 44
TARGET_VERSION = "1.44"
VERSION_RE = re.compile(rb"^(GET|POST|DELETE|PUT|HEAD) /v1\.(\d+)(.*?) HTTP", re.MULTILINE)


def rewrite_request(data: bytes) -> bytes:
    def replace(m):
        method = m.group(1)
        minor = int(m.group(2))
        rest = m.group(3)
        ver = TARGET_VERSION.encode() if minor < MIN_VERSION else f"1.{minor}".encode()
        return method + b" /v" + ver + rest + b" HTTP"
    return VERSION_RE.sub(replace, data, count=1)


def forward(src, dst, transform=None):
    try:
        buf = b""
        while True:
            chunk = src.recv(65536)
            if not chunk:
                break
            if transform and not buf:
                buf = chunk
                # Accumulate until we have the full first line (request line)
                while b"\r\n" not in buf:
                    more = src.recv(65536)
                    if not more:
                        break
                    buf += more
                chunk = transform(buf)
                buf = b""
                transform = None  # only transform once
            dst.sendall(chunk)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def handle(client: socket.socket):
    upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        upstream.connect(DOCKER_SOCK)
        t1 = threading.Thread(target=forward, args=(client, upstream, rewrite_request), daemon=True)
        t2 = threading.Thread(target=forward, args=(upstream, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"[proxy] error: {e}", file=sys.stderr)
    finally:
        upstream.close()
        client.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", LISTEN_PORT))
    srv.listen(128)
    print(f"[proxy] listening on :{LISTEN_PORT} → {DOCKER_SOCK}", flush=True)
    while True:
        client, addr = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
