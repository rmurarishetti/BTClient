import math
import os
import pyfiglet
import asyncio
import random
from tqdm import tqdm

from torrent_file import TorrentFile
from piece import Piece
import logging

class FileWriter:
    def __init__(self, torrent_file: TorrentFile):
        self.piece_size = torrent_file.piece_size
        self.num_pieces = torrent_file.num_pieces
        self.size = torrent_file.size
        self.logger = logging.getLogger(__name__)

        # Data for the pieces which each peer has
        self.peer_pieces = {}

        # The actual pieces
        self.pieces = [Piece(i, self.piece_size, torrent_file.get_piece_hash(i)) for i in range(self.num_pieces)]
        last_piece_size = self.size % self.piece_size
        self.pieces[-1].piece_size = last_piece_size if last_piece_size > 0 else self.piece_size

        # End Game status
        self.end_game = False
        # Pieces -> List of peer comms requesting this piece
        self.end_game_pieces = {}

        # Writing FD
        self.fd = os.open(torrent_file.name, os.O_WRONLY | os.O_CREAT)

        # An async, thread-safe queue
        self.data_q = asyncio.Queue()

        # Run forever
        asyncio.ensure_future(self._write())

        #progress bar
        cur, self.total = self.download_progress()
        self.count = 0
        self.progress_bar = tqdm(total=self.total, colour='green')
        

    def set_bitfield(self, peer, bitfield):
        # Converting bytes to bits
        bytes_list = [[int(x) for x in '{0:08b}'.format(byte)] for byte in bitfield]

        # Flatten
        self.peer_pieces[peer] = [i for g in bytes_list for i in g]
    
    def update_bitfield(self, peer, index):
        if peer in self.peer_pieces:
            self.peer_pieces[peer][index] = 1
        else:
            self.set_bitfield(peer, b'\0' * (int(math.ceil(self.num_pieces / 8))))
            self.peer_pieces[peer][index] = 1

    def num_peers_with_piece(self, piece):
        count = 0
        for peer in self.peer_pieces:
            if len(peer) > piece.idx and peer[piece.idx]:
                count += 1
        
        return count

    def next_piece(self, peer):
        if not peer in self.peer_pieces:
            return None
        
        # This is regular next piece
        '''
        for piece in self.pieces:
            if piece.state == Piece.MISSING and self.peer_pieces[peer][piece.idx]:
                piece.state = Piece.REQUESTED
                return piece
        '''

        # Shortcut if in endgame
        if self.end_game:
            return self.next_piece_endgame(peer)

        # This is rarest first, I think it is working
        potential_pieces = []
        min_count = 100
        cur_count = 0
        for piece in self.pieces:
            if piece.state == Piece.MISSING and self.peer_pieces[peer][piece.idx]:
                # Rarest first strategy
                cur_count = self.num_peers_with_piece(piece)
                if cur_count < min_count:
                    potential_pieces = [piece]
                    min_count = cur_count
                elif self.num_peers_with_piece(piece) == min_count:
                    potential_pieces.append(piece)
            
        if len(potential_pieces) > 0:
            ret_piece = random.choice(potential_pieces) # Return a random piece so all peers dont scramble for the same one
            ret_piece.state = Piece.REQUESTED
            # TODO: reconsider dictionary addition for entire process, perhaps do halfway through
            self.add_peer_to_dictionary(ret_piece, peer)
            return ret_piece
        elif len(potential_pieces) == 0:
            # End Game time
            custom_fig = pyfiglet.Figlet(font='slant', width=200)
            ascii_art = custom_fig.renderText('ENDGAME INITIATED')
            slant_bold_red_text = "\033[1;31m" + ascii_art + "\033[0m"
            print(slant_bold_red_text)
            self.end_game = True
            return self.next_piece_endgame(peer)

    # Randomly grabs a piece in requested or missing state while in endgame mode
    def next_piece_endgame(self, peer):
        applicable = [pieces for pieces in self.pieces if (pieces.state == Piece.MISSING or
                                                           pieces.state == Piece.REQUESTED)]
        # Randomly grab piece to avoid too many collisions
        if len(applicable) > 0:
            rand_piece = random.choice(applicable)
            self.add_peer_to_dictionary(rand_piece, peer)
            return rand_piece
        else:
            # No more pieces!
            return None

    def add_peer_to_dictionary(self, piece, peer):
        if piece in self.end_game_pieces:
            self.end_game_pieces[piece].append(peer)
        else:
            self.end_game_pieces[piece] = [peer]

    # returns a list of all pieces currently in the 'requested' state
    def requested_pieces(self, peer):
        retlist = []
        for piece in self.pieces:
            if piece.state == Piece.REQUESTED and self.peer_pieces[peer][piece.idx]:
                retlist.append(piece)
        return retlist

            
    def block_received(self, piece: Piece, begin, data, peer):
        piece.received_block(begin, data)
        if piece.complete():
            # regardless of whether the hash matches, need to CANCEL all other peers on this piece
            if self.end_game:
                ## send cancel to all but me
                self.cancel_all_but_peer(piece, peer)
                ## clear dictionary
            if piece in self.end_game_pieces:
                self.end_game_pieces.pop(piece)
            # ensure hash matches, reset if not
            if not piece.hash_match():
                logging.debug('Piece did not match hash: {}'.format(piece.idx))
                piece.reset()
                piece.state = Piece.MISSING
            else:
                logging.debug('Writing Piece with index ' + str(piece.idx))
                piece.state = Piece.RECEIVED
                self.write_piece(piece)
                self.count += 1
                if (self.count <= self.total):
                    self.progress_bar.update(1)
                
    def cancel_all_but_peer(self, piece: Piece, peer):
        if piece not in self.end_game_pieces:
            # no dictionary entry for this piece, just return
            return
        if len(self.end_game_pieces[piece]) == 1:
            # only the peer is in the list
            return
        else:
            for other_peer in self.end_game_pieces[piece]:
                if other_peer != peer:
                    # TODO: SEND CANCEL MESSAGE!
                    pass

    def download_progress(self):
        return len([piece for piece in self.pieces if piece.state == Piece.RECEIVED]), self.num_pieces

    def write_piece(self, piece: Piece):
        # Add the location and data of the piece
        self.data_q.put_nowait(((piece.idx * self.piece_size), piece.get_data()))

    async def _write(self):
        while True:
            pos, data = await self.data_q.get()

            os.lseek(self.fd, pos, 0)
            os.write(self.fd, data)
