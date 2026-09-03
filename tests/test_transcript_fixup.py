import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from transcript_fixup import fix_near_homophones


def test_fixes_so_dua_to_so_du():
    assert "số dư" in fix_near_homophones("cho tôi biết số dừa tài khoản")


def test_fixes_tai_phan_to_tai_khoan():
    assert "tài khoản" in fix_near_homophones("số dư tài phản của tôi")


def test_leaves_ordinary_sentence_alone():
    sentence = "hôm nay trời mưa quá"
    assert fix_near_homophones(sentence) == sentence


def test_leaves_already_correct_sentence_alone():
    sentence = "tôi muốn biết số dư tài khoản"
    assert fix_near_homophones(sentence) == sentence


def test_leaves_out_of_scope_sentence_alone():
    sentence = "tôi muốn biết đường tình duyên của tôi"
    assert fix_near_homophones(sentence) == sentence