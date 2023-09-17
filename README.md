
## 🚀 BitTorrent Protocol

BitTorrent is a peer-to-peer (P2P) file sharing protocol that allows users to distribute data and electronic files over the Internet in a decentralized manner. BitTorrent is one of the most popular protocols for transferring large files, such as digital video files containing TV shows and video clips, or digital audio files containing songs.

BitTorrent works by dividing a file into small pieces called chunks. Each user who is downloading the file downloads a different set of chunks. Once a user has downloaded all of the chunks for a file, they can then stitch the chunks back together to create the complete file.

BitTorrent uses a central server called a tracker to coordinate the download process. The tracker keeps track of which users have which chunks of the file. When a new user joins the download, the tracker tells them which other users have the chunks that they need.

Once a user has downloaded a file, they can then choose to seed the file. This means that they keep the file open and allow other users to download chunks from them. The more users who are seeding a file, the faster it can be downloaded by other users.

## BitTorrent Client

A BitTorrent client is a computer program that implements the BitTorrent protocol. BitTorrent clients are available for a variety of computing platforms and operating systems. Some popular BitTorrent clients include:

μTorrent
qBittorrent
Deluge
Vuze
Transmission
To use a BitTorrent client, you first need to find a torrent file for the file that you want to download. Torrent files contain information about the file that you want to download, such as its name, size, and hash. Once you have found a torrent file, you can open it in your BitTorrent client to start the download process.

BitTorrent clients are very efficient at transferring large files. They are able to do this by using a number of techniques, such as:

Chunking: BitTorrent divides files into small pieces called chunks. This makes it easier to download the file from multiple users simultaneously.
Seeding: BitTorrent users who have already downloaded a file can choose to seed the file. This makes the file available to other users to download.
Pipelining: BitTorrent clients can download multiple chunks of a file simultaneously. This speeds up the download process.

## Running this project:

#### Requirements
Run `pip install -r requirements.txt` to grab all dependencies

The client can be run by using the following command:
```
	python main.py [options] [-t torrent file] [-d][-sp port][-pp port] [--verbose]
```

We have 3 arguments/options to specify when the main command is run:

* -t \<torrent file>: specified the torrent file path that we’ll be using to seed or download.
* -d: specifies the option to download a file using a torrent, rather the lack of specifies that the file which the torrent file points to will be seeded.
* --verbose is used to enable verbose for debugging and tracking the status of the client.
* -sp \<port>: specifies the port for the client to seed while downloading
* -p \<port>: specified the port for a peer client instance to download the file from

An example usage of the command to download a file called torrentfile.txt with no verbose would be:
```
python main.py -t torrentfile.txt.torrent -d -sp 6942 -pp 7190
```
