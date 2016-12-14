from bencode import bencode,bdecode
from Pieces import TorrentFile
import hashlib
from os import path, mkdir
import requests
import random
import string
import threading
import time
import Queue
from peer_connection import PeerConnection
from bitmap import BitMap
import logging

format = '%(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=format)

PEER_ID_START = '-UT1000-'
LOCAL_PORT = 6888

class Torrent(object):
    def __init__(self,torrent_file):
        ##
        self.metainfo = self.get_torrent(torrent_file)
        self.announce_url = self.metainfo['announce']
        self.info = self.metainfo['info']
        self.comment = self.metainfo['comment']
        self.file_list = self.info['files']
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
        ## construct param dict
        self.param_dict = {'info_hash':self.info_hash, 'peer_id':self.peer_id, 'port':self.port, 'left':self.left, 'compact':self.compact, 'uploaded':self.upload, 'downloaded':self.download, 'no_peer_id':self.no_peer_id, 'event':self.event}
        ## get pieces info
        self.piece_length = self.info['piece length']
        self.pieces_hash = self.info['pieces']
        self.pieces_hash_array = self.get_pieces_hash(self.pieces_hash)
        ## set folder_name directory
        if 'name' in self.info:
            self.folder_name = self.info['name']
        else:
            self.folder_name = 'temp'
        ## set up tmp tile
        self.tmp_file = self.setup_temp_file()
        ## get peer_list
        self.peer_list = self.get_peers()
        ## get torrent_file
        self.torrent_file = TorrentFile(self.file_length,self.pieces_hash_array,self.piece_length,self.tmp_file)

    def __str__(self):
        return "Torrent: announce url: %s \nfile_length: %d\ninfo_hash:%s\n" % (self.announce_url,self.file_length,self.info_hash)

    def get_pieces_hash(self,pieces_hash):
        pieces_array = []
        while len(pieces_hash) > 0:
            pieces_array.append(pieces_hash[0:20])
            pieces_hash = pieces_hash[20:]
        return pieces_array

    def get_torrent(self,torrent_file):
        f = open(torrent_file,'r')
        metainfo = bdecode(f.read())
        f.close()
        return metainfo

    def get_peers(self):
        #send request to the tracker and get response
        r = self.send_request_to_tracker("started")
        #parse the response
        return self.parse_response(r)

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

    def connect(self):
        print self.peer_list

        connected_peers = []
        for peer in self.peer_list:
            # if peer == "167.88.114.173:6881":
            peer_connection = PeerConnection(self.peer_id,
                                             peer,
                                             self.info_hash)

            # if peer_connection.is_connected():
            connected_peers.append(peer_connection)
            peer_connection.run()

        print len(connected_peers), "peer(s) connected"

        return connected_peers

    ## setup a temp file if not exist, otherwise open it
    def setup_temp_file(self):
        self.folder_directory = self.folder_name.rsplit('.',1)[0]
        self.temp_file_path = path.join(self.folder_directory, self.folder_name + '.tmp')
        if not path.exists(self.temp_file_path):
            if not path.exists(self.folder_directory):
                mkdir(self.folder_directory)
            open(self.temp_file_path, 'w+').close()
        tempfile = open(self.temp_file_path, 'rb+')
        return tempfile



    def cut_files(self):
        #if not self.torrent_file.is_complete():
        #    print "file not complete!"
        #    return
        index = 0
        for f in self.file_list:
            new_file_name = path.join(self.folder_directory,f['path'][0])
            fs = open(new_file_name,'w+')
            length = f['length']
            self.tmp_file.seek(index)
            content = self.tmp_file.read(length)
            fs.write(content)
            index += length

    def downloadfile(self):
        connection_list = self.connect()
        pieces_in_flight = []
        while 1:
            if self.torrent_file.is_complete():
                print "all pieces have been received"

                for connection in connection_list:
                    print "closing conenction", connection.peer
                    connection.close()

                break
            missing_pieces = self.torrent_file.missing_pieces()
            for connection in connection_list:
                if connection.is_closed():
                    connection_list.remove(connection)
                    continue

                if connection.can_make_request():
                    # print connection.peer, "can make a request"
                    ##check queue, if have piece available, get it and write to file
                    ##remove it from the pieces_in_flight list
                    if not connection.data_queue.empty():
                        returnpiece = connection.data_queue.get()
                        returnpiece.write_to_file()

                        if returnpiece.is_complete():
                            pieces_in_flight.remove(returnpiece)
                            missing_pieces.remove(returnpiece)
                            print "retrived a completed piece from peer", connection.peer, returnpiece.piece_index
                            print len(missing_pieces), "pieces left to download"
                        else:
                            print "received a bad block from peer", connection.peer, returnpiece.piece_index
                            print returnpiece.piece_size, returnpiece.written_piece_hash(), returnpiece.piece_hash

                    # print missing_pieces

                    ##allocate download mission
                    for piece in missing_pieces:
                        if piece not in pieces_in_flight and connection.can_request_piece(piece):
                            print "asking peer", connection.peer, "to download piece", piece.piece_index
                            connection.download_piece(piece)
                            pieces_in_flight.append(piece)

                            print "################ Missing piece queue size", len(missing_pieces)
                            break

def main():

    start = time.time()
    t = Torrent("1.torrent")
    t.downloadfile()
    t.cut_files()
    #t.downloadfile()
    #print torrent.torrent_file.is_complete()

    end = time.time()

    print "total time", end - start
    print t.torrent_file.is_complete()
    return


if __name__ == "__main__":
    main()
