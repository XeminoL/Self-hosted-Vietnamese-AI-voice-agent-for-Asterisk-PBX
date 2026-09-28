import os

GIPFORMER_DIR = os.path.expanduser("~/gipformer")
PIPER_VOICE = os.path.expanduser("~/piper/cake/vi_VN-csa-voice-piper-v3-medium.onnx")
PIPER_SPEAKER = 0

SAMPLE_RATE = 8000
RECOGNIZER_SAMPLE_RATE = 16000
RECOGNIZER_THREADS = 2
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
        import soxr

        if len(audio_bytes) < SAMPLE_RATE * 2 * MIN_SECONDS_TO_RECOGNIZE:
            return ""
        samples = numpy.frombuffer(audio_bytes, dtype=numpy.int16).astype(numpy.float32) / 32768.0
        stream = self._model.create_stream()
        stream.accept_waveform(RECOGNIZER_SAMPLE_RATE,
                               soxr.resample(samples, SAMPLE_RATE, RECOGNIZER_SAMPLE_RATE))
        try:
            self._model.decode_stream(stream)
        except RuntimeError as error:
            print(f"    (gipformer loi: {error})")
            return ""
        return stream.result.text.strip().lower()


class SpeechSynthesizer:
    def __init__(self, speaker=PIPER_SPEAKER):
        from piper import PiperVoice, SynthesisConfig

        self._voice = PiperVoice.load(PIPER_VOICE)
        self._config = SynthesisConfig(speaker_id=speaker)

    def speak(self, sentence):
        import numpy
        import soxr

        audio = b"".join(chunk.audio_int16_bytes
                         for chunk in self._voice.synthesize(sentence, syn_config=self._config))
        samples = numpy.frombuffer(audio, dtype=numpy.int16).astype(numpy.float32) / 32768.0
        phone = soxr.resample(samples, self._voice.config.sample_rate, SAMPLE_RATE)
        return (numpy.clip(phone, -1.0, 1.0) * 32767).astype("<i2").tobytes()
