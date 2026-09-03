import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import bank_data


def test_spell_amount_millions_and_thousands():
    assert bank_data.spell_amount(12_450_000) == "12 triệu 450 nghìn đồng"


def test_spell_amount_millions_only():
    assert bank_data.spell_amount(5_000_000) == "5 triệu đồng"


def test_spell_amount_thousands_only():
    assert bank_data.spell_amount(850_000) == "850 nghìn đồng"


def test_read_balance_existing_customer():
    assert "12 triệu 450 nghìn" in bank_data.read_balance("0901234567")


def test_read_balance_ignores_separators():
    assert bank_data.read_balance("090-123-4567") == bank_data.read_balance("0901234567")


def test_read_balance_unknown_customer():
    assert bank_data.read_balance("0000000000") == bank_data.CUSTOMER_NOT_FOUND


def test_last_transaction_is_the_most_recent():
    sentence = bank_data.read_last_transaction("0901234567")
    assert "02/09" in sentence and "500 nghìn" in sentence


def test_lock_card_succeeds_first_time():
    bank_data.CUSTOMERS["0987654321"]["trang_thai_the"] = "đang hoạt động"
    assert "thành công" in bank_data.lock_card("0987654321")


def test_lock_card_reports_already_locked():
    bank_data.CUSTOMERS["0987654321"]["trang_thai_the"] = "đang hoạt động"
    bank_data.lock_card("0987654321")
    assert "từ trước" in bank_data.lock_card("0987654321")


def test_lock_card_really_changes_state():
    bank_data.CUSTOMERS["0987654321"]["trang_thai_the"] = "đang hoạt động"
    bank_data.lock_card("0987654321")
    assert bank_data.CUSTOMERS["0987654321"]["trang_thai_the"] == "đã khoá"


def test_only_data_changing_actions_need_confirmation():
    assert bank_data.needs_confirmation("khoa_the")
    assert not bank_data.needs_confirmation("tra_so_du")


def test_caller_consents():
    assert bank_data.caller_consented("đúng rồi")
    assert bank_data.caller_consented("vâng khoá đi")


def test_caller_refuses():
    assert not bank_data.caller_consented("thôi không cần")
    assert not bank_data.caller_consented("chưa")


def test_refusal_beats_consent_when_both_appear():
    assert not bank_data.caller_consented("không, thôi đừng khoá")


def test_unrelated_sentence_is_not_consent():
    assert not bank_data.caller_consented("cho tôi biết số dư")


def test_every_action_is_callable():
    for name, action in bank_data.ACTIONS.items():
        assert action("0901234567"), name