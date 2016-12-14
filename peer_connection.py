import socket
from messages import *
from Queue import Queue
from Pieces import *
import bitmap
from threading import Thread, Lock
from sets import Set
import time
import logging

TCP_CONNECTION_TIMEOUT = 2

TCP_BUFFER_SIZE = 128000

STATE_INITIALIZED = "INITIALIZED"
STATE_CONNECTED = "CONNECTED"
STATE_CLOSED = "CLOSED"
STATE_BUSY = "BUSY"
STATE_IDLE = "IDLE"

MESSAGE_LEN_SIZE = 4
HANDSHAKE_MESSAGE_LEN = 49 + len(BT_PROTOCOL)

MAX_BLOCK_WAITING_MILLIS = 3000
MAX_BLOCK_REQUESTS_IN_FLIGHT = 20

def current_millis():
    return int(round(time.time() * 1000))

def parse_message_length(bytestring):
    return struct.unpack("!I", bytestring)[0]

class PeerConnection(object):

    def __init__(self, self_peer_id, peer, info_hash):
        self.logger = logging.getLogger(__name__)
        self.logger

        self.self_peer_id = self_peer_id
        self.peer = peer
        self.job_queue = Queue()
        self.data_queue = Queue()
        self.info_hash = info_hash

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.state = STATE_INITIALIZED
        self.establish_connection(peer)

        self.currently_interested_piece = None
        self.currently_requested_blocks = {}
        self.currently_requested_block = None

        self.lock = Lock()


    def establish_connection(self, peer):
        tokens = peer.split(":")
        host = tokens[0]
        port = int(tokens[1])

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(TCP_CONNECTION_TIMEOUT)

        try:
            self.socket.connect((host, port))
            self.handshake()

            self.update_state(STATE_CONNECTED)
            self.socket.settimeout(None)
        except socket.timeout:
            self.close()
        except socket.error:
            self.close()

    def close(self):
        self.logger.debug("{} #close, closing the connection".format(self.peer))
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

    def can_make_request(self):
        if self.is_closed():
            return False

        if self.is_busy():
            return False

        if self.is_choked():
            return False

        return True

    def handshake(self):
        m = create_hanshake_message(self.info_hash, self.self_peer_id)

        self.socket.settimeout(TCP_CONNECTION_TIMEOUT)
        self.socket.send(str(m))

        payload = self.socket.recv(HANDSHAKE_MESSAGE_LEN)
        handshake_response = create_handshake_message_from_payload(payload)

        if handshake_response is None:
            self.close()
            return

        self.logger.debug(handshake_response)
        self.logger.debug(handshake_response.info_hash)
        return

    def download_piece(self, piece):
        self.job_queue.put(piece)
        self.current_piece = piece
        return

    def can_request_piece(self, piece):
        result = False
        try:

            if self.available_pieces is None or not self.job_queue.empty():
                result = False
            else:
                result = self.available_pieces.test(piece.piece_index)

            if self.available_pieces.count() == 0:
                self.close()

            return result
        except:
            return False


    def receive_next_message(self):

        try:
            self.socket.settimeout(TCP_CONNECTION_TIMEOUT)
            message_length_raw = self.socket.recv(MESSAGE_LEN_SIZE)
        except socket.timeout:
            self.socket.settimeout(None)
            return None
        except socket.error, e:
            self.socket.settimeout(None)
            self.logger.debug("{} has closed connection".format(self.peer))
            self.close()
            return None

        if message_length_raw == "" or message_length_raw is None:
            self.logger.debug("{} has closed connection".format(self.peer))
            self.close()
            return None

        message_length = parse_message_length(message_length_raw)

        message = ""
        size_received = 0

        try:
            while size_received != message_length:
                next_chunk = self.socket.recv(message_length - size_received)
                message += next_chunk
                size_received += len(next_chunk)
        except:
            self.logger.debug("{} error receiving the next full message {} {}".format(self.peer, message_length, size_received))
            self.close
            return None

        parsed_msg = parse_message(message_length, message)
        return parsed_msg

    def handle_msg(self, msg):
        if msg is None:
            self.logger.debug("{} Empty message received".format(self.peer))
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
            self.logger.debug("{} received unsupported message id: {}".format(self.peer, msg.msg_id))

    def handle_keepalive_msg(self, msg):
        self.logger.debug("{} handling KEEP ALIVE msg from peer".format(self.peer))

    def handle_choke_msg(self, msg):
        self.logger.debug("{} handling CHOKE msg from peer".format(self.peer))
        self.am_choking = True

    def handle_unchoke_msg(self, msg):
        self.logger.debug("{} handling UNCHOKE msg from peer".format(self.peer))
        self.am_choking = False

    def handle_have_msg(self, msg):
        self.logger.debug("{} handling HAVE msg from peer".format(self.peer))
        self.available_pieces.set(msg.piece_index)

    def handle_bitfield_msg(self, msg):
        self.logger.debug("{} handling BITFIELD msg from peer".format(self.peer))
        self.available_pieces = msg.bitfield

    def handle_piece_msg(self, msg):
        self.logger.debug("{} handling PIECE msg from peer {} {}".format(self.peer, msg.index, msg.begin))
        block_offset = msg.begin
        block = msg.block

        self.lock.acquire()
        for requested_block in self.currently_requested_blocks:
            if requested_block.piece_index == msg.index and requested_block.block_offset == msg.begin:
                requested_block.set_payload(block)
        self.lock.release()

        self.check_for_piece_completion()

    def check_for_piece_completion(self):
        if self.currently_interested_piece is None:
            return True

        for block in self.currently_interested_piece.block_list:
            if not block.is_complete():
                self.logger.debug("{} piece {} incomplete, will download the next block".format(self.peer, self.currently_interested_piece.piece_index))
                return

        self.logger.debug("{} piece {} completed".format(self.peer, self.currently_interested_piece.piece_index))
        self.data_queue.put(self.currently_interested_piece)
        self.update_state(STATE_IDLE)
        self.currently_interested_piece = None

    def send_interested_message(self):
        self.logger.debug("{} Sending INTERESTED message to peer".format(self.peer))
        msg = create_interested_message()
        self.interested = True

        try:
            self.socket.send(msg.to_bytes())
        except socket.error, e:
            self.logger.debug("{} could not send data to peer".format(self.peer))
            return

    def send_request_message(self, block):
        self.logger.debug("{} Sending REQUEST message to peer {} {}".format(self.peer, block.piece_index, block.block_offset))
        block.mark_pending()
        msg = RequestMessage(block.piece_index, block.block_offset, block.block_size)
        # self.currently_requested_block = block

        self.lock.acquire()
        self.currently_requested_blocks[block] = current_millis()
        self.lock.release()

        try:
            self.socket.send(msg.to_bytes())
        except socket.error, e:
            self.logger.debug("{} could not send data to peer".format(self.peer))
            return

    def get_next_block_to_request(self):
        if self.currently_interested_piece is None:
            return None

        try:
            for block in self.currently_interested_piece.block_list:
                if block.missing and not block.pending:
                    return block
        except:
            return None

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

            if msg is not None:
                self.handle_msg(msg)

        self.logger.debug("{} stopped receiving messages".format(self.peer))

        return

    def has_in_flight_block(self):
        return not self.currently_requested_block is None

    def request_for_blocks(self):
        while True:

            if self.is_closed():
                self.logger.debug("{} connection has already been closed, closing down sending thread to peer".format(self.peer))
                return

            if self.is_choked():
                self.send_interested_message()
                time.sleep(5)
                continue

            self.lock.acquire()
            blocks_to_expire = []
            for block in self.currently_requested_blocks:
                if self.currently_requested_blocks[block] + MAX_BLOCK_WAITING_MILLIS < current_millis():
                    block.mark_missing()
                    blocks_to_expire.append(block)
                elif block.is_complete():
                    blocks_to_expire.append(block)

            for block in blocks_to_expire:
                del self.currently_requested_blocks[block]

            if len(self.currently_requested_blocks) > MAX_BLOCK_REQUESTS_IN_FLIGHT:
                self.lock.release()
                continue

            self.lock.release()

            if not self.job_queue.empty():
                self.currently_interested_piece = self.job_queue.get()
                self.update_state(STATE_BUSY)
                self.logger.debug("{} Started working on piece {}".format(self.peer, self.currently_interested_piece.piece_index))

            if self.currently_interested_piece is None:
                time.sleep(1)
                continue

            if self.is_busy():
                block = self.get_next_block_to_request()

                if block is not None:
                    self.send_request_message(block)


