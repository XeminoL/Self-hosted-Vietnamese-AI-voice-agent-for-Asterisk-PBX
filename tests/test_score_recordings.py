import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_recordings as score


def test_old_and_new_tone_placement_are_the_same_word():
    assert score.word_key("khóa") == score.word_key("khoá")
    assert score.word_key("khóa") != score.word_key("khoa")


def test_word_error_counts():
    expected = score.words_of("giá vàng hôm nay")
    assert score.edit_distance(expected, score.words_of("giá vàng hôm nay")) == 0
    assert score.edit_distance(expected, score.words_of("giá vàn hôm")) == 2


def test_intent_is_read_from_the_call_log():
    assert score.intent_of({"notes": ["tu khoa gia_vang -> doc tai lieu, khong hoi LLM"]}) == "gia_vang"
    assert score.intent_of({"notes": ["HIEU: @DOC ty_gia_do", "DOC tai lieu: ty_gia_do"]}) == "ty_gia_do"
    assert score.intent_of({"notes": [], "transfer": True}) == "chuyen"
    assert score.intent_of({"notes": [], "reply": score.ASK_FOR_PHONE_NUMBER}) == "tai_khoan"
    assert score.intent_of({"notes": ["HIEU: Dạ mưa suốt ạ."], "reply": "Dạ mưa suốt ạ."}) == "khac"


def test_every_sentence_has_a_known_intent():
    import bank_docs
    known = set(bank_docs.available_topics()) | {"tai_khoan", "chuyen", "chao", "khac"}
    lines = score.SENTENCES_FILE.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 100
    assert all(line.split("\t")[1] in known for line in lines)
