import json
import os
import re

import knowledge
import llm_client

FIGURE_SLOT = re.compile(r"\{(\w+)\}")


def use_topics(monkeypatch, folder, topics, figures=None):
    topics_file = folder / "topics.json"
    figures_file = folder / "figures.json"
    topics_file.write_text(json.dumps(topics, ensure_ascii=False), encoding="utf-8")
    figures_file.write_text(json.dumps(figures or {}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(knowledge, "TOPICS_FILE", topics_file)
    monkeypatch.setattr(knowledge, "FIGURES_FILE", figures_file)
    return figures_file


def test_answers_have_their_figures_filled_in():
    for topic in knowledge.topic_names():
        assert all("{" not in answer for answer in knowledge.answers(topic)), topic


def test_unknown_topic():
    assert knowledge.answer("no_such_topic") is None


def test_every_topic_has_three_different_answers():
    for topic in knowledge.topic_names():
        assert len(set(knowledge.answers(topic))) >= 3, topic


def test_asking_the_same_topic_again_never_repeats_the_answer():
    for topic in knowledge.topic_names():
        replies = [knowledge.answer(topic) for _ in range(6)]
        assert all(first != second for first, second in zip(replies, replies[1:])), topic


def test_every_answer_of_a_topic_uses_the_same_figures():
    topics = json.loads(knowledge.TOPICS_FILE.read_text(encoding="utf-8"))
    for name, topic in topics.items():
        assert len({frozenset(FIGURE_SLOT.findall(answer)) for answer in topic["answers"]}) == 1, name


def test_find_topic():
    assert knowledge.find_topic("giá vàng thế nào rồi") == "gold_price"
    assert knowledge.find_topic("đô la hôm nay bao nhiêu") == "usd_rate"
    assert knowledge.find_topic("quên mật khẩu thì làm sao") == "forgot_password"
    assert knowledge.find_topic("lãi suất tiết kiệm bao nhiêu") == "savings_rate"


def test_several_keywords_of_one_topic_beat_one_longer_keyword():
    assert knowledge.find_topic("chi nhánh mở cửa mấy giờ") == "opening_hours"
    assert knowledge.find_topic("chi nhánh ở đâu") == "branches"


def test_out_of_scope_matches_nothing():
    assert knowledge.find_topic("thời tiết hôm nay thế nào") is None
    assert knowledge.find_topic("kể cho tôi một câu chuyện") is None


def test_figures_are_read_again_after_the_file_changes(tmp_path, monkeypatch):
    figures_file = use_topics(monkeypatch, tmp_path, {"price": {"answers": ["Giá là {price}."], "keywords": ["giá"]}},
                              {"price": "một trăm"})
    assert knowledge.answer("price") == "Giá là một trăm."
    figures_file.write_text(json.dumps({"price": "hai trăm"}, ensure_ascii=False), encoding="utf-8")
    os.utime(figures_file, (0, 0))
    assert knowledge.answer("price") == "Giá là hai trăm."


def test_a_new_topic_needs_only_the_data_file(tmp_path, monkeypatch):
    topics = json.loads(knowledge.TOPICS_FILE.read_text(encoding="utf-8"))
    topics["insurance"] = {"answers": ["Dạ bảo hiểm mua tại quầy ạ."], "keywords": ["bảo hiểm"]}
    use_topics(monkeypatch, tmp_path, topics)
    assert "insurance" in llm_client.system_prompt()
    assert knowledge.find_topic("cho tôi hỏi về bảo hiểm") == "insurance"
    assert knowledge.answer("insurance") == "Dạ bảo hiểm mua tại quầy ạ."


def test_prompt_lists_every_topic_and_lookup():
    prompt = llm_client.system_prompt()
    assert llm_client.TOPIC_SLOT not in prompt and llm_client.LOOKUP_SLOT not in prompt
    assert all(topic in prompt for topic in knowledge.topic_names())
    assert "check_balance" in prompt and "lock_card" in prompt
