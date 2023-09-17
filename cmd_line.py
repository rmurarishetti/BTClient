import argparse
from random import seed

def join_parser():
    
    parser = argparse.ArgumentParser(description='Process Arguments for running the Bittorrent Client.')
    
    parser.add_argument('-t', '--torrent', type=str, help='The torrent file to be downloaded/uploaded')
    parser.add_argument('-d', '--download', action='store_true', help='Downloading or Seeding?')
    parser.add_argument('--verbose', action='store_true', help='Verbose for Debugging')
    parser.add_argument('-sp', '--seederport', type=int, help='Port Number of Seeder Instance')
    parser.add_argument('-pp', '--peerport', type=int, help='Port of Local Client Instance')
    args = parser.parse_args()

    torrent = args.torrent
    download = args.download
    verbose = args.verbose
    seederport = args.seederport
    peerport = args.peerport
    my_dict = {'torrent': torrent, 'download':download, 'verbose':verbose, 'sp':seederport, 'pp':peerport}
    return my_dict
