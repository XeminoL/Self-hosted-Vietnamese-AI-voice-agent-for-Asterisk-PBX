import functools

KHONG_TIM_THAY = "Dạ em không tìm thấy số điện thoại này trong hệ thống ạ."
VIEC_DOI_DU_LIEU = {"khoa_the"}
CAU_HOI_XAC_NHAN = {"khoa_the": "Anh chị xác nhận khoá thẻ ạ?"}

TU_DONG_Y = ("đúng rồi", "dung roi", "đúng vậy", "dung vay", "phải rồi",
             "phai roi", "vâng", "vang", "đồng ý", "dong y", "xác nhận",
             "xac nhan", "ok", "okay", "khoá đi", "khoa di", "khoá luôn",
             "khoa luon", "làm đi", "lam di")
TU_TU_CHOI = ("không", "khong", "thôi", "thoi", "chưa", "chua", "đừng",
              "dung lai", "hủy", "huy", "bỏ", "bo qua")

KHACH_HANG = {
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


def doc_tien(so_tien):
    trieu = so_tien // 1_000_000
    nghin = (so_tien % 1_000_000) // 1_000
    if trieu and nghin:
        return f"{trieu} triệu {nghin} nghìn đồng"
    return f"{trieu} triệu đồng" if trieu else f"{nghin} nghìn đồng"


def _can_khach_hang(ham):
    @functools.wraps(ham)
    def bao(so_dien_thoai):
        chi_so = "".join(k for k in so_dien_thoai if k.isdigit())
        khach = KHACH_HANG.get(chi_so)
        return ham(khach) if khach else KHONG_TIM_THAY

    return bao


@_can_khach_hang
def tra_so_du(khach):
    return f"Dạ số dư tài khoản của anh chị là {doc_tien(khach['so_du'])}."


@_can_khach_hang
def tra_giao_dich(khach):
    if not khach["giao_dich"]:
        return "Dạ tài khoản của anh chị chưa có giao dịch nào ạ."
    ngay, loai, so_tien, doi_tac = khach["giao_dich"][0]
    return (f"Dạ giao dịch gần nhất của anh chị là ngày {ngay}, "
            f"{loai} {doc_tien(so_tien)}, bên kia là {doi_tac}.")


@_can_khach_hang
def tra_han_muc(khach):
    return f"Dạ hạn mức mỗi ngày của anh chị là {doc_tien(khach['han_muc_ngay'])}."


@_can_khach_hang
def khoa_the(khach):
    if khach["trang_thai_the"] == "đã khoá":
        return "Dạ thẻ của anh chị đã khoá từ trước rồi ạ."
    khach["trang_thai_the"] = "đã khoá"
    return "Dạ em đã khoá thẻ của anh chị thành công."


CAC_VIEC = {
    "tra_so_du": tra_so_du,
    "tra_giao_dich": tra_giao_dich,
    "tra_han_muc": tra_han_muc,
    "khoa_the": khoa_the,
}


def can_xac_nhan(ten_viec):
    return ten_viec in VIEC_DOI_DU_LIEU


def nguoi_goi_da_dong_y(cau_nguoi_goi):
    cau = cau_nguoi_goi.lower()
    if any(tu in cau for tu in TU_TU_CHOI):
        return False
    return any(tu in cau for tu in TU_DONG_Y)
