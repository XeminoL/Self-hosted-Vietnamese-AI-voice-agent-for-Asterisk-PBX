import hashlib
import json
import os
import subprocess
import threading

TAN_SO = 8000


class ThuVienGiong:
    def __init__(self, thu_muc_host, sinh_giong_dep):
        self.thu_muc_host = thu_muc_host
        self.sinh_giong_dep = sinh_giong_dep
        self.file_so_cai = os.path.join(thu_muc_host, "so-cai.json")
        self.so_cai = self._doc_so_cai()
        self.hang_cho = []
        self.khoa = threading.Lock()
        os.makedirs(thu_muc_host, exist_ok=True)

    def _doc_so_cai(self):
        if not os.path.exists(self.file_so_cai):
            return {}
        with open(self.file_so_cai, encoding="utf-8") as f:
            return json.load(f)

    def _ghi_so_cai(self):
        with open(self.file_so_cai, "w", encoding="utf-8") as f:
            json.dump(self.so_cai, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _ma_cau(cau):
        return hashlib.sha1(cau.strip().lower().encode("utf-8")).hexdigest()[:16]

    def tra(self, cau):
        ma = self._ma_cau(cau)
        if ma not in self.so_cai:
            return None
        duong_dan = os.path.join(self.thu_muc_host, ma + ".sln")
        if not os.path.exists(duong_dan):
            del self.so_cai[ma]
            self._ghi_so_cai()
            return None
        return duong_dan

    def ghi_nho_de_sinh_sau(self, cau):
        with self.khoa:
            if self._ma_cau(cau) not in self.so_cai and cau not in self.hang_cho:
                self.hang_cho.append(cau)

    def sinh_cac_cau_dang_cho(self):
        with self.khoa:
            cac_cau = list(self.hang_cho)
            self.hang_cho.clear()

        for cau in cac_cau:
            ma = self._ma_cau(cau)
            duong_dan_sln = os.path.join(self.thu_muc_host, ma + ".sln")
            try:
                self.sinh_giong_dep(cau, duong_dan_sln)
            except Exception as loi:
                print(f"  (khong sinh duoc giong dep cho '{cau[:30]}...': {loi})")
                continue
            self.so_cai[ma] = cau
            self._ghi_so_cai()
            print(f"  (da them vao thu vien giong: {cau[:50]})")

    def so_cau_da_co(self):
        return len(self.so_cai)
