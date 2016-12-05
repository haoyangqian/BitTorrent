
BT_PROTOCOL = "BitTorrent protocol"
RESERVED = '\x00\x00\x00\x00\x00\x00\x00\x00'

class Handshake(object):

    def __init__(self, pstr_len, pstr, reserved, info_has, peer_id):
        self.pstrlen = chr(19)
        self.pstr = pstr
        self.reserved = reserved
        self.info_hash = info_hash
        self.peer_id = peer_id

    def __str__(self):
        return self.pstrlen + self.pstr +
               self.reserved + self.info_hash +
               self.peer_id

    def __len__(self):
        return 49 + ord(self.pstrlen)

def create_hanshake(info_hash, peer_id)
    return Handshake(chr(19), BT_PROTOCOL, RESERVED, info_hash, peer_id)


def create_handshake_from_payload(payload):
    pstr_len = payload[0]
    pstr = payload[1:20]
    reserverd = payload[20:28]
    info_hash = payload[28:48]
    peer_id = payload[48:68]

    return Handshake(pstr_len, pstr, reserved, info_hash, peer_id)


class PeerMessage(object):
    def __init__(self):
        return


class KeepAlive(Message)

