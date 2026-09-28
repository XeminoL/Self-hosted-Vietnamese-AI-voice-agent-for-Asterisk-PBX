import argparse
import json
import socket
import struct
import sys
import threading
import time
import unicodedata
import uuid
from pathlib import Path

import numpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from models import SpeechRecognizer, SpeechSynthesizer

HOST = "127.0.0.1"
PORT = 9092
CALLER_VOICE = 1
FRAME_BYTES = 320
FRAME_SECONDS = 0.02
LOUD = 500
QUIET_AFTER_REPLY = 1.2
REPLY_LIMIT_SECONDS = 40.0
QUEUE_LIMIT_SECONDS = 120.0
START_GAP_SECONDS = 1.0
LINE_FREE_SECONDS = 3.0
KEY_GAP_FRAMES = 5
RESULTS_FILE = Path(__file__).resolve().parent / "ket-qua-replay.json"

SCENARIOS = {
    "khoa_the_dong_y": [
        ("say", "tôi muốn khoá thẻ của tôi", ["bấm"]),
        ("keys", "0987654321#", ["xác nhận"]),
        ("say", "đúng rồi", ["thành công|từ trước"]),
        ("say", "cảm ơn em", ["thêm"]),
        ("say", "dạ không ạ", ["cảm ơn", "HANGUP"]),
    ],
    "khoa_the_tu_choi": [
        ("keys", "4", ["bấm"]),
        ("keys", "0901234567#", ["xác nhận"]),
        ("say", "thôi không khoá nữa", ["không làm nữa"]),
        ("say", "vậy thôi tạm biệt em", ["cảm ơn", "HANGUP"]),
    ],
    "menu_phim": [
        ("keys", "9", ["bấm một", "số dư"]),
        ("keys", "1", ["bấm"]),
        ("keys", "0912345678#", ["bốn mươi bảy triệu"]),
    ],
    "hoi_tai_lieu": [
        ("say", "lãi suất tiết kiệm bao nhiêu", ["phần trăm"]),
        ("say", "lãi suất tiết kiệm bao nhiêu", ["phần trăm", "DIFFERENT"]),
        ("say", "không phải, tôi hỏi giá vàng", ["xin lỗi", "vàng"]),
        ("say", "chuyển tiền mất phí không", ["bảy nghìn"]),
    ],
    "ngai_bam_so": [
        ("say", "số dư tài khoản của tôi bao nhiêu", ["bấm"]),
        ("say", "tôi không có điện thoại ở đây", ["nhân viên"]),
        ("say", "ừ chuyển đi", ["nhân viên"]),
    ],
    "im_lang": [
        ("silence", 9.5, ["còn nghe máy"]),
        ("silence", 9.5, ["cúp máy", "HANGUP"]),
    ],
    "bam_thang_ngung_doc": [
        ("say", "chi nhánh mở cửa mấy giờ", ["SHORT"]),
    ],
    "xep_hang": [
        ("wait", QUEUE_LIMIT_SECONDS, ["xin nghe"]),
        ("say", "giá vàng hôm nay", ["vàng"]),
    ],
}
GREETING_EXPECTED = {"xep_hang": ["đang bận"]}
BUSY_LINE_MAKER = {"xep_hang": "hoi_tai_lieu"}
SHORTER_THAN_SECONDS = 3.0
PRESS_HASH_AFTER_SECONDS = 1.0


def plain(text):
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


class Call:
    def __init__(self):
        self.sock = socket.create_connection((HOST, PORT))
        self.sock.sendall(struct.pack(">BH", 0x01, 16) + uuid.uuid4().bytes)
        self.received = []
        self.lock = threading.Lock()
        self.hung_up = False
        self.clock = time.monotonic()
        threading.Thread(target=self._receive, daemon=True).start()

    def _receive(self):
        buffer = b""
        while True:
            try:
                data = self.sock.recv(65536)
            except OSError:
                break
            if not data:
                break
            buffer += data
            while len(buffer) >= 3:
                kind, length = struct.unpack(">BH", buffer[:3])
                if len(buffer) < 3 + length:
                    break
                payload, buffer = buffer[3:3 + length], buffer[3 + length:]
                if kind == 0x10 and payload:
                    loud = numpy.abs(numpy.frombuffer(payload, dtype="<i2")).max() > LOUD
                    with self.lock:
                        self.received.append((time.monotonic(), payload, loud))
                elif kind == 0x00:
                    self.hung_up = True
        self.hung_up = True

    def tick(self, frame=None):
        frame = frame if frame is not None else bytes(FRAME_BYTES)
        try:
            self.sock.sendall(struct.pack(">BH", 0x10, len(frame)) + frame)
        except OSError:
            self.hung_up = True
        self.clock += FRAME_SECONDS
        remaining = self.clock - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

    def send_audio(self, audio):
        for start in range(0, len(audio), FRAME_BYTES):
            self.tick(audio[start:start + FRAME_BYTES].ljust(FRAME_BYTES, b"\0"))

    def send_keys(self, keys):
        for key in keys:
            self.sock.sendall(struct.pack(">BH", 0x03, 1) + key.encode())
            for _ in range(KEY_GAP_FRAMES):
                self.tick()

    def wait_for_reply(self, since, press_hash_after=None, limit=REPLY_LIMIT_SECONDS):
        pressed = False
        while time.monotonic() - since < limit and not self.hung_up:
            self.tick()
            with self.lock:
                loud = [t for t, _, is_loud in self.received if is_loud and t > since]
            if loud and press_hash_after and not pressed and time.monotonic() - loud[0] > press_hash_after:
                self.send_keys("#")
                pressed = True
            if loud and time.monotonic() - loud[-1] > QUIET_AFTER_REPLY:
                break
        with self.lock:
            frames = [(t, payload) for t, payload, _ in self.received if t > since]
            loud = [t for t, _, is_loud in self.received if is_loud and t > since]
        if not loud:
            return None
        audio = b"".join(payload for t, payload in frames if loud[0] - 0.1 <= t <= loud[-1] + 0.1)
        return {"first_sound_s": loud[0] - since, "length_s": loud[-1] - loud[0], "audio": audio}

    def close(self):
        self.sock.close()


def run_scenario(name, caller_voice, recognizer, recognizer_lock):
    call = Call()
    greeting = call.wait_for_reply(time.monotonic())
    with recognizer_lock:
        greeting_heard = recognizer.transcribe(greeting["audio"]) if greeting else ""
    expected_greeting = GREETING_EXPECTED.get(name, ["xin nghe"])
    turns = [{"step": "greeting", "first_sound_s": greeting and round(greeting["first_sound_s"], 2),
              "heard": greeting_heard,
              "ok": all(plain(word) in plain(greeting_heard) for word in expected_greeting)}]
    previous_heard = None
    for kind, content, expected in SCENARIOS[name]:
        if kind == "say":
            call.send_audio(caller_voice(content))
        elif kind == "keys":
            call.send_keys(content)
        elif kind == "silence":
            for _ in range(int(content / FRAME_SECONDS)):
                if call.hung_up:
                    break
                call.tick()
        caller_stopped = time.monotonic()
        press_after = PRESS_HASH_AFTER_SECONDS if "SHORT" in expected else None
        if kind == "wait":
            reply = call.wait_for_reply(caller_stopped, limit=content)
        else:
            reply = call.wait_for_reply(caller_stopped if kind != "silence" else caller_stopped - content,
                                        press_after)
        if reply is None:
            turns.append({"step": f"{kind} {content}", "ok": False, "heard": "(no reply)"})
            break
        with recognizer_lock:
            heard = recognizer.transcribe(reply["audio"])
        checks = []
        for word in expected:
            if word == "HANGUP":
                deadline = time.monotonic() + 3
                while not call.hung_up and time.monotonic() < deadline:
                    call.tick()
                checks.append(call.hung_up)
            elif word == "DIFFERENT":
                checks.append(plain(heard) != plain(previous_heard or ""))
            elif word == "SHORT":
                checks.append(reply["length_s"] < SHORTER_THAN_SECONDS)
            else:
                checks.append(any(plain(choice) in plain(heard) for choice in word.split("|")))
        turns.append({"step": f"{kind} {content}", "ok": all(checks), "heard": heard,
                      "first_sound_s": round(reply["first_sound_s"], 2),
                      "length_s": round(reply["length_s"], 2), "expected": expected,
                      "timed": kind not in ("silence", "wait")})
        previous_heard = heard
    call.close()
    return {"scenario": name, "ok": all(t.get("ok", True) for t in turns) and len(turns) > 1,
            "turns": turns}


def print_result(result):
    print(f"\n=== {result['scenario']}: {'PASS' if result['ok'] else 'FAIL'}")
    for turn in result["turns"]:
        mark = {True: " ok ", False: "FAIL", None: "    "}[turn.get("ok")]
        timing = f"{turn['first_sound_s']:5.2f}s" if turn.get("first_sound_s") is not None else "   -  "
        print(f"  {mark} {timing}  {turn['step']:30s} -> {turn.get('heard', '')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenarios", nargs="*", default=list(SCENARIOS))
    parser.add_argument("--together", action="store_true",
                        help="start every scenario at once, one second apart, instead of one after another")
    args = parser.parse_args()

    synthesizer = SpeechSynthesizer(speaker=CALLER_VOICE)
    recognizer = SpeechRecognizer()
    recognizer_lock = threading.Lock()
    voice_lock = threading.Lock()
    spoken = {}

    def caller_voice(sentence):
        with voice_lock:
            if sentence not in spoken:
                spoken[sentence] = synthesizer.speak(sentence)
            return spoken[sentence]

    for scenario in set(args.scenarios) | {BUSY_LINE_MAKER.get(s, s) for s in args.scenarios}:
        for kind, content, _ in SCENARIOS[scenario]:
            if kind == "say":
                caller_voice(content)

    groups = [args.scenarios] if args.together else [
        [BUSY_LINE_MAKER[scenario], scenario] if scenario in BUSY_LINE_MAKER else [scenario]
        for scenario in args.scenarios]
    results = []
    for group in groups:
        time.sleep(LINE_FREE_SECONDS)
        batch = [None] * len(group)

        def run(slot, group=group, batch=batch):
            batch[slot] = run_scenario(group[slot], caller_voice, recognizer, recognizer_lock)

        threads = [threading.Thread(target=run, args=(slot,)) for slot in range(len(group))]
        for thread in threads:
            thread.start()
            time.sleep(START_GAP_SECONDS)
        for thread in threads:
            thread.join()
        for result in batch:
            print_result(result)
            results.append(result)

    timed = sorted(t["first_sound_s"] for r in results for t in r["turns"][1:]
                   if t.get("timed") and t.get("first_sound_s") is not None)
    passed = sum(r["ok"] for r in results)
    print(f"\n{passed}/{len(results)} scenarios passed")
    if timed:
        print(f"reply starts after caller stops: p50 {numpy.percentile(timed, 50):.2f}s, "
              f"p95 {numpy.percentile(timed, 95):.2f}s, max {timed[-1]:.2f}s over {len(timed)} turns")
    RESULTS_FILE.write_text(json.dumps({"together": args.together, "results": results},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
