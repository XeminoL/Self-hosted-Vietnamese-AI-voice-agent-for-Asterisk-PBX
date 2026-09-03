import json
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
    topics_file.write_text(json.dumps({"gia": "Giá là {muc_gia} đồng."}),
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


def test_find_topic_by_keyword():
    assert bank_docs.find_topic_by_keyword("giá vàng thế nào rồi") == "gia_vang"
    assert bank_docs.find_topic_by_keyword("đô la hôm nay bao nhiêu") == "ty_gia_do"
    assert bank_docs.find_topic_by_keyword("quên mật khẩu thì làm sao") == "quen_mat_khau"


def test_longer_keyword_wins():
    assert bank_docs.find_topic_by_keyword("lãi suất tiết kiệm bao nhiêu") == "lai_suat_tiet_kiem"


def test_out_of_scope_sentence_matches_nothing():
    assert bank_docs.find_topic_by_keyword("thời tiết hôm nay thế nào") is None
    assert bank_docs.find_topic_by_keyword("kể cho tôi một câu chuyện") is None