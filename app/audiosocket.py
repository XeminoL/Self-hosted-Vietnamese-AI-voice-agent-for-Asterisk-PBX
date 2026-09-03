import struct
import uuid

TYPE_HANGUP = 0x00
TYPE_UUID = 0x01
TYPE_DTMF = 0x03
TYPE_AUDIO = 0x10
TYPE_ERROR = 0xFF

HEADER_BYTES = 3
UUID_BYTES = 16


class ConnectionClosed(Exception):
    pass


def build_frame(frame_type, payload=b""):
    return struct.pack(">BH", frame_type, len(payload)) + payload


def _parse_uuid(payload):
    if len(payload) == UUID_BYTES:
        return str(uuid.UUID(bytes=payload))
    return payload.hex()


class AudioSocketConnection:
    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer
        self.call_id = None

    def _read_exactly(self, byte_count):
        data = b""
        while len(data) < byte_count:
            chunk = self._reader.read(byte_count - len(data))
            if not chunk:
                raise ConnectionClosed("peer closed the connection")
            data += chunk
        return data

    def read_frame(self):
        header = self._read_exactly(HEADER_BYTES)
        frame_type, length = struct.unpack(">BH", header)
        payload = self._read_exactly(length) if length else b""

        if frame_type == TYPE_HANGUP:
            raise ConnectionClosed("caller hung up")
        if frame_type == TYPE_ERROR:
            raise ConnectionClosed(f"asterisk reported an error: {payload.hex()}")
        if frame_type == TYPE_UUID:
            self.call_id = _parse_uuid(payload)

        return frame_type, payload

    def send_audio(self, payload):
        self._writer.write(build_frame(TYPE_AUDIO, payload))
        self._writer.flush()

    def send_hangup(self):
        self._writer.write(build_frame(TYPE_HANGUP))
        self._writer.flush()