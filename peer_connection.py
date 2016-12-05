import socket
from messages import *
from Queue import Queue
from Pieces import *
import bitmap
from threading import Thread

TCP_CONNECTION_TIMEOUT = 2

TCP_BUFFER_SIZE = 128000

STATE_INITIALIZED = "INITIALIZED"
STATE_CONNECTED = "CONNECTED"
STATE_CLOSED = "CLOSED"
STATE_BUSY = "BUSY"
STATE_IDLE = "IDLE"

MESSAGE_LEN_SIZE = 4
HANDSHAKE_MESSAGE_LEN = 49 + len(BT_PROTOCOL)

def parse_message_length(bytestring):
    '''bytestring assumed to be 4 bytes long and represents 1 number'''
    number = 0
    i = 3
    for byte in bytestring:
        try:
            number += ord(byte) * 256**i
        except(TypeError):
            number += byte * 256**i
        i -= 1
    return number

class PeerConnection(object):

    def __init__(self, self_peer_id, peer, info_hash):
        self.self_peer_id = self_peer_id
        self.job_queue = Queue()
        self.complete_queue = Queue()
        self.info_hash = info_hash

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.state = STATE_INITIALIZED
        self.establish_connection(peer)

    def establish_connection(self, peer):
        tokens = peer.split(":")
        host = tokens[0]
        port = int(tokens[1])

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(TCP_CONNECTION_TIMEOUT)
        print host, port

        try:
            self.socket.connect((host, port))
            self.handshake()

            self.state = STATE_CONNECTED
            self.update_state(STATE_CONNECTED)
            self.socket.settimeout(None)
        except socket.timeout:
            self.close()

    def close(self):
        self.update_state(STATE_CLOSED)

    def update_state(self, state):
        self.state = state

    def is_initialized(self):
        return self.state == STATE_INITIALIZED

    def is_closed(self):
        return self.state == STATE_CLOSED

    def is_connected(self):
        return self.state == STATE_CONNECTED

    def is_busy(self):
        return self.state == STATE_BUSY

    def is_idle(self):
        return self.state == STATE_IDLE

    def is_choked(self):
        return self.am_choking

    def handshake(self):
        m = create_hanshake_message(self.info_hash, self.self_peer_id)

        self.socket.settimeout(TCP_CONNECTION_TIMEOUT)
        self.socket.send(str(m))

        payload = self.socket.recv(HANDSHAKE_MESSAGE_LEN)
        handshake_response = create_handshake_message_from_payload(payload)
        print handshake_response
        print handshake_response.info_hash
        return

    def download_piece(self, piece):
        self.job_queue.put(piece)
        return

    def start_download(self):
        # thread.start_new_thread(self.run, ("Thread-worker", 1))
        t = Thread(target=self.run, args=())
        t.start()
        t.join()
        return

    def receive_next_message(self):
        message_length = parse_message_length(self.socket.recv(MESSAGE_LEN_SIZE))
        message = self.socket.recv(message_length)

        # return self.make_message(message_length, message)
        return message

    def make_message(self, len, m):
        return

    def handle_msg(self, msg):
        if msg.id == 0:
            self.handle_choke_msg(msg)
        elif message.id == 1:
            self.handle_unchoke_msg(msg)
        elif message.id == 4:
            self.handle_have_msg(msg)
        elif message.id == 5:
            self.handle_bitfield_msg(msg)
        elif message.id == 7:
            self.handle_piece_msg(msg)

    def handle_choke_msg(self, msg):
        self.am_choking = True

    def handle_unchoke_msg(self, msg):
        self.am_choking = False

    def handle_have_msg(self, msg):
        self.available_pieces.set(msg.piece_index)

    def handle_bitfiled_msg(self, msg):
        self.available_pieces = bitmap.fromstring(msg.bitfield)

    def handle_piece_msg(self, msg):
        block_offset = msg.begin
        block = msg.block
        self.current_piece.block_list[block_offset].set_payload(block)
        self.check_for_piece_completion()

    def check_for_piece_completion(self):
        for block_offset in self.current_piece.block_list:
            if not self.current_piece.block_list[block_offset].is_complete:
                return

        self.complete_queue.put(self.current_piece)
        self.update_state(STATE_IDLE)
        self.current_piece = None

    def run(self):
        while True:
            msg = self.receive_next_message()
            print "message received is ", msg, len(msg)

        self.socket.send(str(m))
        payload = self.socket.recv(1024)
        handshake_response = create_handshake_message_from_payload(payload)
        print handshake_response
        print handshake_response.info_hash
        print self.info_hash
        return

