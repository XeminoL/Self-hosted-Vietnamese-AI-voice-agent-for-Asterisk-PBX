import caller_words as words


def test_old_and_new_tone_placement_match():
    assert words.says_any("khóa thẻ giúp tôi", ["khoá thẻ"])
    assert words.says_any("hủy đi", ["huỷ"])


def test_short_words_only_match_whole_words():
    assert words.says_any("ừ chuyển đi", ["ừ"])
    assert not words.says_any("vừa chừng thôi", ["ừ"])


def test_phrases_are_removed_as_whole_words():
    assert words.without_phrases("số dư tối thiểu là bao nhiêu", ["số dư tối thiểu"]) == "là bao nhiêu"


def test_objections():
    for sentence in ("không phải", "Không đúng rồi em", "sai rồi", "ơ nhầm rồi",
                     "tôi không hỏi cái đó", "không phải, tôi hỏi giá vàng"):
        assert words.is_objection(sentence), sentence


def test_questions_are_not_objections():
    for sentence in ("không biết lãi suất bao nhiêu", "phí thường niên là sao",
                     "giá vàng hôm nay", "không có thẻ thì sao"):
        assert not words.is_objection(sentence), sentence


def test_consent():
    assert words.consented("đúng rồi")
    assert words.consented("vâng khoá đi")
    assert not words.consented("thôi không cần")
    assert not words.consented("không, thôi đừng khoá")
    assert not words.consented("cho tôi biết số dư")


def test_asking_for_a_person_but_not_asking_if_it_is_a_machine():
    assert words.asks_for_staff("tôi muốn nói chuyện với người thật")
    assert not words.asks_for_staff("em là người thật hay máy")


def test_accepting_an_offer_of_staff():
    assert words.accepts_staff("ừ chuyển đi")
    assert not words.accepts_staff("thôi khỏi")
