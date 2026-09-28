import argparse
import collections
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from call_log import read_calls
from conversation import ASKING_FOR_NUMBER, CONFIRMATION_QUESTIONS

TEST_SET = Path(__file__).resolve().parent / "spoken_test_set.tsv"
TONE_MARKS = {"̀", "́", "̃", "̉", "̣"}
ASKS_ABOUT_THE_ACCOUNT = set(ASKING_FOR_NUMBER) | set(CONFIRMATION_QUESTIONS.values())


def word_key(word):
    letters = unicodedata.normalize("NFD", word.lower())
    tone = "".join(c for c in letters if c in TONE_MARKS)
    rest = unicodedata.normalize("NFC", "".join(c for c in letters if c not in TONE_MARKS))
    return rest, tone


def words_of(text):
    return [word_key(word) for word in re.sub(r"[^\w\s]", " ", text).split()]


def edit_distance(expected, heard):
    previous = list(range(len(heard) + 1))
    for i, wanted in enumerate(expected, start=1):
        current = [i]
        for j, got in enumerate(heard, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (wanted != got)))
        previous = current
    return previous[-1]


def intent_of(turn):
    if turn.get("transfer"):
        return "transfer"
    if turn.get("hang_up"):
        return "goodbye"
    if turn.get("topic"):
        return turn["topic"]
    if turn.get("lookup") or turn.get("reply") in ASKS_ABOUT_THE_ACCOUNT:
        return "own_account"
    return "other"


def spoken_turns(since):
    return [event for call in read_calls() if call[0].get("clock", "") >= since
            for event in call if event["event"] == "turn" and event.get("audio_s")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", required=True, help="clock of the first test call, e.g. '2026-09-29 20:00'")
    args = parser.parse_args()

    labelled = [line.split("\t") for line in TEST_SET.read_text(encoding="utf-8").splitlines() if line.strip()]
    turns = spoken_turns(args.since)
    if len(turns) != len(labelled):
        print(f"warning: {len(turns)} spoken turns but {len(labelled)} sentences, "
              f"pairing the first {min(len(turns), len(labelled))} in order")

    errors = words = right = 0
    misses = collections.Counter()
    for (sentence, expected), turn in zip(labelled, turns):
        wanted, heard = words_of(sentence), words_of(turn.get("heard", ""))
        errors += edit_distance(wanted, heard)
        words += len(wanted)
        decided = intent_of(turn)
        right += decided == expected
        if decided != expected:
            misses[(expected, decided)] += 1
            print(f"  {expected:20s} -> {decided:20s} | said: {sentence} | heard: {turn.get('heard', '')}")
    paired = min(len(turns), len(labelled))
    print(f"\nword error rate {errors / max(words, 1):.1%} over {words} words")
    print(f"understood {right}/{paired} = {right / max(paired, 1):.1%}")
    for (expected, decided), count in misses.most_common():
        print(f"  {count} x {expected} taken as {decided}")


if __name__ == "__main__":
    main()
