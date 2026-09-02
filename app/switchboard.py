import os
import socketserver
import time

import webrtcvad

from audiosocket import (AudioSocketConnection, ConnectionClosed, TYPE_AUDIO,
                         TYPE_DTMF)
from conversation import Conversation
from models import APP_DIR, SAMPLE_RATE, SpeechRecognizer, SpeechSynthesizer
from voice_library import VoiceLibrary

HOST = "127.0.0.1"
PORT = 9092

MS_PER_FRAME = 20
BYTES_PER_FRAME = SAMPLE_RATE * 2 * MS_PER_FRAME // 1000
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
library = None


def load_models():
    global recognizer, synthesizer, library

    print("Dang tai gipformer ...")
    started = time.time()
    recognizer = SpeechRecognizer()
    print(f"  xong sau {time.time() - started:.0f}s")

    print("Dang tai VieNeu ...")
    started = time.time()
    synthesizer = SpeechSynthesizer()
    print(f"  xong sau {time.time() - started:.0f}s")

    library = VoiceLibrary(os.path.join(APP_DIR, "voice-library"), synthesizer.polished)
    print(f"Thu vien giong: {library.size()} cau san")


def audio_for(sentence):
    path = library.lookup(sentence)
    if path:
        with open(path, "rb") as f:
            return f.read(), True
    library.queue_for_later(sentence)
    return synthesizer.fast(sentence), False


class VoiceChannel:
    def __init__(self, connection, call_id):
        self.connection = connection
        self.call_id = call_id
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.digits_so_far = ""
        self.dialed_number = ""

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

    def play(self, audio_bytes):
        deadline = time.monotonic()
        for start in range(0, len(audio_bytes), BYTES_PER_FRAME):
            frame = audio_bytes[start:start + BYTES_PER_FRAME]
            self.connection.send_audio(frame.ljust(BYTES_PER_FRAME, bytes(1)))
            deadline += MS_PER_FRAME / 1000
            self._sleep_until(deadline)
            self.connection.read_frame()

        for _ in range(DEAD_FRAMES_AFTER_PLAYBACK):
            self.connection.read_frame()

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

    @staticmethod
    def _sleep_until(deadline):
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)


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
            channel.play(audio_for(TRANSFER_NOTICE)[0])
            return

        started = time.time()
        audio_bytes, from_library = audio_for(result.reply)
        source = "thu vien" if from_library else f"piper {time.time() - started:.1f}s"
        print(f"[{channel.call_id}] NOI ({source}): {result.reply}")
        channel.play(audio_bytes)


class ConnectionHandler(socketserver.StreamRequestHandler):
    def handle(self):
        connection = AudioSocketConnection(self.rfile, self.wfile)
        call_id = "?"
        try:
            connection.read_frame()
            call_id = (connection.call_id or "?")[:8]
            print(f"\n[{call_id}] === cuoc goi moi ===")

            channel = VoiceChannel(connection, call_id)
            channel.play(audio_for(GREETING)[0])
            serve_call(channel, Conversation())
            connection.send_hangup()
        except ConnectionClosed as reason:
            print(f"[{call_id}] ket thuc: {reason}")
        except OSError as error:
            print(f"[{call_id}] mat ket noi: {error}")

        print(f"[{call_id}] === het ===")
        library.synthesize_pending()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    load_models()
    with Server((HOST, PORT), ConnectionHandler) as server:
        print(f"\nAudioSocket dang cho o {HOST}:{PORT} — goi so 600")
        server.serve_forever()
