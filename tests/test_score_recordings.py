import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import knowledge
import score_recordings as score
from conversation import ASK_FOR_PHONE_NUMBER

INTENTS_THAT_ARE_NOT_TOPICS = {"own_account", "transfer", "goodbye", "other"}


def test_old_and_new_tone_placement_are_the_same_word():
    assert score.word_key("khóa") == score.word_key("khoá")
    assert score.word_key("khóa") != score.word_key("khoa")


def test_word_errors_are_counted():
    expected = score.words_of("giá vàng hôm nay")
    assert score.edit_distance(expected, score.words_of("giá vàng hôm nay")) == 0
    assert score.edit_distance(expected, score.words_of("giá vàn hôm")) == 2


def test_intent_comes_from_the_call_log():
    assert score.intent_of({"topic": "gold_price"}) == "gold_price"
    assert score.intent_of({"transfer": True}) == "transfer"
    assert score.intent_of({"hang_up": True}) == "goodbye"
    assert score.intent_of({"reply": ASK_FOR_PHONE_NUMBER}) == "own_account"
    assert score.intent_of({"lookup": "check_balance"}) == "own_account"
    assert score.intent_of({"reply": "Dạ mưa suốt ạ."}) == "other"


def test_every_sentence_in_the_test_set_has_a_known_intent():
    known = set(knowledge.topic_names()) | INTENTS_THAT_ARE_NOT_TOPICS
    lines = score.TEST_SET.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 100
    assert all(line.split("\t")[1] in known for line in lines)
