import struct
import uuid

LOAI_NGAT = 0x00
LOAI_UUID = 0x01
LOAI_DTMF = 0x03
LOAI_AUDIO = 0x10
LOAI_LOI = 0xFF

DAI_HEADER = 3
DAI_UUID = 16


class KetThucKetNoi(Exception):
    pass


def dong_khung(loai, payload=b""):
    return struct.pack(">BH", loai, len(payload)) + payload


def _doc_uuid(payload):
    if len(payload) == DAI_UUID:
        return str(uuid.UUID(bytes=payload))
    return payload.hex()


class KetNoiAudioSocket:
    def __init__(self, doc, ghi):
        self._doc = doc
        self._ghi = ghi
        self.ma_cuoc_goi = None

    def _doc_du(self, so_byte):
        du_lieu = b""
        while len(du_lieu) < so_byte:
            phan = self._doc.read(so_byte - len(du_lieu))
            if not phan:
                raise KetThucKetNoi("ben kia dong ket noi")
            du_lieu += phan
        return du_lieu

    def doc_khung(self):
        header = self._doc_du(DAI_HEADER)
        loai, do_dai = struct.unpack(">BH", header)
        payload = self._doc_du(do_dai) if do_dai else b""

        if loai == LOAI_NGAT:
            raise KetThucKetNoi("nguoi goi cup may")
        if loai == LOAI_LOI:
            raise KetThucKetNoi(f"asterisk bao loi: {payload.hex()}")
        if loai == LOAI_UUID:
            self.ma_cuoc_goi = _doc_uuid(payload)

        return loai, payload

    def gui_audio(self, payload):
        self._ghi.write(dong_khung(LOAI_AUDIO, payload))
        self._ghi.flush()

    def gui_ngat(self):
        self._ghi.write(dong_khung(LOAI_NGAT))
        self._ghi.flush()
