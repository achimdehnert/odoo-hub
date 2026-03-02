#!/usr/bin/env python3
"""
Docker Socket API Version Proxy
Rewrites /v1.{x}/ where x < 44 to /v1.44/ on EVERY request line in a
persistent HTTP/1.1 keep-alive connection.
Supports streaming (chunked / longpoll) via threads.
"""
import re
import socket
import threading
import sys

LISTEN_PORT = 2375
DOCKER_SOCK  = "/var/run/docker.sock"
# Matches the request line: METHOD /v1.NN/... HTTP/1.x
REQ_LINE_RE  = re.compile(rb"^([A-Z]+) /v1\.(\d+)(/[^\r\n]*) HTTP/")


def rewrite_line(line: bytes) -> bytes:
    m = REQ_LINE_RE.match(line)
    if m:
        minor = int(m.group(2))
        if minor < 44:
            rest  = m.group(3)
            suffix = line[m.end():]          # " HTTP/1.x\r\n"
            line = m.group(1) + b" /v1.44" + rest + b" HTTP/" + suffix
    return line


def client_to_upstream(client: socket.socket, upstream: socket.socket):
    """Forward client→upstream, rewriting every HTTP request line."""
    buf = b""
    try:
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            buf += chunk
            # Flush complete lines; rewrite request lines
            while b"\r\n" in buf:
                line, buf = buf.split(b"\r\n", 1)
                line = rewrite_line(line)
                upstream.sendall(line + b"\r\n")
        # Flush remainder
        if buf:
            upstream.sendall(rewrite_line(buf))
    except Exception:
        pass
    finally:
        try:
            upstream.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def upstream_to_client(upstream: socket.socket, client: socket.socket):
    """Forward upstream→client verbatim (no rewrite needed)."""
    try:
        while True:
            chunk = upstream.recv(65536)
            if not chunk:
                break
            client.sendall(chunk)
    except Exception:
        pass
    finally:
        try:
            client.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def handle(client: socket.socket):
    upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        upstream.connect(DOCKER_SOCK)
        t1 = threading.Thread(target=client_to_upstream,  args=(client, upstream), daemon=True)
        t2 = threading.Thread(target=upstream_to_client,  args=(upstream, client), daemon=True)
        t1.start(); t2.start()
        t1.join();  t2.join()
    except Exception as e:
        print(f"[proxy] error: {e}", file=sys.stderr)
    finally:
        upstream.close()
        client.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", LISTEN_PORT))
    srv.listen(256)
    print(f"[proxy] listening :{LISTEN_PORT} → {DOCKER_SOCK}", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
