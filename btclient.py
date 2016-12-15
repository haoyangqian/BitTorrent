from prettytable import PrettyTable
from torrent import Torrent
from threading import Thread
import time
import logging

torrent_list = []
mix = PrettyTable()
mix.field_names = ["id", "name","done","pieces","files","peers","speed(KB/s)", "duration(s)"]

logging.basicConfig(level=logging.INFO, format=format)

def main():
    print "BitTorrent Client started"
    while 1:
        n = raw_input('>')
        command = n.split(' ')
        cmd_type = command[0]
        if cmd_type == "help":
            print "help"
        elif cmd_type == "torrent":
            if len(command) == 1:
                print "Invalid command, try 'torrent help'"
                continue
            torrent_type = command[1]
            if torrent_type == "add":
                if len(command) != 4:
                    print "torrent add <torrent> <backingfile>"
                else:
                    try:
                        torrent_file = command[2]
                        backing_file = command[3]
                        t = Torrent(torrent_file,backing_file)

                        torrent_list.append(t)

                        download_thread = Thread(target=start_download, args=(t,))
                        download_thread.start()
                        # download_thread.join()
                    except Exception as e:
                        print "exception when create torrent", e

            if torrent_type == "remove":
                if len(command) != 3:
                    print "torrent remove <torrentid>"
                torrent_id = command[2]
                try:
                    mix.del_row(int(torrent_id))
                    del torrent_list[int(torrent_id)]
                except:
                    print "wrong torrent_id"
            if torrent_type == "list":
                mix.clear_rows()
                index = 0
                for t in torrent_list:
                    complete = t.complete_pieces()
                    complete_current = t.complete_pieces_current_run()
                    #print "complete is {}, complete_current is {}".format(complete, complete_current)
                    total = t.total_pieces()

                    pieces = "{}/{} ({:0.2f}%)".format(complete, total, float(complete) / total * 100)

                    speed = "0" if t.complete else "{:0.2f}".format(complete_current * (2 ** 19) / 1024 / (time.time() - t.start_time))

                    duration = "{:0.2f}".format(time.time() - t.start_time)

                    mix.add_row([index,t.backing_file,t.complete,pieces,len(t.file_list),len(t.connection_list),speed, duration])
                    index = index + 1
                print mix

        elif cmd_type == "close":
            print "All Modules have been destroyed, shutting down"
            exit(1)
        elif cmd_type == "":
            continue
        else:
            print "Invalid command. Try 'help'"


def start_download(torrent):
    torrent.downloadfile()
    torrent.cut_files()
    return

if __name__ == "__main__":
    main()
