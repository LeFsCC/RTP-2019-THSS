from time import time


class RtcpPacket:
    def __init__(self):
        self.payload = bytearray(8)
        self.header = bytearray(8)

    def encode(self, version, padding, rc, pt, ssrc, length, payload):
        """Encode the RTP packet with header fields and payload."""
        timestamp = int(time())
        self.header[0] = (version << 6) | (padding << 5) | rc
        self.header[1] = pt
        self.header[2] = (length >> 8) & 255
        self.header[3] = length & 255
        self.header[4] = ssrc >> 24 & 255
        self.header[5] = ssrc >> 16 & 255
        self.header[6] = ssrc >> 8 & 255
        self.header[7] = ssrc & 255
        self.payload = payload

    def decode(self, byteStream):
        """Decode the RTP packet."""
        self.header = bytearray(byteStream[:8])
        self.payload = byteStream[8:]

    def getPayload(self):
        return self.payload

    def getPacket(self):
        return self.header + self.payload
