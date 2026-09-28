import accounts
import conversation as conv
import knowledge
from conversation import Conversation
from domain import PHRASES
from llm_client import ModelReply

PHONE = "0901234567"
UNLOCKED_PHONE = "0987654321"


def talk(*turns):
    session = Conversation()
    results = [session.respond(*turn) if isinstance(turn, tuple) else session.respond(turn) for turn in turns]
    return session, results


def free_reply(sentence, text, cut_off=False):
    return Conversation()._check_free_reply(sentence, ModelReply(text, cut_off, {}), [])


def test_free_reply_about_a_topic_reads_the_document():
    reply = free_reply("tôi muốn vay tiền thì cần gì", "Anh chị cần xem thông tin vay cần gì ạ.")
    assert reply in knowledge.answers("loan_documents")


def test_asking_to_dial_about_the_callers_own_account_is_kept():
    assert free_reply("hạn mức thẻ của tôi bao nhiêu", conv.ASK_FOR_PHONE_NUMBER) == conv.ASK_FOR_PHONE_NUMBER


def test_asking_to_dial_for_general_information_reads_the_document():
    assert free_reply("giá vàng thế nào rồi", conv.ASK_FOR_PHONE_NUMBER) in knowledge.answers("gold_price")


def test_small_talk_and_clean_sentences_pass_through():
    assert free_reply("hôm nay trời mưa quá", "Dạ mưa suốt mấy hôm nay ạ.") == "Dạ mưa suốt mấy hôm nay ạ."
    assert free_reply("em bao nhiêu tuổi", "Dạ em mới vào làm thôi ạ.") == "Dạ em mới vào làm thôi ạ."


def test_made_up_figures_are_never_spoken():
    assert "58" not in free_reply("giá vàng thế nào", "Dạ giá vàng 58 triệu ạ.")
    assert free_reply("thời tiết hôm nay", "Dạ hôm nay 30 độ C ạ.") == conv.OUT_OF_SCOPE


def test_a_cut_off_reply_is_never_spoken():
    cut_off = "Lãi suất tiết kiệm là phần tiền lãi được"
    assert free_reply("lãi suất tiết kiệm là gì", cut_off, cut_off=True) in knowledge.answers("savings_rate")
    assert free_reply("kể chuyện gì đi", "Ngày xưa có một người rất là", cut_off=True) == conv.OUT_OF_SCOPE


def test_a_made_up_phone_number_is_dropped():
    assert Conversation()._settle_lookup("@LOOKUP check_balance 0901234567", "", []) is None


def test_the_dialed_number_wins_over_the_one_the_model_wrote():
    assert Conversation()._settle_lookup("@LOOKUP check_balance 0999999999", PHONE, []) == ("check_balance", PHONE)


def test_a_dialed_number_without_a_named_lookup_checks_the_balance():
    assert Conversation()._settle_lookup("Dạ em nghe ạ.", PHONE, []) == (accounts.DEFAULT_AFTER_DIALING, PHONE)


def test_lock_card_waits_for_a_yes():
    session = Conversation()
    assert session._settle_lookup("@LOOKUP lock_card 0901234567", PHONE, []) is None
    assert session.awaiting_confirmation == ("lock_card", PHONE)


def test_a_made_up_number_for_lock_card_is_never_kept(model):
    model.append("@LOOKUP lock_card 0901234567")
    session, results = talk("khoá thẻ của tôi giúp em")
    assert results[0].reply == conv.ASK_FOR_PHONE_NUMBER
    assert session.awaiting_confirmation is None
    assert session.pending_lookup == "lock_card"


def test_a_made_up_topic_falls_back_to_the_keywords_or_out_of_scope():
    session = Conversation()
    assert session._settle_document("giá vàng thế nào", "@DOC gold_price_today", []) in knowledge.answers("gold_price")
    assert session._settle_document("kể chuyện đi", "@DOC made_up_topic", []) == conv.OUT_OF_SCOPE


def test_keywords_beat_a_wrong_topic_choice():
    reply = Conversation()._settle_document("ngân hàng của bạn là ngân hàng gì", "@DOC savings_rate", [])
    assert reply in knowledge.answers("about_us")


def test_the_dialed_number_is_passed_to_the_model():
    assert PHONE in Conversation._caller_sentence("đây", PHONE)
    assert Conversation._caller_sentence("", PHONE).startswith(PHRASES["for_the_model"]["no_words"])


def test_a_repeated_fixed_sentence_is_said_another_way():
    for group in conv.SAME_MEANING_SENTENCES:
        for sentence in group:
            other = conv.say_differently(sentence, sentence)
            assert other in group and other != sentence


def test_any_other_repeated_sentence_gets_a_reminder_opening():
    sentence = "Dạ số dư tài khoản của anh chị là 5 triệu đồng."
    assert conv.say_differently(sentence, sentence) == "Dạ như em vừa nói, số dư tài khoản của anh chị là 5 triệu đồng."
    assert conv.say_differently("Dạ vâng ạ.", "Dạ em xin nghe.") == "Dạ vâng ạ."


def test_silence_three_times_never_repeats_the_same_words():
    _, results = talk("", "", "")
    assert results[0].reply != results[1].reply != results[2].reply


def test_every_way_of_asking_for_the_number_says_dial():
    assert all("bấm" in sentence.lower() for sentence in conv.ASKING_FOR_NUMBER)


def test_a_single_word_of_noise_is_asked_again_without_the_model():
    _, results = talk("ồm", "bảy")
    assert results[0].reply == conv.DID_NOT_CATCH
    assert results[1].reply in conv.PHRASES["did_not_catch"]


def test_objection_with_a_new_topic_apologises_and_reads_it():
    _, results = talk("lãi suất vay bao nhiêu", "không phải, tôi hỏi giá vàng")
    assert results[1].reply.startswith(PHRASES["openings"]["apology"])
    assert "vàng" in results[1].reply


def test_an_objection_never_reads_the_rejected_topic_again():
    _, results = talk("giá vàng hôm nay", "sai rồi, không phải giá vàng")
    assert "vàng" not in results[1].reply


def test_a_plain_objection_asks_again():
    _, results = talk("giá vàng", "không phải")
    assert results[1].reply == conv.ASK_AGAIN_AFTER_MISTAKE


def test_two_objections_in_a_row_go_to_staff():
    _, results = talk("giá vàng", "không phải", "sai rồi")
    assert results[2].transfer


def test_the_objection_count_resets_after_a_normal_question():
    _, results = talk("giá vàng", "không phải", "đô la bao nhiêu", "sai rồi")
    assert not results[3].transfer


def test_no_to_a_confirmation_is_a_refusal_not_an_objection():
    session, results = talk(("", "", "4"), ("", UNLOCKED_PHONE), "không phải")
    assert results[2].reply == PHRASES["cancelled"]
    assert session.objections_in_a_row == 0


def test_dialing_while_a_confirmation_is_open_cancels_it():
    _, results = talk(("", "", "4"), ("", UNLOCKED_PHONE), ("", PHONE))
    assert results[2].reply == PHRASES["cancelled"]
    assert not accounts.customers[UNLOCKED_PHONE]["card_locked"]


def test_a_caller_who_will_not_dial_gets_an_explanation(model):
    model.append("@LOOKUP check_balance")
    _, results = talk("số dư tài khoản của tôi bao nhiêu", "tôi không có điện thoại ở đây")
    assert results[0].reply == conv.ASK_FOR_PHONE_NUMBER
    assert results[1].reply == PHRASES["why_we_need_the_number"]


def test_yes_after_the_explanation_goes_to_staff(model):
    model.append("@LOOKUP check_balance")
    _, results = talk("số dư tài khoản của tôi bao nhiêu", "sao phải bấm", "ừ chuyển đi")
    assert results[2].transfer


def test_no_after_the_explanation_keeps_talking(model):
    model.extend(["@LOOKUP check_balance", "Dạ vâng, anh chị cần gì thêm ạ?"])
    _, results = talk("số dư tài khoản của tôi bao nhiêu", "sao phải bấm", "thôi khỏi")
    assert not results[2].transfer
    assert results[2].reply == "Dạ vâng, anh chị cần gì thêm ạ?"


def test_an_annoyed_caller_is_offered_staff():
    _, results = talk("giá vàng", "phiền quá đi", "được")
    assert results[1].reply == PHRASES["offer_staff"]
    assert results[2].transfer


def test_asking_for_a_person_transfers_right_away():
    assert talk("tôi muốn nói chuyện với người thật")[1][0].transfer


def test_asking_if_it_is_a_machine_gets_an_honest_answer():
    result = talk("em là người thật hay máy")[1][0]
    assert not result.transfer
    assert result.reply in knowledge.answers("automated_assistant")


def test_reluctance_words_mean_nothing_unless_the_number_was_asked_for(model):
    model.append("@DOC transfer_time")
    result = talk("tại sao chuyển tiền lâu vậy")[1][0]
    assert result.reply in knowledge.answers("transfer_time")


def test_goodbye_ends_the_call():
    result = talk("giá vàng", "vậy thôi, tạm biệt em")[1][1]
    assert result.reply == PHRASES["goodbye"] and result.hang_up


def test_thanks_asks_if_there_is_more_and_no_ends_the_call():
    _, results = talk("giá vàng", "cảm ơn em", "không")
    assert results[1].reply == PHRASES["anything_else"] and not results[1].hang_up
    assert results[2].hang_up


def test_thanks_with_a_new_question_keeps_going():
    result = talk("giá vàng", "cảm ơn, còn đô la thì sao")[1][1]
    assert not result.hang_up and result.reply in knowledge.answers("usd_rate")


def test_no_followed_by_a_question_is_not_goodbye():
    result = talk("giá vàng", "cảm ơn", "không, cho hỏi phí thường niên")[1][2]
    assert not result.hang_up and result.reply in knowledge.answers("annual_fee")


def test_a_menu_key_asks_for_the_number_then_runs_that_lookup():
    session = Conversation()
    assert session.respond("", "", "3").reply == conv.ASK_FOR_PHONE_NUMBER
    assert session.expects_number()
    reply = session.respond("", PHONE).reply
    assert "hạn mức" in reply and "20 triệu" in reply
    assert not session.expects_number()


def test_lock_card_from_the_menu_asks_to_confirm_then_locks():
    _, results = talk(("", "", "4"), ("", UNLOCKED_PHONE), "đúng rồi")
    assert results[1].reply == conv.CONFIRMATION_QUESTIONS["lock_card"]
    assert results[2].reply == accounts.SAY["card_locked"]


def test_refusing_the_confirmation_cancels_and_no_ends_the_call():
    _, results = talk(("", "", "4"), ("", UNLOCKED_PHONE), "thôi không khoá nữa", "không")
    assert results[2].reply == PHRASES["cancelled"]
    assert results[3].hang_up


def test_key_zero_transfers_and_an_unknown_key_reads_the_menu():
    session = Conversation()
    assert session.respond("", "", "0").transfer
    assert session.respond("", "", "9").reply == PHRASES["menu"]


def test_a_clear_topic_question_skips_the_model():
    session, results = talk("lãi suất tiết kiệm bao nhiêu")
    assert results[0].reply in knowledge.answers("savings_rate")
    assert session.history[-1]["content"] == "@DOC savings_rate"


def test_a_question_about_the_callers_own_account_asks_the_model(model):
    model.append("@LOOKUP daily_limit")
    assert talk("hạn mức thẻ của tôi bao nhiêu")[1][0].reply == conv.ASK_FOR_PHONE_NUMBER


def test_a_lookup_named_before_the_number_runs_without_the_model_again(model):
    model.append("@LOOKUP daily_limit")
    session, _ = talk("hạn mức thẻ của tôi bao nhiêu")
    reply = session.respond("", PHONE).reply
    assert "hạn mức" in reply and "20 triệu" in reply


def test_lock_card_named_by_voice_still_asks_to_confirm(model):
    model.append("@LOOKUP lock_card")
    session, _ = talk("tôi muốn khoá thẻ của tôi")
    assert session.respond("", PHONE).reply == conv.CONFIRMATION_QUESTIONS["lock_card"]


def test_a_pending_lookup_is_forgotten_when_the_caller_moves_on(model):
    model.append("@LOOKUP check_balance")
    session, _ = talk("số dư của tôi bao nhiêu", "giá vàng hôm nay")
    assert session.pending_lookup is None and not session.expects_number()


def test_minimum_balance_is_general_information():
    assert talk("số dư tối thiểu là bao nhiêu")[1][0].reply in knowledge.answers("minimum_balance")
