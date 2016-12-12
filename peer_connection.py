import socket
from messages import *
from Queue import Queue
from Pieces import *
import bitmap
from threading import Thread
from sets import Set
import time

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
    return struct.unpack("!I", bytestring)[0]
    # '''bytestring assumed to be 4 bytes long and represents 1 number'''
    # number = 0
    # i = 3
    # for byte in bytestring:
    #     try:
    #         number += ord(byte) * 256**i
    #     except(TypeError):
    #         number += byte * 256**i
    #     i -= 1
    # return number

class PeerConnection(object):

    def __init__(self, self_peer_id, peer, info_hash):
        self.self_peer_id = self_peer_id
        self.peer = peer
        self.job_queue = Queue()
        self.complete_queue = Queue()
        self.info_hash = info_hash

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.state = STATE_INITIALIZED
        self.establish_connection(peer)

        self.currently_interested_piece = None
        self.currently_requested_blocks = Set([])
        self.currently_requested_block = None

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
        except socket.error:
            self.close()

    def close(self):
        print "#close, closing the connection"
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

    def should_receive_messages(self):
        return not self.is_closed()

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
        self.current_piece = piece
        return

    def start_download(self):
        # thread.start_new_thread(self.run, ("Thread-worker", 1))
        t = Thread(target=self.run, args=())
        t.start()
        t.join()
        return

    def receive_next_message(self):
        try:
            message_length_raw = self.socket.recv(MESSAGE_LEN_SIZE)
        except socket.error, e:
            print "Peer", self.peer, "has closed connection"
            self.close()
            return None

        if message_length_raw == "" or message_length_raw is None:
            print "Peer", self.peer, "has closed connection"
            self.close()
            return None

        message_length = parse_message_length(message_length_raw)
        print "message length is ", message_length

        message = ""
        size_received = 0

        while size_received != message_length:
            print "looping to get the next message"
            next_chunk = self.socket.recv(message_length - size_received)
            message += next_chunk
            size_received += len(next_chunk)

        parsed_msg = parse_message(message_length, message)
        return parsed_msg

    def handle_msg(self, msg):
        if msg is None:
            print "empty message, return"
            return

        if msg.msg_id == MSG_KEEPALIVE:
            self.handle_keepalive_msg(msg)
        elif msg.msg_id == MSG_CHOKE:
            self.handle_choke_msg(msg)
        elif msg.msg_id == MSG_UNCHOKE:
            self.handle_unchoke_msg(msg)
        elif msg.msg_id == MSG_HAVE:
            self.handle_have_msg(msg)
        elif msg.msg_id == MSG_BITFIELD:
            self.handle_bitfield_msg(msg)
        elif msg.msg_id == MSG_PIECE:
            self.handle_piece_msg(msg)
        else:
            print "received unsupported message"

    def handle_keepalive_msg(self, msg):
        print "handling KEEP ALIVE msg from peer", self.peer

    def handle_choke_msg(self, msg):
        print "handling CHOKE msg from peer", self.peer
        self.am_choking = True

    def handle_unchoke_msg(self, msg):
        print "handling UNCHOKE msg from peer", self.peer
        self.am_choking = False

    def handle_have_msg(self, msg):
        print "handling HAVE msg from peer", self.peer
        self.available_pieces.set(msg.piece_index)

    def handle_bitfield_msg(self, msg):
        print "handling BITFIELD msg from peer", self.peer
        self.available_pieces = msg.bitfield

    def handle_piece_msg(self, msg):
        print "handling PIECE msg from peer", self.peer
        # block_offset = msg.begin
        # block = msg.block
        # self.current_piece.block_list[block_offset].set_payload(block)
        # self.check_for_piece_completion()

    def check_for_piece_completion(self):
        for block_offset in self.current_piece.block_list:
            if not self.current_piece.block_list[block_offset].is_complete:
                return

        self.complete_queue.put(self.current_piece)
        self.update_state(STATE_IDLasdfasE)
        self.current_piece = None

    def send_interested_message(self):
        print "Sending INTERESTED message to peer", self.peer
        msg = create_interested_message()
        self.interested = True

        try:
            self.socket.send(msg.to_bytes())
        except socket.error, e:
            print "could not send data to peer", self.peer
            return

    def send_request_message(self, block):
        print "Sending REQUEST message to peer", self.peer
        msg = RequestMessage(block.piece_index, block.block_offset, block.block_size)

        try:
            self.socket.send(msg.to_bytes())
        except socket.error, e:
            print "could not send data to peer", self.peer
            return

    def run(self):
        request_thread = Thread(target=self.request_for_blocks, args=())
        request_thread.start()


        receive_thread = Thread(target=self.receive_messages, args=())
        receive_thread.start()

        # request_thread.join()
        # receive_thread.join()
        return

    def receive_messages(self):
        while self.should_receive_messages():
            msg = self.receive_next_message()
            self.handle_msg(msg)

        print "stopped receiving messages"


    def request_for_blocks(self):
        while True:
            if self.is_closed():
                print "connection has already been closed, closing down sending thread to peer", self.peer
                break

            if self.is_choked():
                self.send_interested_message()
                time.sleep(5)
                continue

            if len(self.currently_requested_blocks) > 10:
                continue

            if self.is_idle() and not self.job_queue.empty():
                self.currently_interested_piece = self.job_queue.get()
                self.update_state(STATE_BUSY)

            if self.is_busy():
                block = self.get_next_block_to_request()
                self.send_request_message(block)


            # self.send_request_message(Block(0, i * 2**14, 2**19))
            # self.send_request_message(Block(0, 0, 2**14))
            # time.sleep(10)
            # for block in currently_interested_piece.blocks_list:
            #     if block not in self.currently_requested_blocks:
            #         self.currently_requested_blocks.add(block)
            #         self.send_request_message(block)










