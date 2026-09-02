import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dieu-khien"))

import hoi_thoai as ht


def test_tach_lenh_dung_khuon():
    assert ht.tach_lenh_goi_viec("@TRA tra_so_du 0901234567") == ("tra_so_du", "0901234567")


def test_tach_lenh_bo_dau_cau():
    assert ht.tach_lenh_goi_viec("@TRA tra_so_du: 0901234567.") == ("tra_so_du", "0901234567")


def test_tach_lenh_ten_viec_sai():
    assert ht.tach_lenh_goi_viec("@TRA khong_co_viec_nay 0901234567") is None


def test_tach_lenh_thieu_tham_so():
    assert ht.tach_lenh_goi_viec("@TRA tra_so_du") is None


def test_cau_thuong_khong_co_lenh():
    assert ht.tach_lenh_goi_viec("Dạ em xin nghe.") is None


def test_tach_chu_de_tai_lieu():
    assert ht.tach_chu_de_tai_lieu("@DOC lai_suat_tiet_kiem") == "lai_suat_tiet_kiem"


def test_tach_chu_de_khong_ton_tai():
    assert ht.tach_chu_de_tai_lieu("@DOC chu_de_bia_dat") is None


def test_bo_phan_lenh_khoi_cau():
    assert ht.bo_phan_lenh("Dạ em tra ngay. @TRA tra_so_du 090") == "Dạ em tra ngay."


def test_bo_phan_lenh_giu_cau_sach():
    assert ht.bo_phan_lenh("Dạ em xin nghe.") == "Dạ em xin nghe."


def test_co_chu_so():
    assert ht.co_chu_so("giá vàng 131 triệu")
    assert not ht.co_chu_so("Dạ em không nắm được ạ")


def test_dung_cau_nguoi_goi_them_so_da_bam():
    cau = ht.BoHoiThoai._dung_cau_nguoi_goi("đây", "0901234567")
    assert "0901234567" in cau


def test_dung_cau_nguoi_goi_khi_khong_ra_chu():
    assert ht.BoHoiThoai._dung_cau_nguoi_goi("", "0901234567").startswith("đây")


def test_chot_lenh_bo_khi_llm_bia_so():
    bo = ht.BoHoiThoai()
    lenh = bo._chot_lenh("tôi muốn xem số dư", "@TRA tra_so_du 0901234567", "", [])
    assert lenh is None


def test_chot_lenh_dung_so_da_bam_khi_llm_viet_sai():
    bo = ht.BoHoiThoai()
    lenh = bo._chot_lenh("đây", "@TRA tra_so_du 0999999999", "0901234567", [])
    assert lenh == ("tra_so_du", "0901234567")


def test_chot_lenh_tu_tra_so_du_khi_bam_so_ma_llm_im():
    bo = ht.BoHoiThoai()
    lenh = bo._chot_lenh("đây", "Dạ em nghe ạ.", "0901234567", [])
    assert lenh == ("tra_so_du", "0901234567")


def test_khoa_the_phai_qua_xac_nhan():
    bo = ht.BoHoiThoai()
    lenh = bo._chot_lenh("khoá thẻ", "@TRA khoa_the 0901234567", "0901234567", [])
    assert lenh is None
    assert bo.viec_cho_xac_nhan == ("khoa_the", "0901234567")


def test_dong_y_thi_chay_viec_da_cho():
    bo = ht.BoHoiThoai()
    bo.viec_cho_xac_nhan = ("khoa_the", "0901234567")
    assert bo._chot_lenh("đúng rồi", "Dạ.", "", []) == ("khoa_the", "0901234567")


def test_khong_dong_y_thi_bo_viec():
    bo = ht.BoHoiThoai()
    bo.viec_cho_xac_nhan = ("khoa_the", "0901234567")
    assert bo._chot_lenh("thôi khỏi", "Dạ.", "", []) is None
    assert bo.viec_cho_xac_nhan is None


def test_loc_cau_bia_so_lieu_thi_tra_tai_lieu():
    bo = ht.BoHoiThoai()
    cau = bo._loc_cau_llm("giá vàng thế nào", "Dạ giá vàng 58 triệu ạ.", [])
    assert "58" not in cau


def test_loc_cau_bia_so_ngoai_pham_vi_thi_khong_biet():
    bo = ht.BoHoiThoai()
    cau = bo._loc_cau_llm("thời tiết hôm nay", "Dạ hôm nay 30 độ C ạ.", [])
    assert cau == ht.KHONG_NAM_DUOC


def test_loc_cau_sach_thi_giu_nguyen():
    bo = ht.BoHoiThoai()
    cau = "Dạ em là Duyên ạ."
    assert bo._loc_cau_llm("em tên gì", cau, []) == cau
