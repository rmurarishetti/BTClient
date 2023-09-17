import hashlib
import math

import bencodepy

SHA_SIZE = 20

class TorrentFile(object):
    def __init__(self, path_to_torrent):
        # Read the torrent file
        with open(path_to_torrent, 'rb') as f:
            torrent_file = bencodepy.decode(f.read())
            
            # Announce URL
            self.announce = torrent_file[b'announce'].decode('utf-8')

            # Info hash
            self.info_hash = hashlib.sha1(bencodepy.encode(torrent_file[b'info'])).digest()

            # Size
            if b'length' in torrent_file[b'info']:
                self.size = int(torrent_file[b'info'][b'length'])
                
                self.name = torrent_file[b'info'][b'name'].decode('utf-8')
            else:
                self.size = sum([int(x[b'length']) for x in torrent_file[b'info'][b'files']])

            # Piece Length
            self.piece_size = torrent_file[b'info'][b'piece length']

            # Number of pieces
            self.num_pieces = math.ceil(self.size / self.piece_size)

            # Pieces Hashed
            self._pieces_hash = [torrent_file[b'info'][b'pieces'][i * SHA_SIZE: (i * SHA_SIZE) + SHA_SIZE] 
                                for i in range(self.num_pieces)]
            
            
    def get_piece_hash(self, idx):
        return self._pieces_hash[idx]