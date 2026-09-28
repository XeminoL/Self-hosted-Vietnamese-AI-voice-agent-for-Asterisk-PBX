import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from conversation import Conversation

SAMPLE_TURNS = [
    "tôi muốn biết số dư tài khoản",
    "lãi suất tiết kiệm bao nhiêu",
    "chuyển tiền mất phí không",
    "tôi muốn vay tiền thì cần gì",
    "thời tiết hôm nay thế nào",
    "cho tôi gặp người thật",
]


def main():
    session = Conversation()
    for sentence in sys.argv[1:] or SAMPLE_TURNS:
        started = time.monotonic()
        result = session.respond(sentence)
        print(f"caller: {sentence}")
        for note in result.notes:
            print(f"    {note}")
        print(f"switchboard ({time.monotonic() - started:.1f}s): {'(transfer)' if result.transfer else result.reply}\n")


if __name__ == "__main__":
    main()
