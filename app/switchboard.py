import collections
import socketserver
import threading
import time

import webrtcvad

from audiosocket import (AudioSocketConnection, ConnectionClosed, TYPE_AUDIO,
                         TYPE_DTMF)
from call_log import CallLog
from conversation import (GOODBYE, GOODBYE_AFTER_SILENCE, STILL_THERE, Conversation,
                          warm_up_llm)
from models import SAMPLE_RATE, SpeechRecognizer, SpeechSynthesizer
from staff_transfer import TransferFailed, transfer_to_staff

HOST = "127.0.0.1"
PORT = 9092

MS_PER_FRAME = 20
BYTES_PER_FRAME = SAMPLE_RATE * 2 * MS_PER_FRAME // 1000
SILENCE_FRAME = bytes(BYTES_PER_FRAME)
MAX_CATCH_UP_SECONDS = 0.5
VAD_AGGRESSIVENESS = 3

SPEECH_FRAMES_TO_START = 10
SILENT_FRAMES_TO_STOP = 40
SILENT_FRAMES_BEFORE_NUDGE = 400
MAX_FRAMES_PER_TURN = 1500
DEAD_FRAMES_AFTER_PLAYBACK = 25
ENDPOINT_WAIT_SECONDS = SILENT_FRAMES_TO_STOP * MS_PER_FRAME / 1000

MENU_KEY_WAIT_FRAMES = 60
NUMBER_WAIT_FRAMES = 150
END_OF_NUMBER_KEYS = ("#", "*")
STOP_TALKING_KEY = "#"

MAX_ACTIVE_CALLS = 1
QUEUE_WAIT_FRAMES = 3000
FRAMES_TO_WAIT_FOR_TRANSFER = 250
SPOKEN_AUDIO_CACHE_SIZE = 300

MAX_TURNS = 40
GREETING = "Dạ em xin nghe. Anh chị cứ nói điều cần hỏi, hoặc bấm phím chín để nghe các phím ạ."
TRANSFER_NOTICE = "Dạ em chuyển anh chị cho nhân viên, anh chị giữ máy giúp em."
TRANSFER_FAILED = "Dạ hiện em chưa nối được nhân viên, anh chị gọi lại sau giúp em nhé. Em chào anh chị ạ."
HOLD_NOTICE = "Dạ tổng đài đang bận, anh chị vui lòng giữ máy trong giây lát ạ."
BUSY_GOODBYE = "Dạ tổng đài vẫn đang bận, anh chị vui lòng gọi lại sau ạ. Em cảm ơn anh chị."

recognizer = None
synthesizer = None
spoken_audio = collections.OrderedDict()
spoken_audio_lock = threading.Lock()
call_slots = threading.BoundedSemaphore(MAX_ACTIVE_CALLS)


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

    def stop_talking(self):
        self.frames.clear()

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
    speak(GREETING)
    print(f"  xong sau {time.time() - started:.0f}s")


def speak(sentence):
    with spoken_audio_lock:
        if sentence in spoken_audio:
            spoken_audio.move_to_end(sentence)
            return spoken_audio[sentence], True
    audio = synthesizer.speak(sentence)
    with spoken_audio_lock:
        spoken_audio[sentence] = audio
        while len(spoken_audio) > SPOKEN_AUDIO_CACHE_SIZE:
            spoken_audio.popitem(last=False)
    return audio, False


class VoiceChannel:
    def __init__(self, connection, call_id):
        self.connection = connection
        self.call_id = call_id
        self.speaker = Speaker(connection)
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.digits_so_far = ""
        self.frames_since_digit = 0
        self.dialed_number = ""
        self.menu_key = ""
        self.cut_short = False
        self.expects_number = lambda: False

    def hang_up(self):
        self.speaker.stopped.set()

    def has_keys(self):
        return bool(self.dialed_number or self.menu_key)

    def take_keys(self):
        keys = self.dialed_number, self.menu_key
        self.dialed_number = self.menu_key = ""
        return keys

    def read(self):
        frame_type, payload = self.connection.read_frame()
        if frame_type == TYPE_DTMF:
            self._collect_key(payload.decode("ascii", "ignore"))
        elif self.digits_so_far:
            self.frames_since_digit += 1
            self._finish_digits_after_a_pause()
        return frame_type, payload

    def listen_until_caller_stops(self):
        frames = []
        speech_frames = 0
        silent_frames = 0
        speech_started = False

        for _ in range(MAX_FRAMES_PER_TURN):
            if self.has_keys():
                return b""
            frame_type, payload = self.read()
            if frame_type != TYPE_AUDIO:
                continue
            if self.digits_so_far:
                silent_frames = 0
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
            if not speech_started and silent_frames >= SILENT_FRAMES_BEFORE_NUDGE:
                return None

        return b"".join(frames) if speech_started else None

    def say(self, sentence):
        started = time.monotonic()
        audio, remembered = speak(sentence)
        speak_seconds = time.monotonic() - started
        self.cut_short = False
        self.speaker.queue(audio)
        queued_at = time.monotonic()
        while self.speaker.is_speaking():
            self.read()
        for _ in range(DEAD_FRAMES_AFTER_PLAYBACK):
            self.read()
        return {"speak_s": round(speak_seconds, 2), "remembered": remembered,
                "cut_short": self.cut_short, "queued_at": queued_at}

    def _collect_key(self, key):
        self.frames_since_digit = 0
        if key.isdigit():
            self.digits_so_far += key
        elif key in END_OF_NUMBER_KEYS and self.digits_so_far:
            self._finish_digits()
        elif key == STOP_TALKING_KEY and self.speaker.is_speaking():
            self.cut_short = True
            self.speaker.stop_talking()
            print(f"[{self.call_id}] NGUOI GOI BAM # -> ngung doc")

    def _finish_digits_after_a_pause(self):
        single_key = len(self.digits_so_far) == 1 and not self.expects_number()
        if single_key and self.frames_since_digit >= MENU_KEY_WAIT_FRAMES:
            self._finish_digits()
        elif self.frames_since_digit >= NUMBER_WAIT_FRAMES:
            self._finish_digits()

    def _finish_digits(self):
        digits, self.digits_so_far = self.digits_so_far, ""
        if len(digits) == 1 and not self.expects_number():
            self.menu_key = digits
            print(f"[{self.call_id}] NGUOI GOI BAM PHIM: {digits}")
        else:
            self.dialed_number = digits
            print(f"[{self.call_id}] NGUOI GOI BAM SO: {digits}")
        if self.speaker.is_speaking():
            self.cut_short = True
            self.speaker.stop_talking()

    def _is_speech(self, frame):
        return (len(frame) == BYTES_PER_FRAME
                and self.vad.is_speech(frame, SAMPLE_RATE))


def serve_call(channel, conversation, log):
    channel.expects_number = conversation.expects_number
    nudged = False
    for _ in range(MAX_TURNS):
        audio_bytes = channel.listen_until_caller_stops()
        if audio_bytes is None:
            if nudged:
                print(f"[{channel.call_id}] IM LANG LAU -> chao roi cup")
                log.write("silence", action="goodbye")
                channel.say(GOODBYE_AFTER_SILENCE)
                return "silence"
            nudged = True
            print(f"[{channel.call_id}] IM LANG -> hoi con nghe khong")
            log.write("silence", action="nudge")
            channel.say(STILL_THERE)
            continue
        nudged = False
        caller_stopped = time.monotonic()

        transcript, asr_seconds = "", 0.0
        if audio_bytes:
            transcript = recognizer.transcribe(audio_bytes)
            asr_seconds = time.monotonic() - caller_stopped
            print(f"[{channel.call_id}] NGHE {asr_seconds:.1f}s "
                  f"({len(audio_bytes) / (SAMPLE_RATE * 2):.1f}s tieng): {transcript or '(khong ra chu)'}")
        dialed_number, menu_key = channel.take_keys()

        thinking_started = time.monotonic()
        result = conversation.respond(transcript, dialed_number, menu_key)
        think_seconds = time.monotonic() - thinking_started
        for line in result.log:
            print(f"    {line}")

        sentence = TRANSFER_NOTICE if result.transfer else result.reply
        played = channel.say(sentence)
        print(f"[{channel.call_id}] NOI (piper {played['speak_s']:.1f}s"
              f"{', co san' if played['remembered'] else ''}): {sentence}")
        log.write("turn", heard=transcript, dialed=dialed_number, key=menu_key,
                  audio_s=round(len(audio_bytes) / (SAMPLE_RATE * 2), 2),
                  endpoint_s=ENDPOINT_WAIT_SECONDS if audio_bytes else 0.0,
                  asr_s=round(asr_seconds, 2), think_s=round(think_seconds, 2),
                  speak_s=played["speak_s"], remembered=played["remembered"],
                  reply_after_s=round(played["queued_at"] - caller_stopped, 2),
                  reply=sentence, cut_short=played["cut_short"], notes=result.log,
                  transfer=result.transfer, hang_up=result.hang_up,
                  audio_file=log.save_audio(audio_bytes))

        if result.transfer:
            return hand_over_to_staff(channel, log)
        if result.hang_up:
            return "goodbye"

    channel.say(GOODBYE)
    return "too many turns"


def hand_over_to_staff(channel, log):
    try:
        target = transfer_to_staff(channel.connection.call_id)
    except TransferFailed as reason:
        print(f"[{channel.call_id}] CHUYEN MAY THAT BAI: {reason}")
        log.write("transfer", ok=False, reason=str(reason))
        channel.say(TRANSFER_FAILED)
        return "transfer failed"
    print(f"[{channel.call_id}] DA CHUYEN {target} -> may nhan vien")
    log.write("transfer", ok=True, channel=target)
    try:
        for _ in range(FRAMES_TO_WAIT_FOR_TRANSFER):
            channel.connection.read_frame()
    except ConnectionClosed:
        pass
    return "transferred"


def wait_for_a_free_line(channel, log):
    if call_slots.acquire(blocking=False):
        return True
    print(f"[{channel.call_id}] TONG DAI BAN -> cho")
    log.write("busy", action="hold")
    channel.say(HOLD_NOTICE)
    waited_from = time.monotonic()
    for _ in range(QUEUE_WAIT_FRAMES):
        channel.read()
        if call_slots.acquire(blocking=False):
            log.write("busy", action="line free", waited_s=round(time.monotonic() - waited_from, 1))
            return True
    log.write("busy", action="gave up")
    channel.say(BUSY_GOODBYE)
    return False


class ConnectionHandler(socketserver.StreamRequestHandler):
    def handle(self):
        connection = AudioSocketConnection(self.rfile, self.wfile)
        call_id = "?"
        log = None
        reason = "?"
        try:
            connection.read_frame()
            call_id = (connection.call_id or "?")[:8]
            log = CallLog(connection.call_id or "unknown")
            print(f"\n[{call_id}] === cuoc goi moi ===")

            channel = VoiceChannel(connection, call_id)
            got_a_line = False
            try:
                got_a_line = wait_for_a_free_line(channel, log)
                reason = "busy"
                if got_a_line:
                    channel.say(GREETING)
                    reason = serve_call(channel, Conversation(), log)
            finally:
                if got_a_line:
                    call_slots.release()
                channel.hang_up()
            if reason != "transferred":
                connection.send_hangup()
        except ConnectionClosed as closed:
            reason = str(closed)
            print(f"[{call_id}] ket thuc: {closed}")
        except OSError as error:
            reason = f"lost connection: {error}"
            print(f"[{call_id}] mat ket noi: {error}")

        if log:
            log.write("end", reason=reason)
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
