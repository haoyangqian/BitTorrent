from bencode import bencode,bdecode
from Pieces import TorrentFile
import hashlib
import os
import requests
import random
import string

PEER_ID_START = '-UT1000-'
LOCAL_PORT = 6888

class Torrent(object):
    def __init__(self,torrent_file):
        self.metainfo = self.get_torrent(torrent_file)
        self.announce_url = self.metainfo['announce']
        self.info = self.metainfo['info']
        self.comment = self.metainfo['comment']
        sha_info = hashlib.sha1(bencode(self.info))
        self.info_hash = sha_info.digest()
        self.file_length = self.file_length()
        self.left = self.file_length
        self.no_peer_id = 0
        self.compact = 1
        self.upload = 0
        self.download = 0
        self.event = "started"
        self.peer_id = self.generate_peer_id()
        self.port = LOCAL_PORT
        self.param_dict = {'info_hash':self.info_hash, 'peer_id':self.peer_id, 'port':self.port, 'left':self.left, 'compact':self.compact, 'uploaded':self.upload, 'downloaded':self.download, 'no_peer_id':self.no_peer_id, 'event':self.event}
        self.piece_length = self.info['piece length']
        self.pieces_hash = self.info['pieces']
        print self.info['pieces']
        
    def __str__(self):
        return "Torrent: announce url: %s \nfile_length: %d\ninfo_hash:%s\n" % (self.announce_url,self.file_length,self.info_hash)

    def get_torrent(self,torrent_file):
        f = open(torrent_file,'r')
        metainfo = bdecode(f.read())
        f.close()        
        return metainfo

    def get_peers(self):
        #send request to the tracker and get response
        r = self.send_request_to_tracker("started")
        #parse the response
        peer_list = self.parse_response(r)
        print peer_list

    def send_request_to_tracker(self,rtype):
        if rtype == 'started':
            self.param_dict['event'] = 'started'
            r = requests.get(self.announce_url,params=self.param_dict)
        elif rtype == 'stopped':
            self.param_dict['event'] = 'stopped'
            r = requests.get(self.announce_url,params=self.param_dict)
        elif rtype == 'completed':
            self.param_dict['event'] = 'completed'
            r = requests.get(self.announce_url,params=self.param_dict)
        return r
    
    def file_length(self):
        info = self.info
        length = 0
        #if it only contains a single file, get the file length 
        if 'length' in info:
            length = info['length']
        #else get the total length of every files 
        else:
            files = info['files']
            for fileDict in files:
                length += fileDict['length']
        return length

    #generate a peer id which contains 20 bytes
    def generate_peer_id(self):
        N = 20 - len(PEER_ID_START)
        end = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(N))
        peer_id = PEER_ID_START + end
        return peer_id
    
    #parse response from tracker, return a peer list
    def parse_response(self,r):
        response = bdecode(r.content)
        peers = response['peers']
        return self.parse_ip(peers,self.compact)
    
    #parse the peer_list, if compact == 1, every 6 bytes, first 4 is IP, last 2 is port
    def parse_ip(self,peers,compact):
        address = ''
        peer_list = []
        #parse the compact mode
        if compact == 1:
            for i,c in enumerate(peers):
                if i%6 == 4:
                    port = ord(c)*256
                elif i%6 == 5:
                    port += ord(c)
                    address += ':' + str(port)
                    peer_list.append(address)
                    address = ''
                elif i%6 == 3:
                    address += str(ord(c))
                else:
                    address += str(ord(c))+ '.'
        #parse the uncompact mode
        else:
            for p in peers:
                address = p[ip] + ':' + p[port]
                peer_list.append(address)
                address = ''
        return peer_list
    
    def connect(self,peer_list):
        return
    
    
        
def main():
    torrent = Torrent("4.torrent")
    peer_list = torrent.get_peers()
    size = 2**10*(2**10)
    f = TorrentFile(size,'1.txt',torrent.pieces_hash,2**19)
    print f.pieces_num


if __name__ == "__main__":
    main()



