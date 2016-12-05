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
        peer = self.peer_list[2]

        peer_connection = PeerConnection(self.generate_peer_id(),
                                         peer,
                                         self.info_hash,
                                         Queue(),
                                         Queue())

        peer_connection.handshake()

        return


    def setup_temp_file(self):
        self.folder_directory = self.folder_name.rsplit('.',1)[0]
        self.temp_file_path = path.join(self.folder_directory, self.folder_name + '.tmp')
        if path.exists(self.temp_file_path):
            open(self.temp_file_path, 'w').close()
        else:
            mkdir(self.folder_directory)
        tempfile = open(self.temp_file_path, 'wb+')
        return tempfile

    def download(self):
        ## check bitmap in
        ## connection_list = connect(self.peer_list)
        #while 1:
            #checkbitmap
        return
    

threadList = ["Thread-1", "Thread-2", "Thread-3"]
nameList = ["One", [2,3,4], "Three", 4, "Five"]
queueLock = threading.Lock()
pieces_queue = Queue.Queue(10)
data_queue = Queue.Queue(1)

class myThread (threading.Thread):
    def __init__(self, threadID, name, q1 , q2):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q1
        self.q2 = q2
    def run(self):
        print "Starting " + self.name + "\n"
        download_data(self.name, self.q)
        print "Exiting " + self.name +"\n"

def download_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not q.empty():
            data = q.get()
            queueLock.release()
            print "%s download %s\n" % (threadName, data)
        else:
            queueLock.release()
        time.sleep(1)

def main():
    #torrent = Torrent("4.torrent")
    #print torrent.torrent_file.is_complete()
    global exitFlag
    exitFlag = 0
    threads = []
    threadID = 1
    for tName in threadList:
        thread = myThread(threadID, tName, pieces_queue,data_queue)
        thread.start()
        threads.append(thread)
        threadID += 1

    # Fill the queue
    queueLock.acquire()
    for word in nameList:
        pieces_queue.put(word)
    queueLock.release()

    # Wait for queue to empty
    while not pieces_queue.empty():
        pass
    
    # Notify threads it's time to exit
    exitFlag = 1

    # Wait for all threads to complete
    for t in threads:
        t.join()
    print "Exiting Main Thread"
    

if __name__ == "__main__":
    main()
