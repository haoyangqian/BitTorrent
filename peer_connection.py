import socket
import message

class PeerConnection(Object):

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

        s = socket.socket()
        s.connect((host, port))

        return s


    def handshake(self):




    def download_piece(self)



