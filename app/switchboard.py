import collections
import socketserver
import threading
import time

import webrtcvad

from audiosocket import (AudioSocketConnection, ConnectionClosed, TYPE_AUDIO,
                         TYPE_DTMF)
from conversation import Conversation, warm_up_llm
from models import SAMPLE_RATE, SpeechRecognizer, SpeechSynthesizer

HOST = "127.0.0.1"
PORT = 9092

MS_PER_FRAME = 20
BYTES_PER_FRAME = SAMPLE_RATE * 2 * MS_PER_FRAME // 1000
SILENCE_FRAME = bytes(BYTES_PER_FRAME)
MAX_CATCH_UP_SECONDS = 0.5
VAD_AGGRESSIVENESS = 3

SPEECH_FRAMES_TO_START = 10
SILENT_FRAMES_TO_STOP = 40
SILENT_FRAMES_BEFORE_GIVING_UP = 750
MAX_FRAMES_PER_TURN = 1500
DEAD_FRAMES_AFTER_PLAYBACK = 25

MAX_TURNS = 20
GREETING = "Dạ em xin nghe."
TRANSFER_NOTICE = "Dạ em chuyển anh chị cho nhân viên, anh chị giữ máy giúp em."

recognizer = None
synthesizer = None


class Speaker:
    def __init__(self, connection):
        self.connection = connection
        self.frames = collections.deque()
        self.stopped = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def queue(self, audio):
        for start in range(0, len(audio), BYTES_PER_FRAME):
            self.frames.append(audio[start:start + BYTES_PER_FRAME].ljust(BYTES_PER_FRAME, bytes(1)))

    def is_speaking(self):
        return bool(self.frames)

    def _run(self):
        deadline = time.monotonic()
        while not self.stopped.is_set():
            try:
                frame = self.frames.popleft()
            except IndexError:
                frame = SILENCE_FRAME
            try:
                self.connection.send_audio(frame)
            except OSError:
                return
            deadline += MS_PER_FRAME / 1000
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            elif remaining < -MAX_CATCH_UP_SECONDS:
                deadline = time.monotonic()


def load_models():
    global recognizer, synthesizer

    print("Dang tai gipformer ...")
    started = time.time()
    recognizer = SpeechRecognizer()
    print(f"  xong sau {time.time() - started:.0f}s")

    print("Dang tai giong Piper ...")
    started = time.time()
    synthesizer = SpeechSynthesizer()
    synthesizer.speak(GREETING)
    print(f"  xong sau {time.time() - started:.0f}s")


class VoiceChannel:
    def __init__(self, connection, call_id):
        self.connection = connection
        self.call_id = call_id
        self.speaker = Speaker(connection)
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.digits_so_far = ""
        self.dialed_number = ""

    def hang_up(self):
        self.speaker.stopped.set()

    def listen_until_caller_stops(self):
        frames = []
        speech_frames = 0
        silent_frames = 0
        speech_started = False

        for _ in range(MAX_FRAMES_PER_TURN):
            frame_type, payload = self.connection.read_frame()

            if frame_type == TYPE_DTMF:
                self._collect_digit(payload)
                if self.dialed_number:
                    return b""
                continue
            if frame_type != TYPE_AUDIO:
                continue

            if self._is_speech(payload):
                speech_frames += 1
                silent_frames = 0
                speech_started = speech_started or speech_frames >= SPEECH_FRAMES_TO_START
            else:
                speech_frames = 0
                silent_frames += 1

            frames.append(payload)

            if speech_started and silent_frames >= SILENT_FRAMES_TO_STOP:
                break
            if not speech_started and silent_frames >= SILENT_FRAMES_BEFORE_GIVING_UP:
                return None

        return b"".join(frames) if speech_started else None

    def say(self, sentence):
        started = time.monotonic()
        audio = synthesizer.speak(sentence)
        seconds = time.monotonic() - started
        self.speaker.queue(audio)
        while self.speaker.is_speaking():
            self.connection.read_frame()
        for _ in range(DEAD_FRAMES_AFTER_PLAYBACK):
            self.connection.read_frame()
        return f"piper {seconds:.1f}s"

    def _collect_digit(self, payload):
        char = payload.decode("ascii", "ignore")
        if char.isdigit():
            self.digits_so_far += char
        elif char in ("#", "*") and self.digits_so_far:
            self.dialed_number, self.digits_so_far = self.digits_so_far, ""
            print(f"[{self.call_id}] NGUOI GOI BAM: {self.dialed_number}")

    def _is_speech(self, frame):
        return (len(frame) == BYTES_PER_FRAME
                and self.vad.is_speech(frame, SAMPLE_RATE))


def serve_call(channel, conversation):
    for _ in range(MAX_TURNS):
        audio_bytes = channel.listen_until_caller_stops()
        if audio_bytes is None:
            return

        started = time.time()
        transcript = recognizer.transcribe(audio_bytes)
        audio_seconds = len(audio_bytes) / (SAMPLE_RATE * 2)
        print(f"[{channel.call_id}] NGHE {time.time() - started:.1f}s "
              f"({audio_seconds:.1f}s tieng): {transcript or '(khong ra chu)'}")

        result = conversation.respond(transcript, channel.dialed_number)
        channel.dialed_number = ""
        for line in result.log:
            print(f"    {line}")

        if result.transfer:
            print(f"[{channel.call_id}] CHUYEN MAY")
            channel.say(TRANSFER_NOTICE)
            return

        source = channel.say(result.reply)
        print(f"[{channel.call_id}] NOI ({source}): {result.reply}")


class ConnectionHandler(socketserver.StreamRequestHandler):
    def handle(self):
        connection = AudioSocketConnection(self.rfile, self.wfile)
        call_id = "?"
        try:
            connection.read_frame()
            call_id = (connection.call_id or "?")[:8]
            print(f"\n[{call_id}] === cuoc goi moi ===")

            channel = VoiceChannel(connection, call_id)
            try:
                channel.say(GREETING)
                serve_call(channel, Conversation())
            finally:
                channel.hang_up()
            connection.send_hangup()
        except ConnectionClosed as reason:
            print(f"[{call_id}] ket thuc: {reason}")
        except OSError as error:
            print(f"[{call_id}] mat ket noi: {error}")

        print(f"[{call_id}] === het ===")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    load_models()
    print(f"  (HIEU da nap san loi dan: {warm_up_llm()})")
    with Server((HOST, PORT), ConnectionHandler) as server:
        print(f"\nAudioSocket dang cho o {HOST}:{PORT} — goi so 600")
        server.serve_forever()
