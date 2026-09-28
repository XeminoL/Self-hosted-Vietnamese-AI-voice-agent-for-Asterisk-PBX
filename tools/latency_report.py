import argparse
import sys
from pathlib import Path

import numpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from call_log import read_calls

STAGES = [
    ("endpoint_s", "wait for the caller to stop"),
    ("asr_s", "hear (gipformer)"),
    ("think_s", "understand (model + rules)"),
    ("speak_s", "speak (Piper)"),
    ("reply_after_s", "caller stops -> reply queued"),
]


def spoken_turns(calls, since):
    return [event for call in calls for event in call
            if event["event"] == "turn" and event.get("heard") and call[0].get("clock", "") >= since]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="", help="only calls that started at or after this clock, e.g. 2026-09-28 07:00")
    args = parser.parse_args()

    turns = spoken_turns(read_calls(), args.since)
    if not turns:
        sys.exit("no spoken turns in app/calls/")
    print(f"{len(turns)} spoken turns from app/calls/\n")
    print(f"{'stage':34s} {'p50':>6s} {'p95':>6s} {'max':>6s}")
    for key, label in STAGES:
        values = [turn[key] for turn in turns]
        print(f"{label:34s} {numpy.percentile(values, 50):6.2f} {numpy.percentile(values, 95):6.2f} {max(values):6.2f}")
    total = [turn["endpoint_s"] + turn["reply_after_s"] for turn in turns]
    print(f"{'caller stops -> reply (total)':34s} {numpy.percentile(total, 50):6.2f} "
          f"{numpy.percentile(total, 95):6.2f} {max(total):6.2f}")
    slow = sorted(turns, key=lambda turn: turn["reply_after_s"], reverse=True)[:3]
    print("\nslowest turns:")
    for turn in slow:
        print(f"  {turn['reply_after_s']:5.2f}s  asr {turn['asr_s']:.2f}  think {turn['think_s']:.2f}  "
              f"speak {turn['speak_s']:.2f}  | {turn['heard']}")


if __name__ == "__main__":
    main()
