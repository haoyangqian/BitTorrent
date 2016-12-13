from bitmap import BitMap
import hashlib
import os

BLOCK_SIZE = 2**14
PIECE_SIZE = 2**19

class Block(object):
    def __init__(self,block_offset,block_size):
        self.block_offset = block_offset*BLOCK_SIZE
        #print self.block_offset
        self.block_size = block_size
        self.complete = False
    def is_complete(self):
        return self.complete

    ## set the block payload
    def set_complete(self,payload):
        self.payload = payload
        self.complete = True

    def get_info(self):
        print "-- block offset:" ,self.block_offset ,"  block size:" ,       self.block_size
    

class Piece(object):
    def __init__(self,piece_index,piece_size,fs,piece_hash):
        self.block_num = piece_size / BLOCK_SIZE
        self.block_list = []
        self.piece_index = piece_index
        self.piece_size = piece_size
        self.piece_hash = piece_hash
        for block in range(self.block_num):
            self.block_list.append(Block(block,BLOCK_SIZE))
        #if have extra smaller blocks
        if piece_size % BLOCK_SIZE != 0:
            last_block_size = piece_size % BLOCK_SIZE
            #print self.block_num,last_block_size
            self.block_list.append(Block(self.block_num,last_block_size));
            self.block_num += 1
        self.bm = BitMap(self.block_num)
        self.file = fs
        return
    
    #check block's bitmap in disk and the whole SHA1
    def is_complete(self):
        #check SHA1
        self.file.seek(self.piece_index * PIECE_SIZE)
        content = self.file.read(self.piece_size)
        piecehash = hashlib.sha1(content).digest()
        return piecehash == self.piece_hash

    def update_bitmap(self):
        for i in range(self.block_num):
            if self.block_list[i].is_complete():
                self.bm.set(i)
            else:
                self.bm.reset(i)

    def get_info(self):
        print "piece index:",self.piece_index ,"  piece size:" ,self.piece_size
        #for i in range(self.block_num):
        #    self.block_list[i].get_info()

    ## set every block
    def set_block(self,content):
        size = len(content)
        for block in self.block_list:
            #print "boffset",block.block_offset
            block.set_complete(content[block.block_offset:min(block.block_offset + BLOCK_SIZE,size)])
            
        
    ## get the content from blocks and write to file
    def write_to_file(self):
        self.update_bitmap()
        if self.bm.all():
            payload = bytearray('')
            for block in self.block_list:
                payload += block.payload
            self.file.seek(self.piece_index * PIECE_SIZE)
            self.file.write(payload)
        


class TorrentFile(object):
    def __init__(self,file_length,pieces_hash_array,piece_size,fs):
        self.pieces_num = file_length/PIECE_SIZE
        self.piece_list = []
        for piece in range(self.pieces_num):
            self.piece_list.append(Piece(piece,piece_size,fs,pieces_hash_array[piece]));
        #if have extra smaller pieces
        if file_length % PIECE_SIZE != 0:
            last_piece_size = file_length % piece_size
            self.piece_list.append(Piece(self.pieces_num,last_piece_size,fs,pieces_hash_array[self.pieces_num]));
            self.pieces_num += 1
        self.bm = BitMap(self.pieces_num)
        
    def update_bitmap(self):
         for i in range(self.pieces_num):
            if self.piece_list[i].is_complete():
                self.bm.set(i)
            else:
                self.bm.reset(i)
                    
    def is_complete(self):
         self.update_bitmap()
         return self.bm.all()

    ## return the missing pieces
    def missing_pieces(self):
        self.update_bitmap()
        missing_list = []
        for i in range(self.pieces_num):
            if not self.bm.test(i):
                missing_list.append(self.piece_list[i])
        return missing_list

    def set_piece(self,index,content):
        self.piece_list[index].set_block(content)
        self.piece_list[index].write_to_file()
        
    def get_info(self):
        for i in range(self.pieces_num):
            self.piece_list[i].get_info()


def make_test_file(filename):
    fileinfo = os.stat(filename)
    f = open(filename,"r+")
    file_length = fileinfo.st_size
    pieces_num = file_length/PIECE_SIZE
    hash_array = []
    for piece in range(pieces_num):
        f.seek(piece*PIECE_SIZE)
        content = f.read(PIECE_SIZE)
        piecehash = hashlib.sha1(content).digest()
        hash_array.append(piecehash)
    if file_length % PIECE_SIZE != 0:
        last_piece_size = file_length % PIECE_SIZE
        f.seek(pieces_num*PIECE_SIZE)
        content = f.read(last_piece_size)
        piecehash = hashlib.sha1(content).digest()
        hash_array.append(piecehash)
    f.close()
    return hash_array

def write_test_file(torrent_file,filename,index_list):
    f = open(filename,"r")
    for index in index_list:
        if index >= torrent_file.pieces_num:
            print "index of out range"
            return
        f.seek(index*PIECE_SIZE)
        content = f.read(PIECE_SIZE)
        torrent_file.set_piece(index,content)
    
    
def main():
    fileinfo = os.stat("test18.txt")
    file_length = fileinfo.st_size
    print file_length
    hash_array = make_test_file("test18.txt")
    if os.path.exists("newtest.txt"):
        fs = open("newtest.txt","rb+")
    else:
        fs = open("newtest.txt","w+")
    torrent_file = TorrentFile(file_length,hash_array,PIECE_SIZE,fs)
    #write_test_file(torrent_file,"test18.txt",range(18))
    print torrent_file.missing_pieces()

if __name__ == "__main__":
    main()
