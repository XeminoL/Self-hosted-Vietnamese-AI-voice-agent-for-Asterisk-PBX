import time
import urllib.error
import urllib.request

import pytest

import accounts
import knowledge
import llm_client
import model_reply
from conversation import Conversation

PHONE = "0901234567"
REQUIRED_RAW_SCORE = 13
REQUIRED_GUARDED_SCORE = 12
MAX_AVERAGE_SECONDS = 4.0


def _model_is_up():
    try:
        urllib.request.urlopen(llm_client.LLM_BASE + "/health", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


pytestmark = [pytest.mark.real_model,
              pytest.mark.skipif(not _model_is_up(), reason="the model server is not running")]


def asks_to_dial(reply):
    return "bấm" in reply.lower() and "@" not in reply


def plain(reply):
    return "@" not in reply and not model_reply.contains_digit(reply) and len(reply) > 3


def _as_the_code_reads_it(reply):
    return (model_reply.lookup_command(reply, accounts.LOOKUPS),
            model_reply.document_topic(reply, knowledge.topic_names()),
            model_reply.asks_for_transfer(reply))


def reads_as(expected):
    return lambda reply: "@" in reply and _as_the_code_reads_it(reply) == _as_the_code_reads_it(expected)


def dialed(sentence):
    return f"{sentence} (số điện thoại đã bấm: {PHONE})"


RAW_CASES = [
    ("cho tôi biết số dư tài khoản", asks_to_dial),
    (dialed("rồi đây"), reads_as(f"@LOOKUP check_balance {PHONE}")),
    ("lãi suất tiết kiệm bao nhiêu", reads_as("@DOC savings_rate")),
    ("giá vàng thế nào rồi", reads_as("@DOC gold_price")),
    ("mấy giờ ngân hàng mở cửa", reads_as("@DOC opening_hours")),
    ("tôi muốn khoá thẻ", asks_to_dial),
    ("cho tôi gặp người thật", reads_as("@TRANSFER")),
    ("kể cho tôi một chuyện vui", plain),
    ("hôm nay trời mưa quá", plain),
    (dialed("tôi muốn khoá thẻ"), reads_as(f"@LOOKUP lock_card {PHONE}")),
    ("chuyển tiền mất phí không", reads_as("@DOC transfer_fee")),
    ("thẻ tôi mất rồi", lambda reply: asks_to_dial(reply) or reads_as("@DOC lost_card")(reply)),
    ("đô la hôm nay bao nhiêu", reads_as("@DOC usd_rate")),
    (dialed("hạn mức thẻ của tôi bao nhiêu"), reads_as(f"@LOOKUP daily_limit {PHONE}")),
]


def says(*words):
    return lambda result: not result.transfer and all(word in result.reply.lower() for word in words)


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


def test_the_raw_model_answers_the_battery():
    failures, seconds = [], []
    for question, check in RAW_CASES:
        started = time.perf_counter()
        reply = llm_client.ask([{"role": "user", "content": question}]).text
        seconds.append(time.perf_counter() - started)
        if not check(reply):
            failures.append(f"{question} -> {reply}")
    print(f"\nraw battery {len(RAW_CASES) - len(failures)}/{len(RAW_CASES)}, "
          f"average {sum(seconds) / len(seconds):.1f}s")
    assert len(RAW_CASES) - len(failures) >= REQUIRED_RAW_SCORE, failures
    assert sum(seconds) / len(seconds) <= MAX_AVERAGE_SECONDS


def test_the_rules_and_the_model_answer_tricky_questions():
    failures = []
    for question, check in GUARDED_CASES:
        result = Conversation().respond(question)
        if not check(result):
            failures.append(f"{question} -> {'transfer' if result.transfer else result.reply}")
    print(f"\nguarded {len(GUARDED_CASES) - len(failures)}/{len(GUARDED_CASES)}")
    assert len(GUARDED_CASES) - len(failures) >= REQUIRED_GUARDED_SCORE, failures
