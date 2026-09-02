import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dieu-khien"))

from mo_hinh import BoNghe, TAN_SO

MODEL_SO_SANH = "mad1999/pho-whisper-small-ct2"
GIAY_TOI_THIEU = 1.5


def doi_sang_wav(duong_dan_sln):
    duong_dan_wav = f"/tmp/{Path(duong_dan_sln).name}.wav"
    subprocess.run(
        ["sox", "-r", str(TAN_SO), "-c", "1", "-b", "16", "-e", "signed-integer",
         "-t", "raw", duong_dan_sln, duong_dan_wav],
        check=True, capture_output=True,
    )
    return duong_dan_wav


def do_mot_file(bo_nghe, whisper, duong_dan_sln):
    byte_tieng = Path(duong_dan_sln).read_bytes()
    giay_tieng = len(byte_tieng) / (TAN_SO * 2)

    bat_dau = time.time()
    chu_gipformer = bo_nghe.nghe(byte_tieng)
    giay_gipformer = time.time() - bat_dau

    duong_dan_wav = doi_sang_wav(duong_dan_sln)
    bat_dau = time.time()
    cac_doan, _ = whisper.transcribe(duong_dan_wav, language="vi", vad_filter=True,
                                     condition_on_previous_text=False)
    chu_whisper = " ".join(d.text.strip() for d in cac_doan).strip()
    giay_whisper = time.time() - bat_dau

    return giay_tieng, chu_gipformer, giay_gipformer, chu_whisper, giay_whisper


if __name__ == "__main__":
    from faster_whisper import WhisperModel

    cac_file = [f for f in sys.argv[1:]
                if Path(f).stat().st_size >= TAN_SO * 2 * GIAY_TOI_THIEU]
    if not cac_file:
        print("Cach dung: python so_sanh_model_nghe.py <file.sln> ...")
        sys.exit(1)

    print("Dang tai hai model ...")
    bo_nghe = BoNghe()
    whisper = WhisperModel(MODEL_SO_SANH, device="cpu", compute_type="int8")

    cac_dong = []
    tong = {"gipformer": 0.0, "whisper": 0.0}
    for duong_dan in cac_file:
        giay_tieng, chu_g, giay_g, chu_w, giay_w = do_mot_file(bo_nghe, whisper, duong_dan)
        tong["gipformer"] += giay_g
        tong["whisper"] += giay_w
        cac_dong.append(f"--- {Path(duong_dan).name} ({giay_tieng:.1f}s tieng) ---")
        cac_dong.append(f"  gipformer  ({giay_g:5.2f}s, {giay_tieng / giay_g:5.1f}x): {chu_g}")
        cac_dong.append(f"  PhoWhisper ({giay_w:5.2f}s, {giay_tieng / giay_w:5.1f}x): {chu_w}")
        cac_dong.append("")

    cac_dong.append(f"Tong: gipformer {tong['gipformer']:.1f}s | "
                    f"PhoWhisper {tong['whisper']:.1f}s -> "
                    f"nhanh gap {tong['whisper'] / tong['gipformer']:.1f} lan")

    ket_qua = "\n".join(cac_dong)
    Path("ket-qua-so-sanh.txt").write_text(ket_qua, encoding="utf-8")
    print(ket_qua.encode("ascii", "replace").decode("ascii"))
