import json
import os
import urllib.request

from du_lieu_ngan_hang import (CAC_VIEC, CAU_HOI_XAC_NHAN, can_xac_nhan,
                               nguoi_goi_da_dong_y)
from sua_chu_nghe import sua_tu_gan_am
from tai_lieu_ngan_hang import (cac_chu_de, tim_chu_de_theo_tu_khoa,
                                tra_tai_lieu)

DIA_CHI_LLM = "http://127.0.0.1:8080/v1/chat/completions"
GIOI_HAN_TOKEN = 20
SO_LUOT_NHO = 4

MOC_GOI_VIEC = "@TRA"
MOC_CHUYEN_MAY = "@CHUYEN"
MOC_TRA_TAI_LIEU = "@DOC"

XIN_SO_DIEN_THOAI = "Anh chị bấm số điện thoại rồi bấm dấu thăng ạ."
KHONG_NAM_DUOC = "Dạ chỗ này em không nắm được, em xin phép chuyển anh chị cho nhân viên nhé."
CHUA_NGHE_RO = "Dạ em chưa nghe rõ ạ."
KHONG_KHOA_THE = "Dạ vậy em không khoá thẻ."
VIEC_MAC_DINH_KHI_BAM_SO = "tra_so_du"

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "loi_dan.txt"), encoding="utf-8") as f:
    LOI_DAN = f.read().strip()


def hoi_llm(lich_su):
    du_lieu = json.dumps({
        "messages": [{"role": "system", "content": LOI_DAN}] + lich_su[-SO_LUOT_NHO:],
        "max_tokens": GIOI_HAN_TOKEN,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    yeu_cau = urllib.request.Request(
        DIA_CHI_LLM, data=du_lieu, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(yeu_cau) as phan_hoi:
        ket_qua = json.loads(phan_hoi.read())
    return ket_qua["choices"][0]["message"]["content"].strip(), ket_qua.get("timings", {})


def mo_ta_thoi_gian(timings):
    if not timings:
        return ""
    return (f"nap {timings.get('prompt_n', 0)}tk/{timings.get('prompt_ms', 0) / 1000:.1f}s"
            f" | sinh {timings.get('predicted_n', 0)}tk/"
            f"{timings.get('predicted_ms', 0) / 1000:.1f}s"
            f" | cache {timings.get('cache_n', 0)}")


def tach_chu_de_tai_lieu(cau):
    chu_de = _lay_tham_so_sau_moc(cau, MOC_TRA_TAI_LIEU, 1)
    if not chu_de:
        return None
    return chu_de[0] if chu_de[0] in cac_chu_de() else None


def tach_lenh_goi_viec(cau):
    phan = _lay_tham_so_sau_moc(cau, MOC_GOI_VIEC, 2)
    if not phan or phan[0] not in CAC_VIEC:
        return None
    so_dien_thoai = "".join(k for k in phan[1] if k.isdigit())
    return phan[0], so_dien_thoai


def bo_phan_lenh(cau):
    for moc in (MOC_GOI_VIEC, MOC_TRA_TAI_LIEU, MOC_CHUYEN_MAY):
        if moc in cau:
            cau = cau.split(moc, 1)[0]
    return cau.strip()


def _lay_tham_so_sau_moc(cau, moc, so_tham_so):
    if moc not in cau:
        return None
    phan = cau.split(moc, 1)[1].strip().split()
    if len(phan) < so_tham_so:
        return None
    return [p.strip("[](){}:,.") for p in phan[:so_tham_so]]


def co_chu_so(cau):
    return any(ky_tu.isdigit() for ky_tu in cau)


class KetQuaLuot:
    def __init__(self, cau_noi="", nhat_ky=(), chuyen_may=False, cup_may=False):
        self.cau_noi = cau_noi
        self.nhat_ky = list(nhat_ky)
        self.chuyen_may = chuyen_may
        self.cup_may = cup_may


class BoHoiThoai:
    def __init__(self):
        self.lich_su = []
        self.viec_cho_xac_nhan = None

    def tra_loi(self, cau_nghe_duoc, so_da_bam):
        if not cau_nghe_duoc and not so_da_bam:
            return KetQuaLuot(cau_noi=CHUA_NGHE_RO)

        cau_nguoi_goi = self._dung_cau_nguoi_goi(cau_nghe_duoc, so_da_bam)
        self.lich_su.append({"role": "user", "content": cau_nguoi_goi})

        cau_llm, timings = hoi_llm(self.lich_su)
        nhat_ky = [f"HIEU: {cau_llm}"]
        mo_ta = mo_ta_thoi_gian(timings)
        if mo_ta:
            nhat_ky.insert(0, mo_ta)

        ket_qua = self._quyet_dinh(cau_nguoi_goi, cau_llm, so_da_bam, nhat_ky)
        self.lich_su.append({"role": "assistant", "content": ket_qua.cau_noi})
        return ket_qua

    @staticmethod
    def _dung_cau_nguoi_goi(cau_nghe_duoc, so_da_bam):
        cau = sua_tu_gan_am(cau_nghe_duoc) if cau_nghe_duoc else "đây"
        if so_da_bam:
            cau += f" (số điện thoại đã bấm: {so_da_bam})"
        return cau

    def _quyet_dinh(self, cau_nguoi_goi, cau_llm, so_da_bam, nhat_ky):
        if MOC_CHUYEN_MAY in cau_llm:
            return KetQuaLuot(nhat_ky=nhat_ky, chuyen_may=True)

        chu_de = tach_chu_de_tai_lieu(cau_llm)
        if chu_de:
            nhat_ky.append(f"DOC tai lieu: {chu_de}")
            return KetQuaLuot(tra_tai_lieu(chu_de), nhat_ky)

        lenh = self._chot_lenh(cau_nguoi_goi, cau_llm, so_da_bam, nhat_ky)
        if lenh:
            ten_viec, so_dien_thoai = lenh
            nhat_ky.append(f"TRA {ten_viec}({so_dien_thoai})")
            return KetQuaLuot(CAC_VIEC[ten_viec](so_dien_thoai), nhat_ky)

        return KetQuaLuot(self._loc_cau_llm(cau_nguoi_goi, cau_llm, nhat_ky), nhat_ky)

    def _chot_lenh(self, cau_nguoi_goi, cau_llm, so_da_bam, nhat_ky):
        lenh = tach_lenh_goi_viec(cau_llm)

        if self.viec_cho_xac_nhan:
            cho_xac_nhan, self.viec_cho_xac_nhan = self.viec_cho_xac_nhan, None
            if nguoi_goi_da_dong_y(cau_nguoi_goi):
                nhat_ky.append(f"nguoi goi DONG Y -> chay {cho_xac_nhan[0]}")
                return cho_xac_nhan
            nhat_ky.append("nguoi goi KHONG dong y")
            return None

        if lenh and can_xac_nhan(lenh[0]):
            self.viec_cho_xac_nhan = (lenh[0], so_da_bam or lenh[1])
            nhat_ky.append(f"HOI XAC NHAN truoc khi {lenh[0]}")
            return None

        if so_da_bam and not lenh:
            nhat_ky.append("co so da bam, LLM khong sinh @TRA")
            return VIEC_MAC_DINH_KHI_BAM_SO, so_da_bam

        if lenh and so_da_bam and lenh[1] != so_da_bam:
            nhat_ky.append(f"LLM viet sai so, dung so da bam {so_da_bam}")
            return lenh[0], so_da_bam

        if lenh and not so_da_bam:
            nhat_ky.append("LLM bia so, nguoi goi chua bam")
            return None

        return lenh

    def _loc_cau_llm(self, cau_nguoi_goi, cau_llm, nhat_ky):
        cau = bo_phan_lenh(cau_llm)

        if self.viec_cho_xac_nhan:
            return CAU_HOI_XAC_NHAN[self.viec_cho_xac_nhan[0]]
        if not cau:
            return XIN_SO_DIEN_THOAI if MOC_GOI_VIEC in cau_llm else CHUA_NGHE_RO
        if not co_chu_so(cau):
            return cau

        chu_de = tim_chu_de_theo_tu_khoa(cau_nguoi_goi)
        if chu_de:
            nhat_ky.append(f"BIA SO LIEU -> tu khoa: {chu_de}")
            return tra_tai_lieu(chu_de)
        nhat_ky.append(f"BIA SO LIEU, bo: {cau}")
        return KHONG_NAM_DUOC
