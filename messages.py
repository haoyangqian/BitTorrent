import sys
import struct

from bitmap import BitMap

BT_PROTOCOL = "BitTorrent protocol"
RESERVED = '\x00\x00\x00\x00\x00\x00\x00\x00'

MSG_KEEPALIVE = -1
MSG_CHOKE = 0
MSG_UNCHOKE = 1
MSG_INTERESTED = 2
MSG_HAVE = 4
MSG_BITFIELD = 5
MSG_REQUEST = 6
MSG_PIECE = 7

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
    if len(payload) == 0:
        print "empty handshake message"
        sys.exit(-1)

    print "creating handshake message from payload", payload, "$$$"
    pstr_len = payload[0]
    pstr = payload[1:20]
    reserved = payload[20:28]
    info_hash = payload[28:48]
    peer_id = payload[48:68]

    return HandshakeMessage(pstr_len, pstr, reserved, info_hash, peer_id)

def create_interested_message():
    return PeerMessage(MSG_INTERESTED, "")

class PeerMessage(object):
    def __init__(self, msg_id, msg):
        self.msg_id = msg_id
        self.msg = msg

    def __str__(self):
        return str(self.msg_id) + str(msg)

    def __len__(self):
        return len(self.msg)

    def to_bytes(self):
        return struct.pack("!IB", 1, self.msg_id)


class KeepAliveMessage(PeerMessage):
    def __init__(self, msg_id):
        PeerMessage.__init__(self, msg_id, "")

class HaveMessage(PeerMessage):
    def __init__(self, msg_id, msg):
        PeerMessage.__init__(self, msg_id, msg)
        self.piece_index = struct.unpack("!I", msg)[0]
        print "received a have message, piece index:", self.piece_index

class RequestMessage(PeerMessage):
    def __init__(self, index, begin, length):
        PeerMessage.__init__(self, MSG_REQUEST, "")
        self.index = index
        self.begin = begin
        self.length = length

    def to_bytes(self):
        result = struct.pack('!IbIII',
                           13,
                           MSG_REQUEST,
                           self.index,
                           self.begin,
                           self.length)

        # result = struct.pack("!I", 13) + struct.pack("!B", MSG_REQUEST) + struct.pack("!I", self.index) + struct.pack("!I", self.begin) + struct.pack("!I", self.length)
        return result

class BitfieldMessage(PeerMessage):
    def __init__(self, msg_len, msg_id, msg):
        PeerMessage.__init__(self, msg_id, msg)

        bit_string = ''
        for i in range(0, len(msg)):
            num = ord(msg[i])
            bit_string += "{0:b}".format(ord(msg[i]))

        self.bitfield = BitMap(len(bit_string))
        self.bitfield_str = bit_string

        for i in range(0, len(bit_string)):
            if bit_string[i] == '1':
                self.bitfield.set(i)

        # self.bitfield = BitMap.fromstring(msg)
        print "received a bitfield message, bitmap:", self.bitfield

class PieceMessage(PeerMessage):
    def __init__(self, msg_len, msg_id, msg):
        PeerMessage.__init__(self, msg_id, msg)
        self.index = bytes_to_int(msg[0:4])
        self.begin = bytes_to_int(msg[4:8])
        self.block = msg[8:len(msg)]
        print "received a piece message, index", self.index, "begin", self.begin, "and some block"

def parse_message(msg_len, msg):
    if msg_len > 0:
        msg_id = ord(msg[0])
    else:
        return KeepAliveMessage(MSG_KEEPALIVE)

    msg = msg[1: len(msg)]

    if msg_id == MSG_CHOKE or msg_id == MSG_UNCHOKE:
        return PeerMessage(msg_id, msg)
    elif msg_id == MSG_HAVE:
        return HaveMessage(msg_id, msg)
    elif msg_id == MSG_BITFIELD:
        return BitfieldMessage(msg_len, msg_id, msg)
    elif msg_id == MSG_PIECE:
        return PieceMessage(msg_len, msg_id, msg)

    return PeerMessage(msg_id, msg)

def bytes_to_int(bytestring):
    number = 0
    i = 3
    for byte in bytestring:
        try:
            number += ord(byte) * 256**i
        except(TypeError):
            number += byte * 256**i
        i -= 1
    return number

def int_to_bytes(number):
    return struct.pack("I", number)
    # if number < 255:
    #     length = '\x00\x00\x00' + chr(number)
    # elif number < 256**2:
    #     length = '\x00\x00' + chr((number)/256) + chr((number) % 256)
    # elif number < 256**3:
    #     length = ('\x00'+ chr((number)/256**2) + chr(((number) % 256**2) / 256) +
    #         chr(((number) % 256**2) % 256))
    # else:
    #     length = (chr((number)/256**3) + chr(((number)%256**3)/256**2) + chr((((number)%256**3)%256**2)/256) + chr((((number)%256**3)%256**2)%256))
    # return length