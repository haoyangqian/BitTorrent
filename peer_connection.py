import socket
from messages import *

class PeerConnection(object):

    def __init__(self, self_peer_id, peer, info_hash, pieces_queue, data_queue):
        self.self_peer_id = self_peer_id
        self.pieces_queue = pieces_queue
        self.data_queue = data_queue
        self.info_hash = info_hash

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.socket = self.establish_connection(peer)

    def establish_connection(self, peer):
        tokens = peer.split(":")
        host = tokens[0]
        port = int(tokens[1])


        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print host, port
        s.connect((host, port))
        print "connected"
        # print s.getpeername
        return s


    def handshake(self):
        m = create_hanshake_message(self.info_hash, self.self_peer_id)

        self.socket.send(str(m))
        payload = self.socket.recv(1024)
        handshake_response = create_handshake_message_from_payload(payload)
        print handshake_response
        print handshake_response.info_hash
        print self.info_hash
        return


    def download_piece(self):
        return



