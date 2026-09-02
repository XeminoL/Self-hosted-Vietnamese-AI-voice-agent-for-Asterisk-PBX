import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from models import SAMPLE_RATE, SpeechRecognizer

BASELINE_MODEL = "mad1999/pho-whisper-small-ct2"
MIN_SECONDS = 1.5
RESULT_FILE = "ket-qua-so-sanh.txt"


def convert_to_wav(sln_path):
    wav_path = f"/tmp/{Path(sln_path).name}.wav"
    subprocess.run(
        ["sox", "-r", str(SAMPLE_RATE), "-c", "1", "-b", "16", "-e", "signed-integer",
         "-t", "raw", sln_path, wav_path],
        check=True, capture_output=True,
    )
    return wav_path


def measure_one_file(recognizer, whisper, sln_path):
    audio_bytes = Path(sln_path).read_bytes()
    audio_seconds = len(audio_bytes) / (SAMPLE_RATE * 2)

    started = time.time()
    gipformer_text = recognizer.transcribe(audio_bytes)
    gipformer_seconds = time.time() - started

    wav_path = convert_to_wav(sln_path)
    started = time.time()
    segments, _ = whisper.transcribe(wav_path, language="vi", vad_filter=True,
                                     condition_on_previous_text=False)
    whisper_text = " ".join(s.text.strip() for s in segments).strip()
    whisper_seconds = time.time() - started

    return (audio_seconds, gipformer_text, gipformer_seconds,
            whisper_text, whisper_seconds)


if __name__ == "__main__":
    from faster_whisper import WhisperModel

    files = [f for f in sys.argv[1:]
             if Path(f).stat().st_size >= SAMPLE_RATE * 2 * MIN_SECONDS]
    if not files:
        print("Cach dung: python compare_speech_models.py <file.sln> ...")
        sys.exit(1)

    print("Dang tai hai model ...")
    recognizer = SpeechRecognizer()
    whisper = WhisperModel(BASELINE_MODEL, device="cpu", compute_type="int8")

    lines = []
    totals = {"gipformer": 0.0, "whisper": 0.0}
    for path in files:
        audio_seconds, text_g, seconds_g, text_w, seconds_w = measure_one_file(
            recognizer, whisper, path)
        totals["gipformer"] += seconds_g
        totals["whisper"] += seconds_w
        lines.append(f"--- {Path(path).name} ({audio_seconds:.1f}s tieng) ---")
        lines.append(f"  gipformer  ({seconds_g:5.2f}s, {audio_seconds / seconds_g:5.1f}x): {text_g}")
        lines.append(f"  PhoWhisper ({seconds_w:5.2f}s, {audio_seconds / seconds_w:5.1f}x): {text_w}")
        lines.append("")

    lines.append(f"Tong: gipformer {totals['gipformer']:.1f}s | "
                 f"PhoWhisper {totals['whisper']:.1f}s -> "
                 f"nhanh gap {totals['whisper'] / totals['gipformer']:.1f} lan")

    text = "\n".join(lines)
    Path(RESULT_FILE).write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
