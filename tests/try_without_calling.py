import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from conversation import Conversation

SAMPLE_TURNS = [
    "tôi muốn biết số dư tài khoản",
    "lãi suất tiết kiệm bao nhiêu",
    "chuyển tiền mất phí không",
    "mấy giờ ngân hàng mở cửa",
    "tôi muốn vay tiền thì cần gì",
    "rút tiền ở máy atm khác có mất phí không",
    "quên mật khẩu thì làm sao",
    "đô la hôm nay bao nhiêu",
    "giá vàng thế nào rồi",
    "thời tiết hôm nay thế nào",
    "cho tôi gặp người thật",
]
FAKE_PHONE_NUMBER = "0901234567"
RESULT_FILE = "ket-qua-thu.txt"


def print_result(lines):
    text = "\n".join(lines)
    Path(RESULT_FILE).write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    print(f"\nBan co dau: cat tests/{RESULT_FILE}")


def run(turns):
    session = Conversation()
    lines = []
    durations = []

    for index, sentence in enumerate(turns, start=1):
        dialed_number = FAKE_PHONE_NUMBER if "bấm số" in sentence else ""
        started = time.time()
        result = session.respond(sentence, dialed_number)
        duration = time.time() - started
        durations.append(duration)

        lines.append(f"--- luot {index} ({duration:.1f}s) ---")
        lines.append(f"  nguoi goi: {sentence}")
        for line in result.log:
            lines.append(f"  [{line}]")
        lines.append(f"  tong dai : "
                     f"{'(chuyen cho nhan vien)' if result.transfer else result.reply}")
        lines.append("")

    lines.append(f"HIEU: nhanh nhat {min(durations):.1f}s | "
                 f"cham nhat {max(durations):.1f}s | "
                 f"trung binh {sum(durations) / len(durations):.1f}s")
    return lines


if __name__ == "__main__":
    print_result(run(sys.argv[1:] or SAMPLE_TURNS))