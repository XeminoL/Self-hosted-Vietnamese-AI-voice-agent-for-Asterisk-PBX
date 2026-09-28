import accounts

KNOWN_PHONE = "0901234567"
UNLOCKED_PHONE = "0987654321"


def test_spell_amount():
    assert accounts.spell_amount(12_450_000) == "12 triệu 450 nghìn đồng"
    assert accounts.spell_amount(5_000_000) == "5 triệu đồng"
    assert accounts.spell_amount(850_000) == "850 nghìn đồng"


def test_spell_date_as_day_and_month():
    assert accounts.spell_date("02/09") == "2 tháng 9"


def test_balance_of_a_known_customer():
    assert "12 triệu 450 nghìn" in accounts.run_lookup("check_balance", KNOWN_PHONE)


def test_separators_in_the_number_are_ignored():
    assert accounts.run_lookup("check_balance", "090-123-4567") == accounts.run_lookup("check_balance", KNOWN_PHONE)


def test_unknown_customer():
    assert accounts.run_lookup("check_balance", "0000000000") == accounts.SAY["customer_not_found"]


def test_last_transaction_is_the_most_recent():
    reply = accounts.run_lookup("last_transaction", KNOWN_PHONE)
    assert "ngày 2 tháng 9" in reply and "500 nghìn" in reply


def test_lock_card_once_then_already_locked():
    assert accounts.run_lookup("lock_card", UNLOCKED_PHONE) == accounts.SAY["card_locked"]
    assert accounts.customers[UNLOCKED_PHONE]["card_locked"]
    assert accounts.run_lookup("lock_card", UNLOCKED_PHONE) == accounts.SAY["card_already_locked"]


def test_every_test_starts_with_the_card_unlocked():
    assert not accounts.customers[UNLOCKED_PHONE]["card_locked"]


def test_only_lock_card_needs_confirmation():
    assert accounts.needs_confirmation("lock_card")
    assert not accounts.needs_confirmation("check_balance")


def test_every_lookup_answers():
    for lookup in accounts.LOOKUPS:
        assert accounts.run_lookup(lookup, KNOWN_PHONE), lookup
