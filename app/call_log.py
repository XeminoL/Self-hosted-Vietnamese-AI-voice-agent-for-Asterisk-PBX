import json
import os
import threading
import time
import wave

CALLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calls")
SHORT_ID_LENGTH = 8
RECORD_SWITCH = "RECORD_CALLS"
AUDIO_RATE = 8000

_write_lock = threading.Lock()


class CallLog:
    def __init__(self, call_id, folder=None):
        folder = folder or CALLS_DIR
        os.makedirs(folder, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(folder, f"{stamp}-{call_id[:SHORT_ID_LENGTH]}.jsonl")
        self.audio_dir = self.path[:-len(".jsonl")]
        self.records_audio = os.environ.get(RECORD_SWITCH) == "1"
        self.saved_turns = 0
        self.started = time.monotonic()
        self.write("start", call_id=call_id, clock=time.strftime("%Y-%m-%d %H:%M:%S"),
                   records_audio=self.records_audio)

    def save_audio(self, audio):
        if not self.records_audio or not audio:
            return None
        os.makedirs(self.audio_dir, exist_ok=True)
        self.saved_turns += 1
        path = os.path.join(self.audio_dir, f"turn-{self.saved_turns:02d}.wav")
        with wave.open(path, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(AUDIO_RATE)
            handle.writeframes(audio)
        return os.path.relpath(path, os.path.dirname(self.path))

    def write(self, event, **fields):
        record = {"t": round(time.monotonic() - self.started, 2), "event": event, **fields}
        line = json.dumps(record, ensure_ascii=False)
        with _write_lock, open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def read_calls(folder=None):
    folder = folder or CALLS_DIR
    if not os.path.isdir(folder):
        return []
    calls = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".jsonl"):
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                calls.append([json.loads(line) for line in handle if line.strip()])
    return calls
