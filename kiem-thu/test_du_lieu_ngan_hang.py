import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dieu-khien"))

import du_lieu_ngan_hang as dl


def test_doc_tien_ca_trieu_va_nghin():
    assert dl.doc_tien(12_450_000) == "12 triệu 450 nghìn đồng"


def test_doc_tien_chi_trieu():
    assert dl.doc_tien(5_000_000) == "5 triệu đồng"


def test_doc_tien_chi_nghin():
    assert dl.doc_tien(850_000) == "850 nghìn đồng"


def test_tra_so_du_khach_co_that():
    assert "12 triệu 450 nghìn" in dl.tra_so_du("0901234567")


def test_tra_so_du_bo_qua_ky_tu_la():
    assert dl.tra_so_du("090-123-4567") == dl.tra_so_du("0901234567")


def test_tra_so_du_khach_khong_ton_tai():
    assert dl.tra_so_du("0000000000") == dl.KHONG_TIM_THAY


def test_tra_giao_dich_lay_cai_gan_nhat():
    cau = dl.tra_giao_dich("0901234567")
    assert "02/09" in cau and "500 nghìn" in cau


def test_khoa_the_lan_dau_thanh_cong():
    dl.KHACH_HANG["0987654321"]["trang_thai_the"] = "đang hoạt động"
    assert "thành công" in dl.khoa_the("0987654321")


def test_khoa_the_lan_hai_bao_da_khoa():
    dl.KHACH_HANG["0987654321"]["trang_thai_the"] = "đang hoạt động"
    dl.khoa_the("0987654321")
    assert "từ trước" in dl.khoa_the("0987654321")


def test_khoa_the_doi_trang_thai_that():
    dl.KHACH_HANG["0987654321"]["trang_thai_the"] = "đang hoạt động"
    dl.khoa_the("0987654321")
    assert dl.KHACH_HANG["0987654321"]["trang_thai_the"] == "đã khoá"


def test_can_xac_nhan_chi_voi_viec_doi_du_lieu():
    assert dl.can_xac_nhan("khoa_the")
    assert not dl.can_xac_nhan("tra_so_du")


def test_nguoi_goi_dong_y():
    assert dl.nguoi_goi_da_dong_y("đúng rồi")
    assert dl.nguoi_goi_da_dong_y("vâng khoá đi")


def test_nguoi_goi_tu_choi():
    assert not dl.nguoi_goi_da_dong_y("thôi không cần")
    assert not dl.nguoi_goi_da_dong_y("chưa")


def test_tu_choi_thang_dong_y_khi_lan_lon():
    assert not dl.nguoi_goi_da_dong_y("không, thôi đừng khoá")


def test_cau_noi_gi_cung_khong_tinh_la_dong_y():
    assert not dl.nguoi_goi_da_dong_y("cho tôi biết số dư")


def test_moi_viec_deu_goi_duoc():
    for ten, ham in dl.CAC_VIEC.items():
        assert ham("0901234567"), ten
