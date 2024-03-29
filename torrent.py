from bencode import bencode,bdecode
from Pieces import TorrentFile
import hashlib
from os import path, mkdir, sys
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

MAX_PIECE_IN_FLIGHT_SECOND = 30

class Torrent(object):
    def __init__(self,torrent_file,backing_file):
        self.logger = logging.getLogger(__name__)

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
        self.backing_file = backing_file
        ## set up tmp tile
        self.tmp_file = self.setup_temp_file(backing_file)
        ## get peer_list
        self.peer_list = self.get_peers()
        ## get torrent_file
        self.torrent_file = TorrentFile(self.file_length,self.pieces_hash_array,self.piece_length,self.tmp_file)
        self.complete = False

        self.start_time = time.time()
        self.previous_completed_pieces = self.torrent_file.bm.count()
        self.connection_list = []


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
        # print self.peer_list

        connected_peers = []
        for peer in self.peer_list:
            peer_connection = PeerConnection(self.peer_id,
                                             peer,
                                             self.info_hash)

            if peer_connection.is_connected():
                connected_peers.append(peer_connection)
                peer_connection.run()

        logging.debug("{} peer(s) connected for".format(len(connected_peers)))

        return connected_peers

    ## setup a temp file if not exist, otherwise open it
    def setup_temp_file(self,backing_file):
        self.temp_file_path = path.join(backing_file, self.folder_name + '.tmp')
        #print backing_file
        #print self.temp_file_path
        if not path.exists(self.temp_file_path):
            if not path.exists(backing_file):
                mkdir(backing_file)
            open(self.temp_file_path, 'w+').close()
        tempfile = open(self.temp_file_path, 'rb+')
        return tempfile

    def get_start_time(self):
        return self.start_time

    def cut_files(self):
        #if not self.torrent_file.is_complete():
        #    print "file not complete!"
        #    return
        index = 0
        for f in self.file_list:
            new_file_name = path.join(self.backing_file,f['path'][0])
            fs = open(new_file_name,'w+')
            length = f['length']
            self.tmp_file.seek(index)
            content = self.tmp_file.read(length)
            fs.write(content)
            index += length

        self.complete = True

    def complete_pieces(self):
        return self.torrent_file.pieces_num - len(self.torrent_file.missing_pieces())

    def complete_pieces_current_run(self):
        return self.torrent_file.bm.count() - self.previous_completed_pieces

    def total_pieces(self):
        return self.torrent_file.pieces_num

    def downloadfile(self):
        self.connection_list = self.connect()
        pieces_in_flight = {}
        piece_to_peer = {}

        self.start_time = time.time()
        missing_pieces = self.torrent_file.missing_pieces()
        while 1:
            if len(missing_pieces) == 0:
                # print "bitmap:",self.torrent_file.bm.tostring()
                # print "bm count:",self.torrent_file.bm.count()
                # print "bm size:",self.torrent_file.bm.size()
                # print "num pieces:",self.torrent_file.pieces_num
                # print "missing piece:",len(missing_pieces)
                logging.debug("All pieces have been received")

                for connection in self.connection_list:
                    logging.debug("Closing connection to peer {}".format(connection.peer))
                    connection.close()

                break

            missing_pieces = self.torrent_file.missing_pieces()
            connections_to_remove = []
            pieces_to_expire = []
            for piece in pieces_in_flight:
                if pieces_in_flight[piece] + MAX_PIECE_IN_FLIGHT_SECOND < time.time():
                    pieces_to_expire.append(piece)
                    self.logger.debug("Expiring piece {}".format(piece.piece_index))

            for piece in pieces_to_expire:
                del pieces_in_flight[piece]
                piece.expire()
                piece_to_peer[piece].reset()

            for connection in self.connection_list:
                if connection.is_closed():
                    connections_to_remove.append(connection)
                    continue

                if not connection.data_queue.empty():
                    # print connection.peer, "can make a request"
                    ##check queue, if have piece available, get it and write to file
                    ##remove it from the pieces_in_flight list
                    returnpiece = connection.data_queue.get()
                    returnpiece.write_to_file()
                    returnpiece.clear_data()

                    if returnpiece.is_complete():
                        if returnpiece in pieces_in_flight:
                            del pieces_in_flight[returnpiece]

                        if returnpiece in missing_pieces:
                            missing_pieces.remove(returnpiece)
                        print "Torrent file {} downloaded piece {} from peer {}".format(self.folder_name, returnpiece.piece_index, connection.peer)
                        logging.debug("{} pieces left to download".format(len(missing_pieces)))

                    else:
                        logging.debug("received a bad block from peer {} {}, closing connection to peer".format(connection.peer, returnpiece.piece_index))
                        for block in returnpiece.block_list:
                            block.mark_missing()

                        connection.close()
                        # print returnpiece.piece_size, returnpiece.written_piece_hash(), returnpiece.piece_hash

                if connection.can_make_request():
                        # print missing_pieces

                    ##allocate download mission
                    for piece in missing_pieces:
                        in_flight = piece in pieces_in_flight
                        can_request = connection.can_request_piece(piece)

                        if piece not in pieces_in_flight and connection.can_request_piece(piece):
                            logging.debug("Asking peer {} to download piece {}".format(connection.peer, piece.piece_index))
                            # print "Asking peer {} to download piece {}".format(connection.peer, piece.piece_index)
                            connection.download_piece(piece)
                            pieces_in_flight[piece] = time.time()
                            piece_to_peer[piece] = connection
                            logging.debug("Missing piece queue size {}".format(len(missing_pieces)))
                            break
                    # print "cannot distribute piece"
                    # print "in flight {} can_request {}".format(in_flight, can_request)
                    # print "{} pieces in flight, {} missing pieces".format(len(pieces_in_flight), len(missing_pieces))
                    # print "@1 choke {} busy {} choke {}".format(connection.is_closed(), connection.is_busy(), connection.is_choked())
                # else:
                    # print "cannot make request"
                    # print "@2 choke {} busy {} choke {}".format(connection.is_closed(), connection.is_busy(), connection.is_choked())


            for remove in connections_to_remove:
                self.connection_list.remove(remove)

                if len(self.connection_list) == 0:
                    print "Torrent {} has no more active peer".format(self.folder_name)
                    sys.exit(-1)



        end_time = time.time()
        print "Torrent file {} completed in {} seconds".format(self.folder_name, end_time - self.start_time)

def main():

    start = time.time()
    t = Torrent("4.torrent")
    t.downloadfile()
    t.cut_files()
    #t.downloadfile()
    #print torrent.torrent_file.is_complete()

    end = time.time()

    print "total time", end - start
    print t.torrent_file.is_complete()
    sys.exit(0)


if __name__ == "__main__":
    main()
