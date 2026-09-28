import queue
import select
import socket
import sys
import threading
import time

LOOPBACK = "127.0.0.1"
CLIENT_PORT = 8080
TUNNEL_PORT = 8081
LLM_PORT = 8085
IDLE_TUNNELS = 4
TUNNEL_WAIT_SECONDS = 30
RETRY_SECONDS = 1
CHUNK_BYTES = 65536


def _copy(source, target):
    try:
        while True:
            data = source.recv(CHUNK_BYTES)
            if not data:
                break
            target.sendall(data)
    except OSError:
        pass
    finally:
        try:
            target.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _pipe(first, second, first_bytes=b""):
    if first_bytes:
        second.sendall(first_bytes)
    backward = threading.Thread(target=_copy, args=(second, first), daemon=True)
    backward.start()
    _copy(first, second)
    backward.join()
    first.close()
    second.close()


def _listening_socket(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOOPBACK, port))
    server.listen()
    return server


def _still_open(tunnel):
    readable, _, _ = select.select([tunnel], [], [], 0)
    return not readable


def _collect_tunnels(idle):
    server = _listening_socket(TUNNEL_PORT)
    while True:
        tunnel, _ = server.accept()
        idle.put(tunnel)


def _next_open_tunnel(idle):
    deadline = time.monotonic() + TUNNEL_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            tunnel = idle.get(timeout=max(0.0, deadline - time.monotonic()))
        except queue.Empty:
            return None
        if _still_open(tunnel):
            return tunnel
        tunnel.close()
    return None


def _serve_client(client, idle):
    tunnel = _next_open_tunnel(idle)
    if tunnel is None:
        client.close()
        return
    _pipe(client, tunnel)


def run_wsl_side():
    idle = queue.Queue()
    threading.Thread(target=_collect_tunnels, args=(idle,), daemon=True).start()
    server = _listening_socket(CLIENT_PORT)
    print(f"bridge: callers on {LOOPBACK}:{CLIENT_PORT}, windows dials in on {LOOPBACK}:{TUNNEL_PORT}",
          flush=True)
    while True:
        client, _ = server.accept()
        threading.Thread(target=_serve_client, args=(client, idle), daemon=True).start()


def _keep_one_tunnel():
    while True:
        try:
            tunnel = socket.create_connection((LOOPBACK, TUNNEL_PORT))
        except OSError:
            time.sleep(RETRY_SECONDS)
            continue
        try:
            first_bytes = tunnel.recv(CHUNK_BYTES)
        except OSError:
            first_bytes = b""
        if not first_bytes:
            tunnel.close()
            time.sleep(RETRY_SECONDS)
            continue
        try:
            model = socket.create_connection((LOOPBACK, LLM_PORT))
        except OSError:
            tunnel.close()
            continue
        _pipe(tunnel, model, first_bytes)


def run_windows_side():
    print(f"bridge: dialing into WSL {LOOPBACK}:{TUNNEL_PORT}, forwarding to {LOOPBACK}:{LLM_PORT}",
          flush=True)
    workers = [threading.Thread(target=_keep_one_tunnel, daemon=True) for _ in range(IDLE_TUNNELS)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    sides = {"wsl": run_wsl_side, "windows": run_windows_side}
    if len(sys.argv) != 2 or sys.argv[1] not in sides:
        sys.exit("usage: python llm_bridge.py wsl|windows")
    sides[sys.argv[1]]()
