from bitmap import BitMap
import hashlib

BLOCK_SIZE = 2**14
PIECE_SIZE = 2**19

class Block(object):
    def __init__(self, piece_index, block_offset, block_size):

        self.missing = True
        self.pending = False

        self.piece_index = piece_index
        self.block_offset = block_offset * block_size
        self.block_size = block_size
        self.payload = None

    def is_complete(self):
        return self.payload == None

    def get_info(self):
        print "-- block offset:" ,self.block_offset ,"  block size:" ,       self.block_size

    def mark_pending(self):
        self.pending = True

    def set_payload(self, payload):
        self.missing = False
        self.pending = False
        self.payload = payload

class Piece(object):
    def __init__(self,piece_index,piece_size,fs,piece_hash):
        self.block_num = piece_size / BLOCK_SIZE
        self.block_list = dict()
        self.piece_index = piece_index
        self.piece_size = piece_size
        self.piece_hash = piece_hash
        for block in range(self.block_num):
            b = Block(piece_index, block, BLOCK_SIZE)
            self.block_list[b.block_offset] = b
        #if have extra smaller blocks
        if piece_size % BLOCK_SIZE != 0:
            last_block_size = piece_size % BLOCK_SIZE
            b = Block(piece_index, self.block_num, last_block_size)
            self.block_list[b.block_offset] = b
            self.block_num += 1
        self.bm = BitMap(self.block_num)
        self.file = fs
        return

    #check block's bitmap and the whole SHA1
    def is_complete(self):
        self.update_bitmap()
        #check SHA1
        self.file.seek(self.piece_index * self.piece_size)
        content = self.file.read(self.piece_size)
        piecehash = hashlib.sha1(content).digest()
        return self.bm.all() and piecehash == self.piece_hash

    def update_bitmap(self):
        for i in self.block_list:
            if self.block_list[i].is_complete():
                self.bm.set(i)
            else:
                self.bm.reset(i)

    def get_info(self):
        print "piece index:",self.piece_index ,"  piece size:" ,self.piece_size
        #for i in range(self.block_num):
        #    self.block_list[i].get_info()


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
         # self.update_bitmap()
         return self.bm.all()

    def missing_pieces(self):
        self.update_bitmap()
        missing_list = []
        for i in range(self.pieces_num):
            if not bm.test(i):
                missing_list.append(i)
        return missing_list

    def get_info(self):
        for i in range(self.pieces_num):
            self.piece_list[i].get_info()

def main():
    size = 34199702
    f = TorrentFile(size,PIECE_SIZE)
    f.get_info()

if __name__ == "__main__":
    main()
