import socketserver
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from audiosocket import AudioSocketConnection, ConnectionClosed, TYPE_AUDIO

HOST = "127.0.0.1"
PORT = 9092
SAMPLE_RATE = 8000
SECONDS_TO_ECHO = 5


class ConnectionHandler(socketserver.StreamRequestHandler):
    def handle(self):
        connection = AudioSocketConnection(self.rfile, self.wfile)
        print("\n=== ket noi moi ===")

        frame_count = 0
        total_bytes = 0
        frame_sizes = {}
        started = time.time()

        try:
            while time.time() - started < SECONDS_TO_ECHO:
                frame_type, payload = connection.read_frame()
                if connection.call_id and frame_count == 0:
                    print(f"  uuid: {connection.call_id}")
                if frame_type == TYPE_AUDIO:
                    frame_count += 1
                    total_bytes += len(payload)
                    frame_sizes[len(payload)] = frame_sizes.get(len(payload), 0) + 1
                    connection.send_audio(payload)
                else:
                    print(f"  khung la: loai 0x{frame_type:02x}, {len(payload)} byte")
        except ConnectionClosed as reason:
            print(f"  ket thuc: {reason}")

        elapsed = time.time() - started
        print(f"  nhan {frame_count} khung, {total_bytes} byte trong {elapsed:.1f}s")
        if frame_count:
            print(f"  co khung: {frame_sizes}")
            print(f"  nhip: {elapsed / frame_count * 1000:.1f} ms/khung")
            print(f"  tieng: {total_bytes / (SAMPLE_RATE * 2):.1f}s")
        print("=== het ===")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server((HOST, PORT), ConnectionHandler) as server:
        print(f"AudioSocket dang cho o {HOST}:{PORT}")
        print(f"Goi so 600, no se vong lai tieng cua ban trong {SECONDS_TO_ECHO}s")
        server.serve_forever()