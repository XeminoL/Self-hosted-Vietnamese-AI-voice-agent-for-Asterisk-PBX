import argparse
import json
import sys
import time
import wave
from pathlib import Path

import numpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from call_log import read_calls
from domain import PHRASES
from read_test_set import through_phone_line
from replay_calls import CALLER_VOICE, FRAME_SECONDS, Call
from speech import SAMPLE_RATE, SpeechSynthesizer

STEPS = [
    ("say", "lãi suất tiết kiệm bao nhiêu"),
    ("say", "không phải, tôi hỏi giá vàng"),
    ("say", "tôi muốn khoá thẻ của tôi"),
    ("keys", "0987654321#"),
    ("say", "đúng rồi"),
    ("say", "cảm ơn em"),
    ("say", "dạ không ạ"),
]
PAUSE_BETWEEN_TURNS_SECONDS = 0.8
TAIL_SECONDS = 1.0
LOG_SETTLE_SECONDS = 1.0


def mix(pieces):
    placed = [(max(0, int(moment * SAMPLE_RATE)), numpy.frombuffer(audio, dtype="<i2").astype(numpy.int32))
              for moment, audio in pieces]
    track = numpy.zeros(max(start + len(samples) for start, samples in placed), dtype=numpy.int32)
    for start, samples in placed:
        track[start:start + len(samples)] += samples
    return numpy.clip(track, -32768, 32767).astype("<i2")


def pause(call, seconds):
    for _ in range(int(seconds / FRAME_SECONDS)):
        call.tick()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="folder for demo-call.wav and demo-call.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    synthesizer = SpeechSynthesizer(speaker=CALLER_VOICE)
    voices = {text: through_phone_line(synthesizer.speak(text)) for kind, text in STEPS if kind == "say"}

    call = Call()
    started = time.monotonic()
    caller_lines = []
    call.wait_for_reply(time.monotonic())
    for kind, content in STEPS:
        pause(call, PAUSE_BETWEEN_TURNS_SECONDS)
        begin = time.monotonic() - started
        if kind == "say":
            call.send_audio(voices[content])
        else:
            call.send_keys(content)
        caller_lines.append({"who": "caller" if kind == "say" else "keys", "text": content,
                             "start": begin, "end": time.monotonic() - started})
        call.wait_for_reply(time.monotonic())
    pause(call, TAIL_SECONDS)
    call.wait_for_hang_up()
    with call.lock:
        received = list(call.received)
    call.close()
    time.sleep(LOG_SETTLE_SECONDS)

    pieces = [(moment - started - FRAME_SECONDS, payload) for moment, payload, _ in received]
    pieces += [(line["start"], voices[line["text"]]) for line in caller_lines if line["who"] == "caller"]
    track = mix(pieces)

    switchboard_lines = []
    loud = [moment - started for moment, _, is_loud in received if is_loud]
    demo_events = read_calls()[-1]
    replies = [PHRASES["greeting"]] + [event["reply"] for event in demo_events if event["event"] == "turn"]
    timings = [None] + [event["endpoint_s"] + event["reply_after_s"] for event in demo_events if event["event"] == "turn"]
    boundaries = [0.0] + [line["end"] for line in caller_lines]
    for reply, after, boundary in zip(replies, timings, boundaries):
        start = next((moment for moment in loud if moment >= boundary), boundary)
        switchboard_lines.append({"who": "switchboard", "text": reply, "start": start, "reply_after_s": after})

    with wave.open(str(output / "demo-call.wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(track.tobytes())
    lines = sorted(caller_lines + switchboard_lines, key=lambda line: line["start"])
    (output / "demo-call.json").write_text(json.dumps({"seconds": len(track) / SAMPLE_RATE, "lines": lines},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(track) / SAMPLE_RATE:.1f}s of call, {len(lines)} lines, written to {output}")


if __name__ == "__main__":
    main()
