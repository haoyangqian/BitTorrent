from bitmap import BitMap

BLOCK_SIZE = 2**14
PIECE_SIZE = 2**19

class Block(object):
    def __init__(self,block_offset,block_size):
        self.block_offset = block_offset*block_size
        self.block_size = block_size
        self.complete = True
    
    def is_complete(self):
        return self.complete

    def set_complete(self,complete):
        self.complete = complete

    def get_info(self):
        print "-- block offset:" ,self.block_offset ,"  block size:" ,       self.block_size
    

class Piece(object):
    def __init__(self,piece_index,piece_size):
        self.block_num = piece_size / BLOCK_SIZE
        self.block_list = []
        self.piece_index = piece_index
        self.piece_size = piece_size
        for block in range(self.block_num):
            self.block_list.append(Block(block,BLOCK_SIZE))
        #if have extra smaller blocks
        if piece_size % BLOCK_SIZE != 0:
            last_block_size = piece_size % BLOCK_SIZE
            self.block_list.append(Block(self.block_num,last_block_size));
            self.block_num += 1
        self.bm = BitMap(self.block_num)
        return
    
    #check block's bitmap and the whole SHA1
    def is_complete(self):
        self.update_bitmap()
        #check SHA1
        return self.bm.all()

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


class TorrentFile(object):
    def __init__(self,file_length,file_name,pieces_hash,piece_size):
        fs = open(file_name,'w+')
        fs.seek(file_length)
        fs.write('\0')
        self.pieces_num = file_length/PIECE_SIZE
        self.piece_list = []
        for piece in range(self.pieces_num):
            self.piece_list.append(Piece(piece,piece_size));
        #if have extra smaller pieces
        if file_length % PIECE_SIZE != 0:
            last_piece_size = file_length % piece_size
            self.piece_list.append(Piece(self.pieces_num,last_piece_size));
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

    def get_info(self):
        for i in range(self.pieces_num):
            self.piece_list[i].get_info()

def main():
    size = 34199702
    f = TorrentFile(size,PIECE_SIZE)
    f.get_info()

if __name__ == "__main__":
    main()
