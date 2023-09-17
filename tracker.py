import bencodepy
from torrent_file import TorrentFile
import socket
import struct
import asyncio
import re
import random
import urllib.parse as urlparser

class Tracker:
    def __init__(self, tf: TorrentFile, peerid, compact):
        self.announce_url = tf.announce
        self.info_hash = tf.info_hash
        self.size = tf.size
        self.peerid = peerid
        self.compact = compact

    async def connect(self):
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peerid,
            'compact': self.compact,
            'no_peer_id': 0,
            'event': 'started',
            'port': 6883,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.size
        }

        parsed_url = urlparser.urlparse(self.announce_url)
        url = self.announce_url + '?' + urlparser.urlencode(params)

        if parsed_url.scheme == 'http':
            f = HTTP_req(url)
            resp = await f.get_req()
            tracker_response = bencodepy.decode(resp)
            return tracker_response

        if parsed_url.scheme == 'udp':
            tracker_response = await self.connect_udp()
            return tracker_response

        
    async def peers(self):
        response = await self.connect()
        peers = response[b'peers']

        if type(peers) == list:
            peer_list = []
            for peer in peers:
                peer_list.append((peer[b'ip'], peer[b'port']))
        else:
            peer_list = [peers[i:i+6] for i in range(0, len(peers), 6)]
            return [(socket.inet_ntoa(peer[:4]), struct.unpack('>H', peer[4:])[0]) for peer in peer_list]

    async def connect_udp(self):
        tracker_url = self.announce_url
        parsed_url = urlparser.urlparse(tracker_url)
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
        info_hash = bytes(self.info_hash)
        peer_id = bytes(self.peerid)
        downloaded = 0
        left = self.size
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
        return {b'peers':remaining_data}
        


class HTTP_req:
    # initializes the HTTP_req object with an unconnected socket
    def __init__(self, url):
        # create socket to url
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.url = url
        ports = re.match(r'^.+:([0-9]+).+$', self.url)
        if ports is not None and ports.group(1) is not None:
            self.port = int(ports.group(1))
        else:
            self.port = 80
        try:
            parsed_urls = re.match(r'https?:\/\/(.*)(\/announce.*)$', self.url)
            #print(self.url)
            self.base_url = parsed_urls.group(1)
            self.announce_url = parsed_urls.group(2)
        except:
            print("INVALID URL PASSED")
            self.base_url = ""
            self.announce_url = ""
        
        # send GET request to url

    # this sends the GET request and closes the socket
    # returns a tuple with the entire request, the response code, and the data
    async def get_req(self, port=80):
        if (port == 80 and self.port != 80):
            port = self.port
        # remove port if it exists in base url
        index = self.base_url.find(":")
        if index != -1:
            stripped_base_url = self.base_url[:(index)]
        else:
            stripped_base_url = self.base_url
        #print("stripped base url: " + stripped_base_url)
        # async wait for connect
        await asyncio.get_event_loop().run_in_executor(None, self.sock.connect, (stripped_base_url, port))
        # async wait for send and response
        resp = await self.__send()
        self.sock.close()
        # check for the response code
        resp_code = int(re.match(b'^HTTP\/[0-9]+\.*[0-9]* ([0-9]+)', resp).group(1))
        #print(resp_code)
        #content = resp[resp.find(b'plain\x0d\x0a\x0d\x0a') + 9:]
        content = self.__parse_resp_for_content(resp)
        #print("------- RESPONSE --------")
        #print(b"resp is " + resp)
        #print("resp_code is " + str(resp_code))
        #print(b"content is: " + content)
        return content
    
    # look for the key which has the smallest index, then return the content
    # using that found index - needed because the order of the keys vary based 
    # on the tracker
    def __parse_resp_for_content(self, response):
        i1 = response.find(b'failure reason')
        i2 = response.find(b'warning message')
        i3 = response.find(b'interval')
        i4 = response.find(b'min interval')
        i5 = response.find(b'tracker id')
        i6 = response.find(b'complete')
        i7 = response.find(b'incomplete')
        i8 = response.find(b'peers')
        min = -1
        for i in [i1,i2,i3,i4,i5,i6,i7,i8]:
            if i != -1 and (min == -1 or i < min):
                min = i
        return response[min - 3:]

    async def __send(self):
        
        #print("ANNOUNCE URL " + self.announce_url + "\t BASE URL " + self.base_url)
        gr = b"GET " + bytes(self.announce_url, 'utf-8') + b" HTTP/1.1\r\n"
        gr += b"Host: " + bytes(self.base_url, 'utf-8') + b"\r\n"
        gr += b"Accept: */*\r\n"
        gr += b"Accept-Encoding: gzip, deflate\r\n"
        gr += b"User-Agent: Python/3.9\r\n\r\n" 
        #gr = b"GET / HTTP/1.1\r\nHost:" + bytes(self.url, 'utf-8') + b"\r\n\r\n"
        bytessent = await asyncio.get_event_loop().run_in_executor(None, self.sock.send, gr)
        #print(str(bytessent) + " bytes sent")
        response = await asyncio.get_event_loop().run_in_executor(None, self.sock.recv, 4096)
        #print("resp received")
        return response

