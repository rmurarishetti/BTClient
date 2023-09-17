import hashlib
import bisect
import random

from util import BLOCK_SIZE

class Block:
    MISSING = 0
    RECEIVED = 1

    def __init__(self, piece_idx, start, size):
        self.piece_idx = piece_idx
        self.start = start
        self.size = size

        self.data = None
        self.state = Block.MISSING

class Piece:
    MISSING = 0
    REQUESTED = 1
    RECEIVED = 2

    def __init__(self, idx, piece_size, hashed):
        self.idx = idx
        self.hashed = hashed
        self.piece_size = piece_size

        self.reset()
    
    def next_block(self, endgame=False):
        bl = None
        not_requested = [block for block in self.blocks if (block.state == Block.MISSING)]
        if len(not_requested) > 0:
            
            if endgame:
                # choose a random missing block if in endgame to prevent racing on same blocks
                bl = random.choice(not_requested)
            else:
                bl = not_requested[0]
            return bl
        else:
            return bl
        
    def received_block(self, begin, data):
        idx = int(begin / BLOCK_SIZE)
        #print('Piece {} Received index {}'.format(self.idx, idx))
        self.blocks[idx].data = data
        self.blocks[idx].state = Block.RECEIVED

    def hash_match(self):
        return self.hashed == hashlib.sha1(self.get_data()).digest()
    
    def get_data(self):
        return b''.join([block.data for block in self.blocks])
    
    def complete(self):
        return all([block.state == Block.RECEIVED for block in self.blocks])
    
    def reset(self):
        last_piece_size = self.piece_size % BLOCK_SIZE
        self.blocks = [Block(self.idx, i, BLOCK_SIZE) for i in range(0, self.piece_size, BLOCK_SIZE)]
        self.blocks[-1].size = last_piece_size if last_piece_size > 0 else BLOCK_SIZE

        self.state = Piece.MISSING