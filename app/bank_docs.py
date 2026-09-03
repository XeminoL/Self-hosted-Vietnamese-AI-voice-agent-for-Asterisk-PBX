import json
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
TOPICS_FILE = os.path.join(DOCS_DIR, "topics.json")
FIGURES_FILE = os.path.join(DOCS_DIR, "figures.json")

_cache = {"topics": {}, "figures": {}, "mtime": {}}

KEYWORDS = {
    "lai_suat_tiet_kiem": ("tiết kiệm", "gửi tiền", "gởi tiền", "lãi tiết kiệm"),
    "lai_suat_vay": ("lãi vay", "vay lãi", "lãi suất vay"),
    "ty_gia_do": ("đô", "đô la", "usd", "tỷ giá", "ngoại tệ"),
    "gia_vang": ("vàng", "sjc", "lượng vàng"),
    "phi_chuyen_tien": ("phí chuyển", "chuyển tiền mất", "chuyển mất phí"),
    "cach_chuyen_tien": ("cách chuyển", "chuyển tiền thế nào", "chuyển sao"),
    "thoi_gian_chuyen_tien": ("bao lâu", "mấy phút", "chuyển lâu"),
    "gio_lam_viec": ("mấy giờ", "giờ làm", "mở cửa", "đóng cửa"),
    "chi_nhanh_o_dau": ("chi nhánh", "ở đâu", "địa chỉ", "phòng giao dịch"),
    "han_muc_mac_dinh": ("hạn mức",),
    "the_bi_mat": ("mất thẻ", "thẻ mất", "rơi thẻ"),
    "quen_mat_khau": ("quên mật khẩu", "mật khẩu", "đăng nhập"),
    "mo_tai_khoan": ("mở tài khoản", "mở thẻ", "làm thẻ"),
    "phi_thuong_nien": ("thường niên", "phí thẻ", "phí năm"),
    "rut_tien_atm": ("rút tiền", "atm", "cây rút"),
    "vay_can_gi": ("vay cần", "vay tiền", "thủ tục vay", "hồ sơ vay"),
    "so_du_toi_thieu": ("tối thiểu", "duy trì"),
}


def _read_if_changed(path, key):
    if not os.path.exists(path):
        return _cache[key]
    mtime = os.path.getmtime(path)
    if _cache["mtime"].get(key) == mtime:
        return _cache[key]
    with open(path, encoding="utf-8") as f:
        _cache[key] = json.load(f)
    _cache["mtime"][key] = mtime
    print(f"  (doc lai {os.path.basename(path)}: {len(_cache[key])} muc)")
    return _cache[key]


def available_topics():
    return list(_read_if_changed(TOPICS_FILE, "topics").keys())


def find_topic_by_keyword(caller_sentence):
    sentence = caller_sentence.lower()
    available = available_topics()
    matches = [
        (len(word), topic)
        for topic, words in KEYWORDS.items()
        for word in words
        if word in sentence and topic in available
    ]
    if not matches:
        return None
    return max(matches)[1]


def read_topic(topic):
    topics = _read_if_changed(TOPICS_FILE, "topics")
    if topic not in topics:
        return None
    figures = _read_if_changed(FIGURES_FILE, "figures")
    sentence = topics[topic]
    for name, value in figures.items():
        sentence = sentence.replace("{" + name + "}", str(value))
    return sentence