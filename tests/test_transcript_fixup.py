from transcript_fixup import fix_near_homophones


def test_fixes_a_close_mishearing_of_a_short_term():
    assert "số dư" in fix_near_homophones("cho tôi biết số dừa tài khoản")


def test_fixes_a_mishearing_two_letters_off_on_a_long_term():
    assert "tài khoản" in fix_near_homophones("số dư tài phản của tôi")


def test_leaves_correct_and_unrelated_sentences_alone():
    for sentence in ("hôm nay trời mưa quá", "tôi muốn biết số dư tài khoản",
                     "tôi muốn biết đường tình duyên của tôi"):
        assert fix_near_homophones(sentence) == sentence


def test_short_terms_need_a_closer_match():
    sentence = "ngân hàng mua usd giá bao nhiêu"
    assert fix_near_homophones(sentence) == sentence


def test_real_phrases_that_look_misheard_stay():
    assert fix_near_homophones("tôi không có điện thoại") == "tôi không có điện thoại"
