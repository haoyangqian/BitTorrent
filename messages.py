
BT_PROTOCOL = "BitTorrent protocol"
RESERVED = '\x00\x00\x00\x00\x00\x00\x00\x00'

class HandshakeMessage(object):

    def __init__(self, pstr_len, pstr, reserved, info_hash, peer_id):
        self.pstrlen = chr(19)
        self.pstr = pstr
        self.reserved = reserved
        self.info_hash = info_hash
        self.peer_id = peer_id

    def __str__(self):
        return self.pstrlen + self.pstr + \
               self.reserved + self.info_hash + \
               self.peer_id

    def __len__(self):
        return 49 + ord(self.pstrlen)

def create_hanshake_message(info_hash, peer_id):
    return HandshakeMessage(chr(19), BT_PROTOCOL, RESERVED, info_hash, peer_id)


def create_handshake_message_from_payload(payload):
    print "creating handshake message from payload", payload, "$$$"
    pstr_len = payload[0]
    pstr = payload[1:20]
    reserved = payload[20:28]
    info_hash = payload[28:48]
    peer_id = payload[48:68]

    return HandshakeMessage(pstr_len, pstr, reserved, info_hash, peer_id)


class PeerMessage(object):
    def __init__(self):
        return


class KeepAlive(PeerMessage):
    def __init__(self):
        return

