import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dieu-khien"))

from sua_chu_nghe import sua_tu_gan_am


def test_sua_so_dua_thanh_so_du():
    assert "số dư" in sua_tu_gan_am("cho tôi biết số dừa tài khoản")


def test_sua_tai_phan_thanh_tai_khoan():
    assert "tài khoản" in sua_tu_gan_am("số dư tài phản của tôi")


def test_khong_pha_cau_binh_thuong():
    cau = "hôm nay trời mưa quá"
    assert sua_tu_gan_am(cau) == cau


def test_khong_sua_cau_da_dung():
    cau = "tôi muốn biết số dư tài khoản"
    assert sua_tu_gan_am(cau) == cau


def test_giu_nguyen_cau_ngoai_pham_vi():
    cau = "tôi muốn biết đường tình duyên của tôi"
    assert sua_tu_gan_am(cau) == cau
