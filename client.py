import asyncio
import random

from torrent_file import TorrentFile
from tracker import Tracker
from file_writer import FileWriter
from peer_comm import PeerComm, PeerSeed

class Client:
    def __init__(self, seederport=None, peerport=None):
        #print('Todo')
        self.seederport = seederport
        self.peerport = peerport
        pass

    def generate_peerid(self):
        return 'VTRK' + ''.join([str(random.randrange(10)) for _ in range(16)])

    def find_peers(self, tf: TorrentFile, peerid):
        tracker = Tracker(tf, peerid, 1)
        return tracker.peers()

    async def download_file(self, torrent_filename):
        tf = TorrentFile(torrent_filename)
        
        fw = FileWriter(tf)
        peerid = self.generate_peerid()

        peers = await self.find_peers(tf, peerid)
        peers += [('127.0.0.1', self.peerport)]
        peer_comms = [PeerComm(fw, tf, peerid, ip, port) for ip, port in peers]
        peer_seed = PeerSeed(tf, peerid, self.seederport)
        await asyncio.gather(*([pc.start() for pc in peer_comms] + [peer_seed.start()]))


    def download_progress(self):
        return self.fw.download_progress() if self.fw else 0

    async def seed_file(self, torrent_filename):
        tf = TorrentFile(torrent_filename)
        peerid = self.generate_peerid()

        peer_seed = PeerSeed(tf, peerid, 4000)

        await peer_seed.start()