import os
import subprocess
import threading

THU_MUC = os.path.dirname(os.path.abspath(__file__))
THU_MUC_GIPFORMER = os.path.expanduser("~/gipformer")
PIPER = os.path.expanduser("~/piper/piper/piper")
PIPER_GIONG = os.path.expanduser("~/piper/vi_VN-vais1000-medium.onnx")

TAN_SO = 8000
SO_LUONG_NGHE = 4
GIONG_DEP = "Mỹ Duyên"
GIAY_TOI_THIEU_DE_NGHE = 1.0


class BoNghe:
    def __init__(self):
        import sherpa_onnx

        self._model = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=f"{THU_MUC_GIPFORMER}/encoder.int8.onnx",
            decoder=f"{THU_MUC_GIPFORMER}/decoder.int8.onnx",
            joiner=f"{THU_MUC_GIPFORMER}/joiner.int8.onnx",
            tokens=f"{THU_MUC_GIPFORMER}/tokens.txt",
            num_threads=SO_LUONG_NGHE,
            decoding_method="modified_beam_search",
        )

    def nghe(self, byte_tieng):
        import numpy

        if len(byte_tieng) < TAN_SO * 2 * GIAY_TOI_THIEU_DE_NGHE:
            return ""
        mau = numpy.frombuffer(byte_tieng, dtype=numpy.int16)
        dong = self._model.create_stream()
        dong.accept_waveform(TAN_SO, mau.astype(numpy.float32) / 32768.0)
        try:
            self._model.decode_stream(dong)
        except RuntimeError as loi:
            print(f"    (gipformer loi: {loi})")
            return ""
        return dong.result.text.strip().lower()


class BoNoi:
    def __init__(self):
        from vieneu import Vieneu

        self._vieneu = Vieneu()

    def nhanh(self, cau):
        file_wav = f"/tmp/piper-{os.getpid()}-{threading.get_ident()}.wav"
        subprocess.run([PIPER, "-m", PIPER_GIONG, "-f", file_wav],
                       input=cau.encode("utf-8"), check=True, capture_output=True)
        return _doi_sang_sln_roi_doc(file_wav)

    def dep(self, cau, duong_dan_sln):
        file_wav = f"/tmp/vieneu-{os.path.basename(duong_dan_sln)}.wav"
        self._vieneu.save(self._vieneu.infer(cau, voice=GIONG_DEP), file_wav)
        _doi_sang_sln(file_wav, duong_dan_sln)


def _doi_sang_sln(file_wav, duong_dan_sln):
    subprocess.run(
        ["sox", file_wav, "-r", str(TAN_SO), "-c", "1", "-b", "16",
         "-e", "signed-integer", "-t", "raw", duong_dan_sln],
        check=True, capture_output=True,
    )
    os.remove(file_wav)


def _doi_sang_sln_roi_doc(file_wav):
    duong_dan_sln = file_wav.replace(".wav", ".sln")
    _doi_sang_sln(file_wav, duong_dan_sln)
    with open(duong_dan_sln, "rb") as f:
        byte_tieng = f.read()
    os.remove(duong_dan_sln)
    return byte_tieng
