import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dieu-khien"))

import tai_lieu_ngan_hang as tl


def test_co_du_chu_de():
    assert len(tl.cac_chu_de()) >= 15


def test_tra_tai_lieu_thay_so_lieu():
    cau = tl.tra_tai_lieu("lai_suat_tiet_kiem")
    assert "{" not in cau and "}" not in cau


def test_tra_chu_de_khong_ton_tai():
    assert tl.tra_tai_lieu("khong_co_chu_de_nay") is None


def test_doc_lai_khi_so_lieu_doi(tmp_path, monkeypatch):
    thu_muc = tmp_path / "tai-lieu"
    thu_muc.mkdir()
    file_tai_lieu = thu_muc / "tai_lieu.json"
    file_so_lieu = thu_muc / "so_lieu.json"
    file_tai_lieu.write_text(json.dumps({"gia": "Giá là {muc_gia} đồng."}),
                             encoding="utf-8")
    file_so_lieu.write_text(json.dumps({"muc_gia": "một trăm"}), encoding="utf-8")

    monkeypatch.setattr(tl, "FILE_TAI_LIEU", str(file_tai_lieu))
    monkeypatch.setattr(tl, "FILE_SO_LIEU", str(file_so_lieu))
    monkeypatch.setattr(tl, "_bo_nho",
                        {"tai_lieu": {}, "so_lieu": {}, "moc_thoi_gian": {}})

    assert "một trăm" in tl.tra_tai_lieu("gia")

    file_so_lieu.write_text(json.dumps({"muc_gia": "hai trăm"}), encoding="utf-8")
    import os
    os.utime(file_so_lieu, (0, 0))
    assert "hai trăm" in tl.tra_tai_lieu("gia")


def test_tim_chu_de_theo_tu_khoa():
    assert tl.tim_chu_de_theo_tu_khoa("giá vàng thế nào rồi") == "gia_vang"
    assert tl.tim_chu_de_theo_tu_khoa("đô la hôm nay bao nhiêu") == "ty_gia_do"
    assert tl.tim_chu_de_theo_tu_khoa("quên mật khẩu thì làm sao") == "quen_mat_khau"


def test_uu_tien_tu_khoa_dai_hon():
    assert tl.tim_chu_de_theo_tu_khoa("lãi suất tiết kiệm bao nhiêu") == "lai_suat_tiet_kiem"


def test_khong_nhan_sai_cau_ngoai_pham_vi():
    assert tl.tim_chu_de_theo_tu_khoa("thời tiết hôm nay thế nào") is None
    assert tl.tim_chu_de_theo_tu_khoa("kể cho tôi một câu chuyện") is None
