from prettytable import PrettyTable
from torrent import Torrent

torrent_list = []
mix = PrettyTable()
mix.field_names = ["id", "name","done","files","peers","down(KB)"]


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
                        mix.add_row([len(torrent_list),t.backing_file,t.complete,len(t.file_list),len(t.peer_list),1295])
                        torrent_list.append(t)
                    except:
                        print "exception when create torrent"

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
 
                print mix
                                
        elif cmd_type == "close":
            print "All Modules have been destroyed, shutting down"
            exit(1)
        elif cmd_type == "":
            continue
        else:
            print "Invalid command. Try 'help'"

if __name__ == "__main__":
    main()
