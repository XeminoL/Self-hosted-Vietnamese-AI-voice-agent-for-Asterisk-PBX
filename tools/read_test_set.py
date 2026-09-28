import argparse
import sys
import time
from pathlib import Path

import numpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from replay_calls import Call
from score_recordings import TEST_SET
from speech import SpeechSynthesizer

SKIP_GREETING_AFTER_SECONDS = 0.5
PAUSE_BEFORE_SPEAKING_SECONDS = 0.6
LINE_FREE_SECONDS = 2.0
REPLY_LIMIT_SECONDS = 30.0
LET_THE_TURN_FINISH_SECONDS = 1.0
FRAME_SECONDS = 0.02
MU = 255.0
FULL_SCALE = 32768.0


def through_phone_line(audio):
    samples = numpy.frombuffer(audio, dtype="<i2").astype(numpy.float64) / FULL_SCALE
    compressed = numpy.sign(samples) * numpy.log1p(MU * numpy.abs(samples)) / numpy.log1p(MU)
    quantized = numpy.round(compressed * 127.0) / 127.0
    restored = numpy.sign(quantized) * numpy.expm1(numpy.abs(quantized) * numpy.log1p(MU)) / MU
    return (numpy.clip(restored, -1.0, 1.0) * (FULL_SCALE - 1)).astype("<i2").tobytes()


def skip_the_greeting(call):
    started = time.monotonic()
    while not call.hung_up:
        call.tick()
        with call.lock:
            heard_something = any(loud for _, _, loud in call.received)
        if heard_something and time.monotonic() - started > SKIP_GREETING_AFTER_SECONDS:
            call.send_keys("#")
            break
    for _ in range(int(PAUSE_BEFORE_SPEAKING_SECONDS / FRAME_SECONDS)):
        call.tick()


def first_sound_of_the_reply(call, since):
    while time.monotonic() - since < REPLY_LIMIT_SECONDS and not call.hung_up:
        call.tick()
        with call.lock:
            loud = [moment for moment, _, is_loud in call.received if is_loud and moment > since]
        if loud:
            call.send_keys("#")
            for _ in range(int(LET_THE_TURN_FINISH_SECONDS / FRAME_SECONDS)):
                call.tick()
            return loud[0] - since
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", type=int, default=1, help="Piper Cake speaker; 0 is the switchboard's own voice")
    parser.add_argument("--first", type=int, default=1, help="start at this line of the test set")
    args = parser.parse_args()

    synthesizer = SpeechSynthesizer(speaker=args.voice)
    lines = [line.split("\t")[0] for line in TEST_SET.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"reading {len(lines) - args.first + 1} sentences with voice {args.voice}, started "
          f"{time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    for number, sentence in enumerate(lines, start=1):
        if number < args.first:
            continue
        call = Call()
        skip_the_greeting(call)
        call.send_audio(through_phone_line(synthesizer.speak(sentence)))
        waited = first_sound_of_the_reply(call, time.monotonic())
        call.close()
        time.sleep(LINE_FREE_SECONDS)
        timing = f"{waited:.2f}s" if waited is not None else "no reply"
        print(f"{number:3d} {timing:>8s}  {sentence}", flush=True)
    print(f"finished {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
