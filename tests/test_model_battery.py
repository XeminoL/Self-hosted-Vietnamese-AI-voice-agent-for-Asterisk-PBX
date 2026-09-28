import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import conversation

PHONE = "0901234567"
REQUIRED_SCORE = 13
REQUIRED_GUARDED_SCORE = 12
MAX_AVERAGE_SECONDS = 4.0


def _model_is_up():
    try:
        urllib.request.urlopen(conversation.LLM_BASE + "/health", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


pytestmark = pytest.mark.skipif(not _model_is_up(), reason="the model server is not running")


def asks_phone(reply):
    return "bấm" in reply.lower() and "@" not in reply


def _as_the_code_reads_it(reply):
    return (conversation.parse_action_command(reply), conversation.parse_document_topic(reply),
            conversation.TAG_TRANSFER in reply)


def exact(expected):
    return lambda reply: reply.strip() == expected or (
        "@" in reply and _as_the_code_reads_it(reply) == _as_the_code_reads_it(expected))


def plain(reply):
    return "@" not in reply and not any(c.isdigit() for c in reply) and len(reply) > 3


RAW_CASES = [
    ("cho tôi biết số dư tài khoản", asks_phone),
    (f"rồi đây (số điện thoại đã bấm: {PHONE})", exact(f"@TRA tra_so_du {PHONE}")),
    ("lãi suất tiết kiệm bao nhiêu", exact("@DOC lai_suat_tiet_kiem")),
    ("giá vàng thế nào rồi", exact("@DOC gia_vang")),
    ("mấy giờ ngân hàng mở cửa", exact("@DOC gio_lam_viec")),
    ("tôi muốn khoá thẻ", asks_phone),
    ("cho tôi gặp người thật", exact("@CHUYEN")),
    ("kể cho tôi một chuyện vui", plain),
    ("hôm nay trời mưa quá", plain),
    (f"tôi muốn khoá thẻ (số điện thoại đã bấm: {PHONE})", exact(f"@TRA khoa_the {PHONE}")),
    ("chuyển tiền mất phí không", exact("@DOC phi_chuyen_tien")),
    ("thẻ tôi mất rồi", lambda r: asks_phone(r) or r.strip() == "@DOC the_bi_mat"),
    ("đô la hôm nay bao nhiêu", exact("@DOC ty_gia_do")),
    (f"hạn mức thẻ của tôi bao nhiêu (số điện thoại đã bấm: {PHONE})", exact(f"@TRA tra_han_muc {PHONE}")),
]


def says(*words):
    return lambda result: not result.transfer and all(w in result.reply.lower() for w in words)


def transfers(result):
    return result.transfer


def polite_and_plain(result):
    return not result.transfer and plain(result.reply)


GUARDED_CASES = [
    ("cho tôi biết là thời tiết hôm nay như nào", polite_and_plain),
    ("bạn tên gì mình nói bạn tên gì", says("duyên")),
    ("ngân hàng của bạn là gì á", says("an tín")),
    ("ngân hàng em tính là ngân hàng gì ta", says("an tín")),
    ("cho tôi biết là mẹ tên gì á", polite_and_plain),
    ("cho tôi biết số dư tài khoản", says("bấm")),
    ("lãi suất tiết kiệm bao nhiêu", says("phần trăm")),
    ("tôi muốn vay tiền thì cần gì", says("căn cước")),
    ("hôm nay trời mưa quá", polite_and_plain),
    ("cho tôi gặp nhân viên đi", transfers),
    ("tôi muốn khoá thẻ", says("bấm")),
    ("giá vàng thế nào rồi", says("triệu")),
]


def _ask_raw(question):
    body = json.dumps({"messages": [{"role": "system", "content": conversation.system_prompt()},
                                    {"role": "user", "content": question}],
                       "max_tokens": conversation.MAX_REPLY_TOKENS, "temperature": conversation.TEMPERATURE,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    request = urllib.request.Request(conversation.LLM_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["choices"][0]["message"]["content"].strip()


def test_raw_model_answers_the_battery():
    failures, seconds = [], []
    for question, check in RAW_CASES:
        started = time.perf_counter()
        reply = _ask_raw(question)
        seconds.append(time.perf_counter() - started)
        if not check(reply):
            failures.append(f"{question} -> {reply}")
    print(f"\nraw battery {len(RAW_CASES) - len(failures)}/{len(RAW_CASES)}, "
          f"average {sum(seconds) / len(seconds):.1f}s")
    assert len(RAW_CASES) - len(failures) >= REQUIRED_SCORE, failures
    assert sum(seconds) / len(seconds) <= MAX_AVERAGE_SECONDS


def test_guarded_replies_to_tricky_questions():
    failures = []
    for question, check in GUARDED_CASES:
        result = conversation.Conversation().respond(question, "")
        if not check(result):
            failures.append(f"{question} -> {'CHUYEN MAY' if result.transfer else result.reply}")
    print(f"\nguarded {len(GUARDED_CASES) - len(failures)}/{len(GUARDED_CASES)}")
    assert len(GUARDED_CASES) - len(failures) >= REQUIRED_GUARDED_SCORE, failures
