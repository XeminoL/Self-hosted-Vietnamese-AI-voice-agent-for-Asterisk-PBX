import argparse
import collections
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from call_log import read_calls
from conversation import SAME_MEANING_SENTENCES, ASK_FOR_PHONE_NUMBER

SENTENCES_FILE = Path(__file__).resolve().parent / "cau-thu.tsv"
TONE_MARKS = {"̀", "́", "̃", "̉", "̣"}
TOPIC_NOTES = [re.compile(r"DOC tai lieu(?: moi)?: (\w+)"), re.compile(r"tu khoa (\w+) ->"),
               re.compile(r"-> tu khoa: (\w+)")]
ACCOUNT_NOTES = ("nho viec", "TRA ", "HOI XAC NHAN", "ngai bam so")
ASKS_FOR_NUMBER = next(group for group in SAME_MEANING_SENTENCES if ASK_FOR_PHONE_NUMBER in group)


def word_key(word):
    letters = unicodedata.normalize("NFD", word.lower())
    tone = "".join(c for c in letters if c in TONE_MARKS)
    rest = unicodedata.normalize("NFC", "".join(c for c in letters if c not in TONE_MARKS))
    return rest, tone


def words_of(text):
    return [word_key(word) for word in re.sub(r"[^\w\s]", " ", text).split()]


def edit_distance(expected, heard):
    previous = list(range(len(heard) + 1))
    for i, want in enumerate(expected, start=1):
        current = [i]
        for j, got in enumerate(heard, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (want != got)))
        previous = current
    return previous[-1]


def intent_of(turn):
    notes = " | ".join(turn.get("notes", []))
    if turn.get("transfer"):
        return "chuyen"
    if turn.get("hang_up"):
        return "chao"
    for pattern in TOPIC_NOTES:
        found = pattern.search(notes)
        if found:
            return found.group(1)
    if any(mark in notes for mark in ACCOUNT_NOTES) or turn.get("reply") in ASKS_FOR_NUMBER:
        return "tai_khoan"
    return "khac"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", required=True, help="clock of the first test call, e.g. '2026-09-29 20:00'")
    args = parser.parse_args()

    labelled = [line.split("\t") for line in SENTENCES_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    spoken = [event for call in read_calls() if call[0].get("clock", "") >= args.since
              for event in call if event["event"] == "turn" and event.get("audio_s")]
    if len(spoken) != len(labelled):
        print(f"warning: {len(spoken)} spoken turns but {len(labelled)} sentences, pairing the first "
              f"{min(len(spoken), len(labelled))} in order")

    errors = words = right = 0
    misses = collections.Counter()
    for (sentence, expected), turn in zip(labelled, spoken):
        want, got = words_of(sentence), words_of(turn.get("heard", ""))
        errors += edit_distance(want, got)
        words += len(want)
        decided = intent_of(turn)
        right += decided == expected
        if decided != expected:
            misses[(expected, decided)] += 1
            print(f"  {expected:22s} -> {decided:22s} | said: {sentence} | heard: {turn.get('heard', '')}")
    paired = min(len(spoken), len(labelled))
    print(f"\nWER {errors / max(words, 1):.1%} over {words} words")
    print(f"understood {right}/{paired} = {right / max(paired, 1):.1%}")
    for (expected, decided), count in misses.most_common():
        print(f"  {count} x {expected} taken as {decided}")


if __name__ == "__main__":
    main()
