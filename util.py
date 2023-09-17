BLOCK_SIZE = 2**14


import socket
import struct
import random
import asyncio
from urllib.parse import urlencode ,urlparse

async def connect_udp():
        tracker_url = 'udp://tracker.opentrackr.org:1337/announce'
        parsed_url = urlparse(tracker_url)
        netloc_str = parsed_url.netloc
        hostname, port = netloc_str.split(':')
        port = int(port)
        tracker_address = (socket.gethostbyname(hostname), port)
        
        PROTOCOL_ID = 0x41727101980
        INITIAL_TRANSACTION_ID = random.randint(-(1 << 31), (1 << 31) - 1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 0))
        connection_request = struct.pack("!qii", PROTOCOL_ID, 0, INITIAL_TRANSACTION_ID)
        
        await asyncio.get_event_loop().run_in_executor(None, sock.sendto,connection_request,tracker_address)
        response = await asyncio.get_event_loop().run_in_executor(None, sock.recv, 4096)
        first_int, second_int = struct.unpack('!ii', response[:8])
        third_int, = struct.unpack('!q', response[8:16])
 
        if second_int != INITIAL_TRANSACTION_ID:
         print('wrong address')
         exit(1)
        
        connection_id = third_int
        action = 1
        transaction_id = second_int
        info_hash = b'066aa48adef581adb53d06a7653904985714995e'
        peer_id = b'-MYTEST1234567890'
        downloaded = 0
        left = 1000
        uploaded = 0
        event = 2
        ip = 0
        key = 0
        num_want = -1
        port = sock.getsockname()[1]
        port_signed = port if port <= 32767 else port - 65536
        extensions = 0
        packed_data = struct.pack("!qii20s20sqqqiiiihh", connection_id, action, transaction_id, info_hash, peer_id, downloaded, left, uploaded, event, ip, key, num_want, port_signed, extensions)
        await asyncio.get_event_loop().run_in_executor(None, sock.sendto,packed_data,tracker_address)
        response = await asyncio.get_event_loop().run_in_executor(None, sock.recv, 4096)
        action, transaction_id, interval, leechers, seeders = struct.unpack('>iiiII', response[:20])
        if transaction_id != INITIAL_TRANSACTION_ID:
         print('wrong address')
         exit(1)
        bytes_remaining = leechers * 6  # each peer has a 6-byte identifier
        remaining_data = response[20:20+bytes_remaining]
        num_peers = leechers

# loop through the peers data to extract IP addresses and port numbers
        peers = []
        for i in range(num_peers):
            offset = i * 6
            ip_bytes = remaining_data[offset:offset+4]
            port_bytes = remaining_data[offset+4:offset+6]
            ip = ".".join(str(b) for b in ip_bytes)
            port = struct.unpack(">H", port_bytes)[0]
            peers.append((ip, port))
        return peers
        
         
        
        
        
        
        
asyncio.run(connect_udp())

        