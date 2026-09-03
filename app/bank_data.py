import functools

CUSTOMER_NOT_FOUND = "Dạ em không tìm thấy số điện thoại này trong hệ thống ạ."
ACTIONS_THAT_CHANGE_DATA = {"khoa_the"}
CONFIRMATION_QUESTIONS = {"khoa_the": "Anh chị xác nhận khoá thẻ ạ?"}

CONSENT_WORDS = ("đúng rồi", "dung roi", "đúng vậy", "dung vay", "phải rồi",
                 "phai roi", "vâng", "vang", "đồng ý", "dong y", "xác nhận",
                 "xac nhan", "ok", "okay", "khoá đi", "khoa di", "khoá luôn",
                 "khoa luon", "làm đi", "lam di")
REFUSAL_WORDS = ("không", "khong", "thôi", "thoi", "chưa", "chua", "đừng",
                 "dung lai", "hủy", "huy", "bỏ", "bo qua")

CUSTOMERS = {
    "0901234567": {
        "ten": "Nguyễn Văn An",
        "so_tai_khoan": "1903 8888 0001",
        "so_du": 12_450_000,
        "trang_thai_the": "đang hoạt động",
        "han_muc_ngay": 20_000_000,
        "giao_dich": [
            ("02/09", "chuyển đi", 500_000, "Nguyễn Thị Bình"),
            ("01/09", "nhận về", 8_000_000, "Công ty TNHH Minh Long"),
            ("31/08", "rút ATM", 2_000_000, "ATM Lê Văn Sỹ"),
        ],
    },
    "0987654321": {
        "ten": "Trần Thị Mai",
        "so_tai_khoan": "1903 8888 0002",
        "so_du": 850_000,
        "trang_thai_the": "đang hoạt động",
        "han_muc_ngay": 5_000_000,
        "giao_dich": [
            ("02/09", "thanh toán", 120_000, "Cửa hàng Circle K"),
            ("30/08", "nhận về", 1_000_000, "Trần Văn Hùng"),
        ],
    },
    "0912345678": {
        "ten": "Lê Hoàng Nam",
        "so_tai_khoan": "1903 8888 0003",
        "so_du": 47_300_000,
        "trang_thai_the": "đã khoá",
        "han_muc_ngay": 50_000_000,
        "giao_dich": [("28/08", "chuyển đi", 15_000_000, "Phạm Quốc Bảo")],
    },
}


def spell_amount(amount):
    millions = amount // 1_000_000
    thousands = (amount % 1_000_000) // 1_000
    if millions and thousands:
        return f"{millions} triệu {thousands} nghìn đồng"
    return f"{millions} triệu đồng" if millions else f"{thousands} nghìn đồng"


def _needs_customer(action):
    @functools.wraps(action)
    def wrapper(phone_number):
        digits = "".join(c for c in phone_number if c.isdigit())
        customer = CUSTOMERS.get(digits)
        return action(customer) if customer else CUSTOMER_NOT_FOUND

    return wrapper


@_needs_customer
def read_balance(customer):
    return f"Dạ số dư tài khoản của anh chị là {spell_amount(customer['so_du'])}."


@_needs_customer
def read_last_transaction(customer):
    if not customer["giao_dich"]:
        return "Dạ tài khoản của anh chị chưa có giao dịch nào ạ."
    date, kind, amount, counterparty = customer["giao_dich"][0]
    return (f"Dạ giao dịch gần nhất của anh chị là ngày {date}, "
            f"{kind} {spell_amount(amount)}, bên kia là {counterparty}.")


@_needs_customer
def read_daily_limit(customer):
    return f"Dạ hạn mức mỗi ngày của anh chị là {spell_amount(customer['han_muc_ngay'])}."


@_needs_customer
def lock_card(customer):
    if customer["trang_thai_the"] == "đã khoá":
        return "Dạ thẻ của anh chị đã khoá từ trước rồi ạ."
    customer["trang_thai_the"] = "đã khoá"
    return "Dạ em đã khoá thẻ của anh chị thành công."


ACTIONS = {
    "tra_so_du": read_balance,
    "tra_giao_dich": read_last_transaction,
    "tra_han_muc": read_daily_limit,
    "khoa_the": lock_card,
}


def needs_confirmation(action_name):
    return action_name in ACTIONS_THAT_CHANGE_DATA


def caller_consented(caller_sentence):
    sentence = caller_sentence.lower()
    if any(word in sentence for word in REFUSAL_WORDS):
        return False
    return any(word in sentence for word in CONSENT_WORDS)