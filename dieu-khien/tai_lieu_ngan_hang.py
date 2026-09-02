import json
import os

THU_MUC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tai-lieu")
FILE_TAI_LIEU = os.path.join(THU_MUC, "tai_lieu.json")
FILE_SO_LIEU = os.path.join(THU_MUC, "so_lieu.json")

_bo_nho = {"tai_lieu": {}, "so_lieu": {}, "moc_thoi_gian": {}}


def _doc_neu_doi(duong_dan, khoa):
    if not os.path.exists(duong_dan):
        return _bo_nho[khoa]
    moc = os.path.getmtime(duong_dan)
    if _bo_nho["moc_thoi_gian"].get(khoa) == moc:
        return _bo_nho[khoa]
    with open(duong_dan, encoding="utf-8") as f:
        _bo_nho[khoa] = json.load(f)
    _bo_nho["moc_thoi_gian"][khoa] = moc
    print(f"  (doc lai {os.path.basename(duong_dan)}: {len(_bo_nho[khoa])} muc)")
    return _bo_nho[khoa]


def cac_chu_de():
    return list(_doc_neu_doi(FILE_TAI_LIEU, "tai_lieu").keys())


TU_KHOA = {
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


def tim_chu_de_theo_tu_khoa(cau_nguoi_goi):
    cau = cau_nguoi_goi.lower()
    co_san = cac_chu_de()
    trung_khop = [
        (len(tu), chu_de)
        for chu_de, cac_tu in TU_KHOA.items()
        for tu in cac_tu
        if tu in cau and chu_de in co_san
    ]
    if not trung_khop:
        return None
    return max(trung_khop)[1]


def tra_tai_lieu(chu_de):
    tai_lieu = _doc_neu_doi(FILE_TAI_LIEU, "tai_lieu")
    if chu_de not in tai_lieu:
        return None
    so_lieu = _doc_neu_doi(FILE_SO_LIEU, "so_lieu")
    cau = tai_lieu[chu_de]
    for ten, gia_tri in so_lieu.items():
        cau = cau.replace("{" + ten + "}", str(gia_tri))
    return cau
