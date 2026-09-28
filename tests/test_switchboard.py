import collections
import threading
import time

import switchboard
from audiosocket import ConnectionClosed, TYPE_AUDIO, TYPE_DTMF

FRAME_SECONDS = switchboard.MS_PER_FRAME / 1000
LOUD_FRAME = b"\x10\x27" * (switchboard.BYTES_PER_FRAME // 2)
QUIET_FRAME = switchboard.SILENCE_FRAME
MAX_GAP_SECONDS = 0.06


class FakeLine:
    def __init__(self, incoming=(), paced=False):
        self.incoming = collections.deque(incoming)
        self.paced = paced
        self.sent = []
        self.sent_at = []
        self.call_id = "test-call"

    def read_frame(self):
        if self.paced:
            time.sleep(FRAME_SECONDS)
        if not self.incoming:
            raise ConnectionClosed("script finished")
        return self.incoming.popleft()

    def send_audio(self, frame):
        self.sent.append(frame)
        self.sent_at.append(time.monotonic())


def quiet(count):
    return [(TYPE_AUDIO, QUIET_FRAME)] * count


def keys(text):
    return [(TYPE_DTMF, key.encode()) for key in text]


def channel_for(incoming, paced=False):
    line = FakeLine(incoming, paced)
    return switchboard.VoiceChannel(line, "test"), line


def test_speaker_sends_a_frame_every_20_ms_across_speech_and_silence():
    line = FakeLine()
    speaker = switchboard.Speaker(line)
    speaker.queue(LOUD_FRAME * 25)
    time.sleep(0.8)
    speaker.queue(LOUD_FRAME * 25)
    time.sleep(1.0)
    speaker.stopped.set()
    time.sleep(0.05)

    gaps = [later - earlier for earlier, later in zip(line.sent_at, line.sent_at[1:])]
    elapsed = line.sent_at[-1] - line.sent_at[0]
    assert max(gaps) < MAX_GAP_SECONDS
    assert abs(elapsed / len(gaps) - FRAME_SECONDS) < 0.002
    assert line.sent.count(LOUD_FRAME) == 50


def test_speaker_never_sends_a_short_frame():
    line = FakeLine()
    speaker = switchboard.Speaker(line)
    speaker.queue(LOUD_FRAME[:100])
    time.sleep(0.1)
    speaker.stopped.set()
    assert all(len(frame) == switchboard.BYTES_PER_FRAME for frame in line.sent)


def test_single_key_becomes_a_menu_choice_after_a_pause():
    channel, _ = channel_for(keys("1") + quiet(switchboard.MENU_KEY_WAIT_FRAMES + 5))
    assert channel.listen_until_caller_stops() == b""
    assert channel.take_keys() == ("", "1")
    channel.hang_up()


def test_number_ends_with_hash():
    channel, _ = channel_for(keys("0901234567#") + quiet(5))
    assert channel.listen_until_caller_stops() == b""
    assert channel.take_keys() == ("0901234567", "")
    channel.hang_up()


def test_number_without_hash_ends_after_a_pause():
    channel, _ = channel_for(keys("0901234567") + quiet(switchboard.NUMBER_WAIT_FRAMES + 5))
    channel.listen_until_caller_stops()
    assert channel.take_keys() == ("0901234567", "")
    channel.hang_up()


def test_first_digit_of_a_number_is_not_a_menu_key_when_a_number_is_expected():
    channel, _ = channel_for(keys("0") + quiet(switchboard.MENU_KEY_WAIT_FRAMES + 5)
                             + keys("901234567#") + quiet(5))
    channel.expects_number = lambda: True
    channel.listen_until_caller_stops()
    assert channel.take_keys() == ("0901234567", "")
    channel.hang_up()


def test_hash_stops_the_reply(monkeypatch):
    long_reply = LOUD_FRAME * 250
    monkeypatch.setattr(switchboard, "speak", lambda sentence: (long_reply, False))
    channel, line = channel_for(quiet(10) + keys("#") + quiet(60), paced=True)
    played = channel.say("một câu rất dài")
    channel.hang_up()
    assert played["cut_short"]
    assert line.sent.count(LOUD_FRAME) < 60


def test_caller_waits_then_gives_up_when_every_line_is_busy(monkeypatch):
    spoken = []
    monkeypatch.setattr(switchboard, "speak", lambda sentence: (spoken.append(sentence) or QUIET_FRAME, False))
    monkeypatch.setattr(switchboard, "QUEUE_WAIT_FRAMES", 5)
    monkeypatch.setattr(switchboard, "call_slots", threading.BoundedSemaphore(1))
    switchboard.call_slots.acquire()
    channel, _ = channel_for(quiet(200), paced=True)
    log = type("Log", (), {"write": lambda self, *args, **fields: None})()
    assert not switchboard.wait_for_a_free_line(channel, log)
    channel.hang_up()
    assert spoken == [switchboard.PHRASES["hold_notice"], switchboard.PHRASES["busy_goodbye"]]


def test_caller_gets_the_line_as_soon_as_it_frees(monkeypatch):
    monkeypatch.setattr(switchboard, "speak", lambda sentence: (QUIET_FRAME, False))
    monkeypatch.setattr(switchboard, "call_slots", threading.BoundedSemaphore(1))
    switchboard.call_slots.acquire()
    threading.Timer(0.2, switchboard.call_slots.release).start()
    channel, _ = channel_for(quiet(3000), paced=True)
    log = type("Log", (), {"write": lambda self, *args, **fields: None})()
    assert switchboard.wait_for_a_free_line(channel, log)
    channel.hang_up()
