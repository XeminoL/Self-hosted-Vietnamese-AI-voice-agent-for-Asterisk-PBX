import os
import subprocess
import threading

APP_DIR = os.path.dirname(os.path.abspath(__file__))
GIPFORMER_DIR = os.path.expanduser("~/gipformer")
PIPER_BIN = os.path.expanduser("~/piper/piper/piper")
PIPER_VOICE = os.path.expanduser("~/piper/vi_VN-vais1000-medium.onnx")

SAMPLE_RATE = 8000
RECOGNIZER_THREADS = 4
LIBRARY_VOICE = "Mỹ Duyên"
MIN_SECONDS_TO_RECOGNIZE = 1.0


class SpeechRecognizer:
    def __init__(self):
        import sherpa_onnx

        self._model = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=f"{GIPFORMER_DIR}/encoder.int8.onnx",
            decoder=f"{GIPFORMER_DIR}/decoder.int8.onnx",
            joiner=f"{GIPFORMER_DIR}/joiner.int8.onnx",
            tokens=f"{GIPFORMER_DIR}/tokens.txt",
            num_threads=RECOGNIZER_THREADS,
            decoding_method="modified_beam_search",
        )

    def transcribe(self, audio_bytes):
        import numpy

        if len(audio_bytes) < SAMPLE_RATE * 2 * MIN_SECONDS_TO_RECOGNIZE:
            return ""
        samples = numpy.frombuffer(audio_bytes, dtype=numpy.int16)
        stream = self._model.create_stream()
        stream.accept_waveform(SAMPLE_RATE, samples.astype(numpy.float32) / 32768.0)
        try:
            self._model.decode_stream(stream)
        except RuntimeError as error:
            print(f"    (gipformer loi: {error})")
            return ""
        return stream.result.text.strip().lower()


class SpeechSynthesizer:
    def __init__(self):
        from vieneu import Vieneu

        self._vieneu = Vieneu()

    def fast(self, sentence):
        wav_path = f"/tmp/piper-{os.getpid()}-{threading.get_ident()}.wav"
        subprocess.run([PIPER_BIN, "-m", PIPER_VOICE, "-f", wav_path],
                       input=sentence.encode("utf-8"), check=True, capture_output=True)
        return _convert_to_sln_and_read(wav_path)

    def polished(self, sentence, sln_path):
        wav_path = f"/tmp/vieneu-{os.path.basename(sln_path)}.wav"
        self._vieneu.save(self._vieneu.infer(sentence, voice=LIBRARY_VOICE), wav_path)
        _convert_to_sln(wav_path, sln_path)


def _convert_to_sln(wav_path, sln_path):
    subprocess.run(
        ["sox", wav_path, "-r", str(SAMPLE_RATE), "-c", "1", "-b", "16",
         "-e", "signed-integer", "-t", "raw", sln_path],
        check=True, capture_output=True,
    )
    os.remove(wav_path)


def _convert_to_sln_and_read(wav_path):
    sln_path = wav_path.replace(".wav", ".sln")
    _convert_to_sln(wav_path, sln_path)
    with open(sln_path, "rb") as f:
        audio_bytes = f.read()
    os.remove(sln_path)
    return audio_bytes
