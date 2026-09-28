import accounts
import knowledge
import model_reply as reply


def lookup(text):
    return reply.lookup_command(text, accounts.LOOKUPS)


def test_lookup_command():
    assert lookup("@LOOKUP check_balance 0901234567") == ("check_balance", "0901234567")
    assert lookup("@LOOKUP check_balance: 0901234567.") == ("check_balance", "0901234567")


def test_lookup_command_needs_a_known_name_and_a_number():
    assert lookup("@LOOKUP no_such_thing 0901234567") is None
    assert lookup("@LOOKUP check_balance") is None
    assert lookup("Dạ em xin nghe.") is None


def test_lookup_name_forgives_diacritics_and_extra_words():
    assert lookup("@LOOKUP lóck_card 0901234567") == ("lock_card", "0901234567")
    assert lookup("@LOOKUP daily_limit_default 0901234") == ("daily_limit", "0901234")


def test_document_topic():
    topics = knowledge.topic_names()
    assert reply.document_topic("@DOC savings_rate", topics) == "savings_rate"
    assert reply.document_topic("@DOC no_such_topic", topics) is None


def test_without_tags():
    assert reply.without_tags("Dạ vâng @LOOKUP check_balance 0901234567") == "Dạ vâng"
    assert reply.without_tags("Dạ em xin nghe.") == "Dạ em xin nghe."


def test_contains_digit():
    assert reply.contains_digit("giá vàng 131 triệu")
    assert not reply.contains_digit("Dạ em không nắm được ạ")
