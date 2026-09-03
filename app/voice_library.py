import hashlib
import json
import os
import threading


class VoiceLibrary:
    def __init__(self, directory, synthesize_polished):
        self.directory = directory
        self.synthesize_polished = synthesize_polished
        self.index_file = os.path.join(directory, "index.json")
        self.index = self._read_index()
        self.pending = []
        self.lock = threading.Lock()
        os.makedirs(directory, exist_ok=True)

    def _read_index(self):
        if not os.path.exists(self.index_file):
            return {}
        with open(self.index_file, encoding="utf-8") as f:
            return json.load(f)

    def _write_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _key_for(sentence):
        return hashlib.sha1(sentence.strip().lower().encode("utf-8")).hexdigest()[:16]

    def lookup(self, sentence):
        key = self._key_for(sentence)
        if key not in self.index:
            return None
        path = os.path.join(self.directory, key + ".sln")
        if not os.path.exists(path):
            del self.index[key]
            self._write_index()
            return None
        return path

    def queue_for_later(self, sentence):
        with self.lock:
            if self._key_for(sentence) not in self.index and sentence not in self.pending:
                self.pending.append(sentence)

    def synthesize_pending(self):
        with self.lock:
            sentences = list(self.pending)
            self.pending.clear()

        for sentence in sentences:
            key = self._key_for(sentence)
            sln_path = os.path.join(self.directory, key + ".sln")
            try:
                self.synthesize_polished(sentence, sln_path)
            except Exception as error:
                print(f"  (khong sinh duoc giong dep cho '{sentence[:30]}...': {error})")
                continue
            self.index[key] = sentence
            self._write_index()
            print(f"  (da them vao thu vien giong: {sentence[:50]})")

    def size(self):
        return len(self.index)