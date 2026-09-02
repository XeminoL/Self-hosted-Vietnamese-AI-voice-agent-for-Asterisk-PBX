import os
import socketserver
import time

import webrtcvad

from audiosocket import (KetNoiAudioSocket, KetThucKetNoi, LOAI_AUDIO,
                         LOAI_DTMF)
from hoi_thoai import BoHoiThoai, MOC_CHUYEN_MAY
from mo_hinh import BoNghe, BoNoi, TAN_SO, THU_MUC
from thu_vien_giong import ThuVienGiong

DIA_CHI = "127.0.0.1"
CONG = 9092

MS_MOI_KHUNG = 20
BYTE_MOI_KHUNG = TAN_SO * 2 * MS_MOI_KHUNG // 1000
DO_KHAT_KHE_VAD = 3

KHUNG_CO_TIENG_DE_BAT_DAU = 10
KHUNG_IM_DE_DUNG = 40
KHUNG_IM_KHI_CHUA_NOI = 750
KHUNG_TOI_DA_MOT_LUOT = 1500
KHUNG_CHET_SAU_KHI_PHAT = 25

SO_LUOT_TOI_DA = 20
CAU_CHAO = "Dạ em xin nghe."
CAU_CHUYEN_MAY = "Dạ em chuyển anh chị cho nhân viên, anh chị giữ máy giúp em."

bo_nghe = None
bo_noi = None
thu_vien = None


def khoi_dong_mo_hinh():
    global bo_nghe, bo_noi, thu_vien

    print("Dang tai gipformer ...")
    bat_dau = time.time()
    bo_nghe = BoNghe()
    print(f"  xong sau {time.time() - bat_dau:.0f}s")

    print("Dang tai VieNeu ...")
    bat_dau = time.time()
    bo_noi = BoNoi()
    print(f"  xong sau {time.time() - bat_dau:.0f}s")

    thu_vien = ThuVienGiong(os.path.join(THU_MUC, "thu-vien-giong"), bo_noi.dep)
    print(f"Thu vien giong: {thu_vien.so_cau_da_co()} cau san")


def lay_byte_tieng(cau):
    duong_dan = thu_vien.tra(cau)
    if duong_dan:
        with open(duong_dan, "rb") as f:
            return f.read(), True
    thu_vien.ghi_nho_de_sinh_sau(cau)
    return bo_noi.nhanh(cau), False


class KenhThoai:
    def __init__(self, ket_noi, ma):
        self.ket_noi = ket_noi
        self.ma = ma
        self.vad = webrtcvad.Vad(DO_KHAT_KHE_VAD)
        self.dang_bam = ""
        self.so_da_bam = ""

    def nghe_den_khi_nguoi_goi_ngung(self):
        cac_khung = []
        khung_co_tieng = 0
        khung_im = 0
        da_co_tieng = False

        for _ in range(KHUNG_TOI_DA_MOT_LUOT):
            loai, payload = self.ket_noi.doc_khung()

            if loai == LOAI_DTMF:
                self._nhan_so_bam(payload)
                if self.so_da_bam:
                    return b""
                continue
            if loai != LOAI_AUDIO:
                continue

            if self._co_tieng(payload):
                khung_co_tieng += 1
                khung_im = 0
                da_co_tieng = da_co_tieng or khung_co_tieng >= KHUNG_CO_TIENG_DE_BAT_DAU
            else:
                khung_co_tieng = 0
                khung_im += 1

            cac_khung.append(payload)

            if da_co_tieng and khung_im >= KHUNG_IM_DE_DUNG:
                break
            if not da_co_tieng and khung_im >= KHUNG_IM_KHI_CHUA_NOI:
                return None

        return b"".join(cac_khung) if da_co_tieng else None

    def phat(self, byte_tieng):
        moc = time.monotonic()
        for dau in range(0, len(byte_tieng), BYTE_MOI_KHUNG):
            khung = byte_tieng[dau:dau + BYTE_MOI_KHUNG]
            self.ket_noi.gui_audio(khung.ljust(BYTE_MOI_KHUNG, bytes(1)))
            moc += MS_MOI_KHUNG / 1000
            self._cho_den(moc)
            self.ket_noi.doc_khung()

        for _ in range(KHUNG_CHET_SAU_KHI_PHAT):
            self.ket_noi.doc_khung()

    def _nhan_so_bam(self, payload):
        ky_tu = payload.decode("ascii", "ignore")
        if ky_tu.isdigit():
            self.dang_bam += ky_tu
        elif ky_tu in ("#", "*") and self.dang_bam:
            self.so_da_bam, self.dang_bam = self.dang_bam, ""
            print(f"[{self.ma}] NGUOI GOI BAM: {self.so_da_bam}")

    def _co_tieng(self, khung):
        return (len(khung) == BYTE_MOI_KHUNG
                and self.vad.is_speech(khung, TAN_SO))

    @staticmethod
    def _cho_den(moc):
        cho = moc - time.monotonic()
        if cho > 0:
            time.sleep(cho)


def phuc_vu_cuoc_goi(kenh, hoi_thoai):
    for _ in range(SO_LUOT_TOI_DA):
        byte_nghe = kenh.nghe_den_khi_nguoi_goi_ngung()
        if byte_nghe is None:
            return

        bat_dau = time.time()
        cau_nghe_duoc = bo_nghe.nghe(byte_nghe)
        giay_tieng = len(byte_nghe) / (TAN_SO * 2)
        print(f"[{kenh.ma}] NGHE {time.time() - bat_dau:.1f}s "
              f"({giay_tieng:.1f}s tieng): {cau_nghe_duoc or '(khong ra chu)'}")

        ket_qua = hoi_thoai.tra_loi(cau_nghe_duoc, kenh.so_da_bam)
        kenh.so_da_bam = ""
        for dong in ket_qua.nhat_ky:
            print(f"    {dong}")

        if ket_qua.chuyen_may:
            print(f"[{kenh.ma}] CHUYEN MAY")
            kenh.phat(lay_byte_tieng(CAU_CHUYEN_MAY)[0])
            return

        bat_dau = time.time()
        byte_tieng, tu_thu_vien = lay_byte_tieng(ket_qua.cau_noi)
        nguon = "thu vien" if tu_thu_vien else f"piper {time.time() - bat_dau:.1f}s"
        print(f"[{kenh.ma}] NOI ({nguon}): {ket_qua.cau_noi}")
        kenh.phat(byte_tieng)


class XuLyKetNoi(socketserver.StreamRequestHandler):
    def handle(self):
        ket_noi = KetNoiAudioSocket(self.rfile, self.wfile)
        ma = "?"
        try:
            ket_noi.doc_khung()
            ma = (ket_noi.ma_cuoc_goi or "?")[:8]
            print(f"\n[{ma}] === cuoc goi moi ===")

            kenh = KenhThoai(ket_noi, ma)
            kenh.phat(lay_byte_tieng(CAU_CHAO)[0])
            phuc_vu_cuoc_goi(kenh, BoHoiThoai())
            ket_noi.gui_ngat()
        except KetThucKetNoi as ly_do:
            print(f"[{ma}] ket thuc: {ly_do}")
        except OSError as loi:
            print(f"[{ma}] mat ket noi: {loi}")

        print(f"[{ma}] === het ===")
        thu_vien.sinh_cac_cau_dang_cho()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    khoi_dong_mo_hinh()
    with Server((DIA_CHI, CONG), XuLyKetNoi) as server:
        print(f"\nAudioSocket dang cho o {DIA_CHI}:{CONG} — goi so 600")
        server.serve_forever()
