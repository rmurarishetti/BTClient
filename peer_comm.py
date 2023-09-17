import asyncio
import math
import struct
import traceback
import os

from file_writer import FileWriter
from piece import Piece
from torrent_file import TorrentFile
from util import BLOCK_SIZE
import logging

class Parser:
    UNKNOWN = -2
    KEEPALIVE = -1
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOTINTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8
    PORT = 9

    LENGTH_INDEX = 0
    MSG_ID_INDEX = 4
    PAYLOAD_INDEX = 5

    def __init__(self, reader):
        self.reset()
        self.reader = reader

    def reset(self):
        self.data = b''

    async def parse(self):
        ret = None
        try:
            # Reading in when there is no data
            while len(self.data) < 4:
                new_data = await self.reader.read(BLOCK_SIZE)
                if new_data:
                    self.data += new_data
            else:
                length = struct.unpack('>I', self.data[Parser.LENGTH_INDEX:Parser.MSG_ID_INDEX])[0]

                # Reading in when there is not enough data
                while len(self.data) < length:
                    new_data = await self.reader.read(BLOCK_SIZE)
                    if new_data:
                        self.data += new_data

                if length == 0:
                    ret = {'ID': Parser.KEEPALIVE}
                else:
                    msg_id = struct.unpack('>b', self.data[Parser.MSG_ID_INDEX:Parser.PAYLOAD_INDEX])[0]

                    if msg_id == Parser.CHOKE:
                        ret = {'ID': Parser.CHOKE}
                    elif msg_id == Parser.UNCHOKE:
                        ret = {'ID': Parser.UNCHOKE}
                    elif msg_id == Parser.INTERESTED:
                        ret = {'ID': Parser.INTERESTED}
                    elif msg_id == Parser.NOTINTERESTED:
                        ret = {'ID': Parser.NOTINTERESTED}
                    elif msg_id == Parser.HAVE:
                        unpacked = struct.unpack('>I', self.data[Parser.PAYLOAD_INDEX:(length-1)+Parser.PAYLOAD_INDEX])
                        ret = {'ID': Parser.HAVE, 'index': unpacked[0]}
                    elif msg_id == Parser.BITFIELD:
                        bitfield = struct.unpack('>' + str(length-1) + 's', self.data[Parser.PAYLOAD_INDEX:(length-1)+Parser.PAYLOAD_INDEX])[0]
                        ret = {'ID': Parser.BITFIELD, 'bitfield': bitfield}
                    elif msg_id == Parser.REQUEST:
                        unpacked = struct.unpack('>III', self.data[Parser.PAYLOAD_INDEX:(length-1)+Parser.PAYLOAD_INDEX])
                        ret = {'ID': Parser.REQUEST, 'index': unpacked[0], 'begin': unpacked[1], 'length': unpacked[2]}
                    elif msg_id == Parser.PIECE:
                        try:
                            unpacked = struct.unpack('>II' + str(length - 9) + 's', self.data[Parser.PAYLOAD_INDEX:(length-1)+Parser.PAYLOAD_INDEX])
                            ret = {'ID': Parser.PIECE, 'index': unpacked[0], 'begin': unpacked[1], 'block': unpacked[2]}
                        except Exception:
                            #print('Could not parse piece')
                            self.data = b''
                            return
                    if msg_id == Parser.CANCEL:
                        unpacked = struct.unpack('>I', self.data[Parser.PAYLOAD_INDEX:(length-1)+Parser.PAYLOAD_INDEX])
                        ret = {'ID': Parser.CANCEL, 'index': unpacked[0]}

                self.data = self.data[4 + length:] # Move the data buffer to the next message
                return ret
        except Exception:
            #print('Failed to retrieve data')
            print(traceback.format_exc())

class PeerComm:
    def __init__(self, file_writer: FileWriter, tf: TorrentFile, peerid, ip, port):
        self.file_writer = file_writer

        self.peerid = peerid
        self.info_hash = tf.info_hash
        self.num_pieces = tf.num_pieces

        self.ip = ip
        self.port = port

        self.choked = True
        self.interested = False
        self.in_transit = 0

        self.parser = None
        self.piece = None
        self.timeouts = 0

    async def request_next_block(self):
        # At the start, no piece
        if not self.piece:
            self.piece = self.file_writer.next_piece(self.ip)
            if not self.piece:
                return False # We are out of pieces

        block = self.piece.next_block()

        # This piece is finished, get a new one
        if not block:
            self.piece = self.file_writer.next_piece(self.ip)
            if not self.piece:
                return False # We are out of pieces
            block = self.piece.next_block()

        if not block:
            # out of pieces
            return False

        request = struct.pack('>IbIII', 13, Parser.REQUEST, self.piece.idx, block.start, block.size)
        #print('Sending Request to {}'.format(self.ip))
        self.writer.write(request)
        await self.writer.drain()

        return True
    
    # TODO: implement? cancel is used for blocks, but I would need to cancel pieces
    async def send_cancel(self):
        block = None
        request = struct.pack('>IbIII', 13, Parser.REQUEST, self.piece.idx, block.start, block.size)

    async def start(self):
        #print('Starting connection with ' + self.ip)
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port),
                timeout=10
            )
            self.parser = Parser(self.reader)
        except Exception:
            #print('Connection Failed {}'.format(self.ip))
            return

        #print('Connection Succeeded {}'.format(self.ip))
        valid = await self.handshake()
        if not valid:
            #print('Invalid handshake {}'.format(self.ip))
            return
        # else:
        #     print('Completed handshake {}'.format(self.ip))

        self.choked = True

        await self.send_interested()
        self.interested = True

        while True:
            try:
                response = await asyncio.wait_for(self.parser.parse(), timeout=5)
            except asyncio.TimeoutError:
                self.timeouts += 1
                if self.timeouts > 2:
                    if self.piece:
                        self.piece.state = Piece.MISSING
                    return # This node is bad
                else:
                    #print('Receive timed out {}'.format(self.ip))
                    response = None
                    self.parser.reset()

            if not response:
                pass
            elif response['ID'] == Parser.UNKNOWN:
                #print('Unknown message {}'.format(response['ID']))
                pass
            elif response['ID'] == Parser.KEEPALIVE:
                #print('Keep Alive')
                pass
            elif response['ID'] == Parser.CHOKE:
                #print('Choke')
                self.choked = True
            elif response['ID'] == Parser.UNCHOKE:
                #print('Unchoke {}'.format(self.ip))
                self.choked = False
            elif response['ID'] == Parser.HAVE:
                #print('Have')
                self.file_writer.update_bitfield(self.ip, response['index'])
            elif response['ID'] == Parser.BITFIELD:
                #print('Bitfield {}'.format(self.ip))
                #print(response['bitfield'])
                self.file_writer.set_bitfield(self.ip, response['bitfield'])
            elif response['ID'] == Parser.PIECE:
                #print('Piece from {}'.format(self.ip))
                self.in_transit -= 1
                self.file_writer.block_received(self.piece, response['begin'], response['block'], self.ip)

            if (not self.choked) and self.interested and self.in_transit == 0:
                self.in_transit += 1
                sent = await self.request_next_block()
                if not sent:
                    return

    async def handshake(self):
        message = struct.pack(
            '>B19s8x20s20s',
            19,
            b'BitTorrent protocol',
            self.info_hash,
            str.encode(self.peerid))
        
        self.writer.write(message)
        await self.writer.drain()

        try:
            response = await self.reader.readexactly(68)
            parts = struct.unpack('>B19s8x20s20s', response)
            return parts[2] == self.info_hash
        except Exception:
            return False

    async def send_interested(self):
        self.writer.write(struct.pack('>Ib', 1, Parser.INTERESTED))
        await self.writer.drain()

class PeerSeed:
    def __init__(self, tf: TorrentFile, peerid, port):
        self.peerid = peerid

        self.info_hash = tf.info_hash
        self.num_pieces = tf.num_pieces
        self.piece_size = tf.piece_size

        self.port = port

        self.fd = os.open(tf.name, os.O_RDONLY)
        self.logger = logging.getLogger(__name__)

    async def send_piece(self, writer, index, begin, length):
        os.lseek(self.fd, index * self.piece_size + begin, 0)
        block_bytes = os.read(self.fd, length)

        message = struct.pack('>IbII' + str(len(block_bytes)) + 's', 9 + len(block_bytes), Parser.PIECE, index, begin, block_bytes)
        logging.debug('Sending Piece')
        writer.write(message)
        await writer.drain()
    
    async def handler(self, reader, writer):
        await self.handshake(reader, writer)
        await self.send_bitfield(writer)

        interested = False

        parser = Parser(reader)
        while True:
            response = await parser.parse()

            if not response:
                pass
            elif response['ID'] == Parser.UNKNOWN:
                logging.debug('Unknown message {}'.format(response['ID']))
                pass
            elif response['ID'] == Parser.KEEPALIVE:
                logging.debug('Keep Alive')
                pass
            elif response['ID'] == Parser.INTERESTED:
                logging.debug('Interested')
                interested = True
                await self.unchoke(writer)
            elif response['ID'] == Parser.NOTINTERESTED:
                logging.debug('Not Interested')
                interested = False
            elif response['ID'] == Parser.REQUEST:
                logging.debug('Request')
                await self.send_piece(writer, response['index'], response['begin'], response['length'])

    async def start(self):
        print('Starting connection on port {}'.format(self.port))
        server = await asyncio.start_server(self.handler, '127.0.0.1', self.port)
        async with server:
            await server.serve_forever()

    async def handshake(self, reader, writer):
        try:
            request = await reader.readexactly(68)
            parts = struct.unpack('>B19s8x20s20s', request)
            if parts[2] != self.info_hash:
                return False
        except Exception:
            return False

        message = struct.pack(
            '>B19s8x20s20s',
            19,
            b'BitTorrent protocol',
            self.info_hash,
            str.encode(self.peerid)
        )
        
        writer.write(message)
        await writer.drain()

    async def unchoke(self, writer):
        logging.debug('Sending unchoke')
        writer.write(struct.pack('>Ib', 1, Parser.UNCHOKE))
        await writer.drain()

    async def send_bitfield(self, writer):
        # Pack a 1 for each piece
        length = int(math.ceil(self.num_pieces/8))
        message = struct.pack('>Ib' + str(length) + 's', length + 1, Parser.BITFIELD, b'\xff' * length)
        writer.write(message)
        await writer.drain()
