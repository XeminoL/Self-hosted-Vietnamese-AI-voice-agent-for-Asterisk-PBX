import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dieu-khien"))

from hoi_thoai import BoHoiThoai

CAC_LUOT_MAU = [
    "tôi muốn biết số dư tài khoản",
    "lãi suất tiết kiệm bao nhiêu",
    "chuyển tiền mất phí không",
    "mấy giờ ngân hàng mở cửa",
    "tôi muốn vay tiền thì cần gì",
    "rút tiền ở máy atm khác có mất phí không",
    "quên mật khẩu thì làm sao",
    "đô la hôm nay bao nhiêu",
    "giá vàng thế nào rồi",
    "thời tiết hôm nay thế nào",
    "cho tôi gặp người thật",
]
SO_DIEN_THOAI_GIA = "0901234567"


def in_ket_qua(cac_dong):
    ket_qua = "\n".join(cac_dong)
    Path("ket-qua-thu.txt").write_text(ket_qua, encoding="utf-8")
    print(ket_qua.encode("ascii", "replace").decode("ascii"))
    print("\nBan co dau: cat kiem-thu/ket-qua-thu.txt")


def chay(cac_luot):
    bo = BoHoiThoai()
    cac_dong = []
    cac_giay = []

    for thu_tu, cau in enumerate(cac_luot, start=1):
        so_da_bam = SO_DIEN_THOAI_GIA if "bấm số" in cau else ""
        bat_dau = time.time()
        ket_qua = bo.tra_loi(cau, so_da_bam)
        giay = time.time() - bat_dau
        cac_giay.append(giay)

        cac_dong.append(f"--- luot {thu_tu} ({giay:.1f}s) ---")
        cac_dong.append(f"  nguoi goi: {cau}")
        for dong in ket_qua.nhat_ky:
            cac_dong.append(f"  [{dong}]")
        cac_dong.append(f"  tong dai : "
                        f"{'(chuyen cho nhan vien)' if ket_qua.chuyen_may else ket_qua.cau_noi}")
        cac_dong.append("")

    cac_dong.append(f"HIEU: nhanh nhat {min(cac_giay):.1f}s | "
                    f"cham nhat {max(cac_giay):.1f}s | "
                    f"trung binh {sum(cac_giay) / len(cac_giay):.1f}s")
    return cac_dong


if __name__ == "__main__":
    in_ket_qua(chay(sys.argv[1:] or CAC_LUOT_MAU))
