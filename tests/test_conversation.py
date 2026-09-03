import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import conversation as conv


def test_parse_command_well_formed():
    assert conv.parse_action_command("@TRA tra_so_du 0901234567") == ("tra_so_du", "0901234567")


def test_parse_command_strips_punctuation():
    assert conv.parse_action_command("@TRA tra_so_du: 0901234567.") == ("tra_so_du", "0901234567")


def test_parse_command_unknown_action():
    assert conv.parse_action_command("@TRA khong_co_viec_nay 0901234567") is None


def test_parse_command_missing_argument():
    assert conv.parse_action_command("@TRA tra_so_du") is None


def test_plain_sentence_has_no_command():
    assert conv.parse_action_command("Dạ em xin nghe.") is None


def test_parse_document_topic():
    assert conv.parse_document_topic("@DOC lai_suat_tiet_kiem") == "lai_suat_tiet_kiem"


def test_parse_document_topic_unknown():
    assert conv.parse_document_topic("@DOC chu_de_bia_dat") is None


def test_strip_tags_removes_trailing_command():
    assert conv.strip_tags("Dạ em tra ngay. @TRA tra_so_du 090") == "Dạ em tra ngay."


def test_strip_tags_keeps_clean_sentence():
    assert conv.strip_tags("Dạ em xin nghe.") == "Dạ em xin nghe."


def test_contains_digit():
    assert conv.contains_digit("giá vàng 131 triệu")
    assert not conv.contains_digit("Dạ em không nắm được ạ")


def test_caller_sentence_includes_dialed_number():
    sentence = conv.Conversation._build_caller_sentence("đây", "0901234567")
    assert "0901234567" in sentence


def test_caller_sentence_when_nothing_transcribed():
    assert conv.Conversation._build_caller_sentence("", "0901234567").startswith("đây")


def test_command_dropped_when_llm_invents_number():
    session = conv.Conversation()
    command = session._settle_command("tôi muốn xem số dư", "@TRA tra_so_du 0901234567", "", [])
    assert command is None


def test_dialed_number_wins_when_llm_writes_wrong_one():
    session = conv.Conversation()
    command = session._settle_command("đây", "@TRA tra_so_du 0999999999", "0901234567", [])
    assert command == ("tra_so_du", "0901234567")


def test_defaults_to_balance_when_dialed_but_llm_silent():
    session = conv.Conversation()
    command = session._settle_command("đây", "Dạ em nghe ạ.", "0901234567", [])
    assert command == ("tra_so_du", "0901234567")


def test_lock_card_requires_confirmation():
    session = conv.Conversation()
    command = session._settle_command("khoá thẻ", "@TRA khoa_the 0901234567", "0901234567", [])
    assert command is None
    assert session.action_awaiting_confirmation == ("khoa_the", "0901234567")


def test_consent_runs_the_pending_action():
    session = conv.Conversation()
    session.action_awaiting_confirmation = ("khoa_the", "0901234567")
    assert session._settle_command("đúng rồi", "Dạ.", "", []) == ("khoa_the", "0901234567")


def test_refusal_drops_the_pending_action():
    session = conv.Conversation()
    session.action_awaiting_confirmation = ("khoa_the", "0901234567")
    assert session._settle_command("thôi khỏi", "Dạ.", "", []) is None
    assert session.action_awaiting_confirmation is None


def test_invented_figure_falls_back_to_document():
    session = conv.Conversation()
    sentence = session._filter_llm_sentence("giá vàng thế nào", "Dạ giá vàng 58 triệu ạ.",
                                            False, [])
    assert "58" not in sentence


def test_invented_figure_out_of_scope_says_it_does_not_know():
    session = conv.Conversation()
    sentence = session._filter_llm_sentence("thời tiết hôm nay", "Dạ hôm nay 30 độ C ạ.",
                                            False, [])
    assert sentence == conv.OUT_OF_SCOPE


def test_clean_sentence_passes_through():
    session = conv.Conversation()
    sentence = "Dạ em là Duyên ạ."
    assert session._filter_llm_sentence("em tên gì", sentence, False, []) == sentence


def test_unfinished_sentence_is_never_spoken():
    session = conv.Conversation()
    cut_off = "Lãi suất tiết kiệm là phần tiền lãi được tính trên số tiền gửi, được trả lại cho"
    spoken = session._filter_llm_sentence("lãi suất tiết kiệm là gì", cut_off, True, [])
    assert spoken != cut_off


def test_unfinished_sentence_falls_back_to_document():
    session = conv.Conversation()
    spoken = session._filter_llm_sentence("lãi suất tiết kiệm là gì",
                                          "Lãi suất tiết kiệm là phần tiền lãi được", True, [])
    assert "bốn phẩy sáu" in spoken


def test_unfinished_sentence_out_of_scope_says_it_does_not_know():
    session = conv.Conversation()
    spoken = session._filter_llm_sentence("kể chuyện gì đi",
                                          "Ngày xưa có một người rất là", True, [])
    assert spoken == conv.OUT_OF_SCOPE


def test_finished_sentence_without_digits_still_passes():
    session = conv.Conversation()
    sentence = "Dạ em nghe ạ."
    assert session._filter_llm_sentence("alo", sentence, False, []) == sentence