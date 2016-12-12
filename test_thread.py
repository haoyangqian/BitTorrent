from bitmap import BitMap
import threading
import time
import Queue

threadList = ["Thread-1", "Thread-2", "Thread-3"]
nameList = ["One", [2,3,4], "Three", 4, "Five"]
pieces_queue_list = []
data_queue_list = []

    


class myThread (threading.Thread):
    def __init__(self, threadID, name, q1 , q2):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q1
        self.q2 = q2
    def run(self):
        print "Starting " + self.name + "\n"
        download_data(self.name, self.q,self.q2)
        print "Exiting " + self.name +"\n"

def download_data(threadName, q, q2):
        while not q.empty():
            data = q.get()
            print "%s download %s\n" % (threadName, data)
            q2.put({'index':data,'data':data})

def test_thread():
    global exitFlag
    exitFlag = 0
    threads = []
    threadID = 1
    print "Starting Main Thread"
     # Fill the queue
    for i in range(3):
        queue = Queue.Queue(4)
        for j in range(4):
            queue.put(i*4 + j)
        pieces_queue_list.append(queue)

    for i in range(3):
        queue = Queue.Queue(4)
        data_queue_list.append(queue)
        
    for i , tName in enumerate(threadList):
        thread = myThread(threadID, tName, pieces_queue_list[i],data_queue_list[i])
        thread.start()
        threads.append(thread)
        threadID += 1

    # Wait for all threads to complete
    for t in threads:
        t.join()
    print "Exiting Main Thread"
    
    bm = BitMap(12)
    while 1:
        if bm.all():
            print "receive all the pieces!!"
            break
        for q in data_queue_list:
            if not q.empty():
                item = q.get()
                data = item['data']
                index = item['index']
                print "receive pieces:%s data:%s\n" % (data,data)
                bm.set(index)
                
def test_file():
    f = open('1.txt','r')
    for i in range(3):
        f.seek(5)
        print f.read(5)

class piece(object):
    def __init__(self,a,b):
        self.a = a
        self.b = b
    
def test_in():
    piece_list = []
    a = piece(1,1)
    b = piece(2,2)
    piece_list.append(a)
    piece_list.append(b)
    a.a = 2
    if a in piece_list:
        print "yes"
    
def main():
    #torrent = Torrent("4.torrent")
    #print torrent.torrent_file.is_complete()
    test_in()    

if __name__ == "__main__":
    main()
