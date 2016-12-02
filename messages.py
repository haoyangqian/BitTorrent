


class Handshake(object):
    def __init__(self,info_hash,peer_id):
        self.pstrlen = chr(19)
        self.pstr = 'BitTorrent protocol'
        self.reserved = '\x00\x00\x00\x00\x00\x00\x00\x00'
        self.info_hash = info_hash
        self.peer_id = peer_id

    def __str__(self):
        return self.pstrlen+self.pstr+self.reserved+self.info_hash+self.peer_id

    def __len__(self):
        return 49+ord(self.pstrlen)




class Message(object):
    def __init__(self):
        return


class KeepAlive(Message)

