import asyncio
from os import WIFEXITED
from cmd_line import join_parser
import pyfiglet
from torrent_file import TorrentFile
from file_writer import FileWriter
from tracker import Tracker
from peer_comm import PeerComm
from client import Client
import logging_config

async def test():
    t = TorrentFile('debian-11.6.0-amd64-netinst.iso.torrent')
    tracker = Tracker(t, 'AB081927503733839118', 1)
    peers = await tracker.peers()
    print(peers)

if __name__ == '__main__':
    

    returned_dict = join_parser()
    
    client = Client(returned_dict['sp'], returned_dict['pp'])

    if returned_dict['download']:
        result = pyfiglet.figlet_format("BTClient Downloader", font="slant", width=200)
        print(result)
        if returned_dict['verbose']:
            logging_config.setup_logging(True)
            
        asyncio.run(client.download_file(returned_dict['torrent']))

    else:
        result = pyfiglet.figlet_format("BTClient Seeder", font="slant", width=200)
        print(result)
        asyncio.run(client.seed_file(returned_dict['torrent']))