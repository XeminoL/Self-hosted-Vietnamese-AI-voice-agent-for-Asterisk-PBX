import socketserver
import time

from audiosocket import KetNoiAudioSocket, KetThucKetNoi

DIA_CHI = "127.0.0.1"
CONG = 9092
TAN_SO = 8000
GIAY_THU = 5


class XuLyKetNoi(socketserver.StreamRequestHandler):
    def handle(self):
        ket_noi = KetNoiAudioSocket(self.rfile, self.wfile)
        print("\n=== ket noi moi ===")

        so_khung = 0
        tong_byte = 0
        cac_co_khung = {}
        bat_dau = time.time()

        try:
            while time.time() - bat_dau < GIAY_THU:
                loai, payload = ket_noi.doc_khung()
                if ket_noi.ma_cuoc_goi and so_khung == 0:
                    print(f"  uuid: {ket_noi.ma_cuoc_goi}")
                if loai == 0x10:
                    so_khung += 1
                    tong_byte += len(payload)
                    cac_co_khung[len(payload)] = cac_co_khung.get(len(payload), 0) + 1
                    ket_noi.gui_audio(payload)
                else:
                    print(f"  khung la: loai 0x{loai:02x}, {len(payload)} byte")
        except KetThucKetNoi as ly_do:
            print(f"  ket thuc: {ly_do}")

        giay = time.time() - bat_dau
        print(f"  nhan {so_khung} khung, {tong_byte} byte trong {giay:.1f}s")
        if so_khung:
            print(f"  co khung: {cac_co_khung}")
            print(f"  nhip: {giay / so_khung * 1000:.1f} ms/khung")
            print(f"  tieng: {tong_byte / (TAN_SO * 2):.1f}s")
        print("=== het ===")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server((DIA_CHI, CONG), XuLyKetNoi) as server:
        print(f"AudioSocket dang cho o {DIA_CHI}:{CONG}")
        print(f"Goi so 600, no se vong lai tieng cua ban trong {GIAY_THU}s")
        server.serve_forever()
