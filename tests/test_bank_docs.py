import json
import re
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import bank_docs


def test_has_enough_topics():
    assert len(bank_docs.available_topics()) >= 15


def test_reading_a_topic_fills_in_figures():
    sentence = bank_docs.read_topic("lai_suat_tiet_kiem")
    assert "{" not in sentence and "}" not in sentence


def test_unknown_topic_returns_none():
    assert bank_docs.read_topic("khong_co_chu_de_nay") is None


def test_files_are_reread_when_figures_change(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    topics_file = docs_dir / "topics.json"
    figures_file = docs_dir / "figures.json"
    topics_file.write_text(json.dumps({"gia": {"answers": ["Giá là {muc_gia} đồng."],
                                               "keywords": ["giá"]}}),
                           encoding="utf-8")
    figures_file.write_text(json.dumps({"muc_gia": "một trăm"}), encoding="utf-8")

    monkeypatch.setattr(bank_docs, "TOPICS_FILE", str(topics_file))
    monkeypatch.setattr(bank_docs, "FIGURES_FILE", str(figures_file))
    monkeypatch.setattr(bank_docs, "_cache",
                        {"topics": {}, "figures": {}, "mtime": {}})

    assert "một trăm" in bank_docs.read_topic("gia")

    figures_file.write_text(json.dumps({"muc_gia": "hai trăm"}), encoding="utf-8")
    os.utime(figures_file, (0, 0))
    assert "hai trăm" in bank_docs.read_topic("gia")


def test_every_topic_has_several_phrasings():
    for name in bank_docs.available_topics():
        assert len(set(bank_docs.topic_phrasings(name))) >= 3, name


def test_same_topic_twice_in_a_row_never_repeats_the_sentence():
    for name in bank_docs.available_topics():
        replies = [bank_docs.read_topic(name) for _ in range(6)]
        assert all(first != second for first, second in zip(replies, replies[1:])), name


def test_every_phrasing_keeps_the_same_figures():
    topics = json.loads(Path(bank_docs.TOPICS_FILE).read_text(encoding="utf-8"))
    for name, topic in topics.items():
        figure_sets = {frozenset(re.findall(r"\{(\w+)\}", sentence)) for sentence in topic["answers"]}
        assert len(figure_sets) == 1, name


def test_find_topic_by_keyword():
    assert bank_docs.find_topic_by_keyword("giá vàng thế nào rồi") == "gia_vang"
    assert bank_docs.find_topic_by_keyword("đô la hôm nay bao nhiêu") == "ty_gia_do"
    assert bank_docs.find_topic_by_keyword("quên mật khẩu thì làm sao") == "quen_mat_khau"


def test_longer_keyword_wins():
    assert bank_docs.find_topic_by_keyword("lãi suất tiết kiệm bao nhiêu") == "lai_suat_tiet_kiem"


def test_new_topic_needs_only_the_data_file(tmp_path, monkeypatch):
    import conversation

    topics = json.loads(Path(bank_docs.TOPICS_FILE).read_text(encoding="utf-8"))
    topics["bao_hiem"] = {"answers": ["Dạ bảo hiểm mua tại quầy ạ."], "keywords": ["bảo hiểm"]}
    topics_file = tmp_path / "topics.json"
    topics_file.write_text(json.dumps(topics, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(bank_docs, "TOPICS_FILE", str(topics_file))
    monkeypatch.setattr(bank_docs, "_cache", {"topics": {}, "figures": {}, "mtime": {}})

    assert "bao_hiem" in conversation.system_prompt()
    assert bank_docs.find_topic_by_keyword("cho tôi hỏi về bảo hiểm") == "bao_hiem"
    assert bank_docs.read_topic("bao_hiem") == "Dạ bảo hiểm mua tại quầy ạ."


def test_prompt_lists_every_topic_and_has_no_slot_left():
    import conversation

    prompt = conversation.system_prompt()
    assert conversation.TOPIC_LIST_SLOT not in prompt
    assert all(topic in prompt for topic in bank_docs.available_topics())


def test_out_of_scope_sentence_matches_nothing():
    assert bank_docs.find_topic_by_keyword("thời tiết hôm nay thế nào") is None
    assert bank_docs.find_topic_by_keyword("kể cho tôi một câu chuyện") is None