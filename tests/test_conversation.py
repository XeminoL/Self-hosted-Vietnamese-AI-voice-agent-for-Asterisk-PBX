import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import conversation as conv
from bank_docs import topic_phrasings


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


def test_parse_command_ignores_diacritics_in_action():
    assert conv.parse_action_command("@TRA khoá_the 0901234567") == ("khoa_the", "0901234567")


def test_parse_command_takes_known_action_before_extra_suffix():
    assert conv.parse_action_command("@TRA tra_han_muc_mac_dinh 0901234") == ("tra_han_muc", "0901234")


def test_vague_answer_on_a_known_topic_reads_the_document():
    log = []
    reply = conv.Conversation()._filter_llm_sentence(
        "tôi muốn vay tiền thì cần gì", "Anh chị cần xem thông tin vay cần gì ạ.", False, log)
    assert reply in topic_phrasings("vay_can_gi")


def test_asking_to_dial_is_not_replaced_by_a_document():
    log = []
    reply = conv.Conversation()._filter_llm_sentence(
        "hạn mức thẻ của tôi bao nhiêu", conv.ASK_FOR_PHONE_NUMBER, False, log)
    assert reply == conv.ASK_FOR_PHONE_NUMBER


def test_asking_to_dial_for_general_info_reads_the_document():
    reply = conv.Conversation()._filter_llm_sentence(
        "giá vàng thế nào rồi", conv.ASK_FOR_PHONE_NUMBER, False, [])
    assert reply in topic_phrasings("gia_vang")


def test_small_talk_stays_small_talk():
    log = []
    reply = conv.Conversation()._filter_llm_sentence(
        "hôm nay trời mưa quá", "Dạ mưa suốt mấy hôm nay ạ.", False, log)
    assert reply == "Dạ mưa suốt mấy hôm nay ạ."


def test_invented_topic_falls_back_to_keywords_or_out_of_scope():
    conversation = conv.Conversation()
    assert conversation._settle_document("giá vàng thế nào", "@DOC gia_vang_hom_nay_ne", []) \
        in topic_phrasings("gia_vang")
    assert conversation._settle_document("kể chuyện đi", "@DOC chu_de_bia", []) == conv.OUT_OF_SCOPE


def test_keyword_beats_a_wrong_topic_choice():
    reply = conv.Conversation()._settle_document(
        "ngân hàng của bạn là ngân hàng gì", "@DOC lai_suat_tiet_kiem", [])
    assert reply in topic_phrasings("gioi_thieu")


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
    sentence = "Dạ em mới vào làm thôi ạ."
    assert session._filter_llm_sentence("em bao nhiêu tuổi", sentence, False, []) == sentence


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


def test_fixed_sentence_is_said_another_way_when_repeated():
    for group in conv.SAME_MEANING_SENTENCES:
        for sentence in group:
            assert conv.say_differently(sentence, sentence) in group
            assert conv.say_differently(sentence, sentence) != sentence


def test_other_sentence_repeated_gets_a_reminder_opening():
    sentence = "Dạ số dư tài khoản của anh chị là 5 triệu đồng."
    assert conv.say_differently(sentence, sentence) == "Dạ như em vừa nói, số dư tài khoản của anh chị là 5 triệu đồng."


def test_different_sentence_is_left_alone():
    assert conv.say_differently("Dạ vâng ạ.", "Dạ em xin nghe.") == "Dạ vâng ạ."


def test_silence_twice_does_not_repeat_the_same_words():
    conversation = conv.Conversation()
    first = conversation.respond("", "").reply
    second = conversation.respond("", "").reply
    third = conversation.respond("", "").reply
    assert first != second and second != third


def test_every_way_to_ask_for_the_number_still_asks_to_dial():
    group = next(g for g in conv.SAME_MEANING_SENTENCES if conv.ASK_FOR_PHONE_NUMBER in g)
    assert all(conv.ASKS_TO_DIAL in sentence.lower() for sentence in group)


def _talk(monkeypatch, llm_lines, caller_lines):
    answers = iter(llm_lines)
    monkeypatch.setattr(conv, "ask_llm", lambda history, slot=None: (next(answers), False, {}))
    conversation = conv.Conversation()
    return conversation, [conversation.respond(line, "") for line in caller_lines]


def test_objection_detected():
    for sentence in ("không phải", "Không đúng rồi em", "sai rồi", "ơ nhầm rồi",
                     "tôi không hỏi cái đó", "không phải, tôi hỏi giá vàng"):
        assert conv.is_objection(sentence), sentence


def test_questions_are_not_objections():
    for sentence in ("không biết lãi suất bao nhiêu", "phí thường niên là sao",
                     "giá vàng hôm nay", "không có thẻ thì sao"):
        assert not conv.is_objection(sentence), sentence


def test_objection_with_new_topic_apologises_and_reads_it(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC lai_suat_vay"],
                       ["lãi suất vay bao nhiêu", "không phải, tôi hỏi giá vàng"])
    assert results[1].reply.startswith(conv.APOLOGY_OPENING)
    assert "vàng" in results[1].reply


def test_objection_never_reads_the_rejected_topic_again(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang"],
                       ["giá vàng hôm nay", "sai rồi, không phải giá vàng"])
    assert "vàng" not in results[1].reply


def test_plain_objection_asks_again(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang"], ["giá vàng", "không phải"])
    assert results[1].reply == conv.ASK_AGAIN_AFTER_MISTAKE


def test_two_objections_in_a_row_go_to_staff(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang"], ["giá vàng", "không phải", "sai rồi"])
    assert results[2].transfer


def test_objection_count_resets_after_a_normal_question(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang", "@DOC ty_gia_do"],
                       ["giá vàng", "không phải", "đô la bao nhiêu", "sai rồi"])
    assert not results[3].transfer


def test_no_to_a_confirmation_is_a_refusal_not_an_objection(monkeypatch):
    conversation, results = _talk(monkeypatch, ["@TRA khoa_the 0901234567", "Dạ vâng ạ."],
                                  ["khoá thẻ giúp tôi", "không phải"])
    assert not results[1].transfer
    assert conversation.objections_in_a_row == 0


def test_short_words_only_match_whole_words():
    assert conv.says_any("ừ chuyển đi", conv.YES_TO_STAFF)
    assert not conv.says_any("vừa chừng thôi", ("ừ",))


def test_reluctant_to_dial_gets_an_explanation(monkeypatch):
    _, results = _talk(monkeypatch, ["@TRA tra_so_du"],
                       ["số dư của tôi bao nhiêu", "tôi không có điện thoại ở đây"])
    assert results[0].reply == conv.ASK_FOR_PHONE_NUMBER
    assert results[1].reply == conv.WHY_WE_NEED_THE_NUMBER


def test_yes_after_the_explanation_goes_to_staff(monkeypatch):
    _, results = _talk(monkeypatch, ["@TRA tra_so_du"],
                       ["số dư của tôi bao nhiêu", "sao phải bấm", "ừ chuyển đi"])
    assert results[2].transfer


def test_no_after_the_explanation_keeps_talking(monkeypatch):
    _, results = _talk(monkeypatch, ["@TRA tra_so_du", "Dạ vâng, anh chị cần gì thêm ạ?"],
                       ["số dư của tôi bao nhiêu", "sao phải bấm", "thôi khỏi"])
    assert not results[2].transfer
    assert results[2].reply == "Dạ vâng, anh chị cần gì thêm ạ?"


def test_annoyed_caller_is_offered_staff(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang"], ["giá vàng", "phiền quá đi", "được"])
    assert results[1].reply == conv.OFFER_STAFF
    assert results[2].transfer


def test_asking_for_a_person_transfers_right_away(monkeypatch):
    _, results = _talk(monkeypatch, [], ["cho tôi gặp nhân viên"])
    assert results[0].transfer


def test_reluctance_words_mean_nothing_without_a_request_to_dial(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC thoi_gian_chuyen_tien"],
                       ["tại sao chuyển tiền lâu vậy"])
    assert not results[0].transfer
    assert results[0].reply != conv.WHY_WE_NEED_THE_NUMBER


def test_having_no_phone_is_not_turned_into_phone_number():
    from transcript_fixup import fix_near_homophones
    assert fix_near_homophones("tôi không có điện thoại") == "tôi không có điện thoại"


def test_saying_goodbye_ends_the_call(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang"], ["giá vàng", "vậy thôi, tạm biệt em"])
    assert results[1].reply == conv.GOODBYE
    assert results[1].hang_up


def test_thanks_asks_if_anything_else_then_no_ends_the_call(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang"], ["giá vàng", "cảm ơn em", "không"])
    assert results[1].reply == conv.ANYTHING_ELSE and not results[1].hang_up
    assert results[2].hang_up


def test_thanks_with_a_new_question_keeps_going(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang", "@DOC ty_gia_do"],
                       ["giá vàng", "cảm ơn, còn đô la thì sao"])
    assert not results[1].hang_up
    assert "đô" in results[1].reply


def test_no_after_anything_else_with_a_question_is_not_goodbye(monkeypatch):
    _, results = _talk(monkeypatch, ["@DOC gia_vang", "@DOC phi_thuong_nien"],
                       ["giá vàng", "cảm ơn", "không, cho hỏi phí thường niên"])
    assert not results[2].hang_up


def test_menu_key_asks_for_the_number_then_runs_that_action():
    conversation = conv.Conversation()
    assert conversation.respond("", "", "3").reply == conv.ASK_FOR_PHONE_NUMBER
    assert conversation.expects_number()
    reply = conversation.respond("", "0901234567").reply
    assert "hạn mức" in reply and "20 triệu" in reply
    assert not conversation.expects_number()


def test_menu_card_lock_asks_to_confirm_then_locks(monkeypatch):
    import copy
    import bank_data
    monkeypatch.setattr(bank_data, "CUSTOMERS", copy.deepcopy(bank_data.CUSTOMERS))
    bank_data.CUSTOMERS["0987654321"]["trang_thai_the"] = "đang hoạt động"
    conversation = conv.Conversation()
    conversation.respond("", "", "4")
    assert conversation.respond("", "0987654321").reply == conv.CONFIRMATION_QUESTIONS["khoa_the"]
    assert "thành công" in conversation.respond("đúng rồi", "").reply


def test_refusing_the_confirmation_cancels_without_the_model(monkeypatch):
    monkeypatch.setattr(conv, "ask_llm", None)
    conversation = conv.Conversation()
    conversation.respond("", "", "4")
    conversation.respond("", "0987654321")
    assert conversation.respond("thôi không khoá nữa", "").reply == conv.CANCELLED
    assert conversation.respond("không", "").hang_up


def test_key_zero_goes_to_staff_and_unknown_key_reads_the_menu():
    conversation = conv.Conversation()
    assert conversation.respond("", "", "0").transfer
    assert conversation.respond("", "", "9").reply == conv.MENU


def test_clear_topic_question_skips_the_model(monkeypatch):
    monkeypatch.setattr(conv, "ask_llm", None)
    conversation = conv.Conversation()
    assert conversation.respond("lãi suất tiết kiệm bao nhiêu", "").reply in topic_phrasings("lai_suat_tiet_kiem")
    assert conversation.history[-1]["content"] == "@DOC lai_suat_tiet_kiem"


def test_own_account_question_still_asks_the_model(monkeypatch):
    _, results = _talk(monkeypatch, ["@TRA tra_han_muc"], ["hạn mức thẻ của tôi bao nhiêu"])
    assert results[0].reply == conv.ASK_FOR_PHONE_NUMBER


def test_action_named_before_the_number_runs_without_asking_the_model_again(monkeypatch):
    conversation, results = _talk(monkeypatch, ["@TRA tra_han_muc"], ["hạn mức thẻ của tôi bao nhiêu"])
    monkeypatch.setattr(conv, "ask_llm", None)
    reply = conversation.respond("", "0901234567").reply
    assert "hạn mức" in reply and "20 triệu" in reply


def test_card_lock_named_by_voice_still_asks_to_confirm(monkeypatch):
    conversation, _ = _talk(monkeypatch, ["@TRA khoa_the"], ["tôi muốn khoá thẻ của tôi"])
    monkeypatch.setattr(conv, "ask_llm", None)
    assert conversation.respond("", "0901234567").reply == conv.CONFIRMATION_QUESTIONS["khoa_the"]


def test_pending_action_is_forgotten_when_the_caller_moves_on(monkeypatch):
    conversation, _ = _talk(monkeypatch, ["@TRA tra_so_du"], ["số dư của tôi bao nhiêu", "giá vàng hôm nay"])
    assert conversation.pending_action is None
    assert not conversation.expects_number()


def test_minimum_balance_is_general_info_not_the_callers_balance(monkeypatch):
    monkeypatch.setattr(conv, "ask_llm", None)
    reply = conv.Conversation().respond("số dư tối thiểu là bao nhiêu", "").reply
    assert reply in topic_phrasings("so_du_toi_thieu")


def test_asking_if_it_is_a_machine_gets_an_honest_answer_not_a_transfer(monkeypatch):
    monkeypatch.setattr(conv, "ask_llm", None)
    result = conv.Conversation().respond("em là người thật hay máy", "")
    assert not result.transfer
    assert result.reply in topic_phrasings("tro_ly_tu_dong")


def test_asking_for_a_real_person_still_transfers(monkeypatch):
    monkeypatch.setattr(conv, "ask_llm", None)
    assert conv.Conversation().respond("tôi muốn nói chuyện với người thật", "").transfer
