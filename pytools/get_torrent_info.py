#!/usr/bin/env /python
# coding: utf-8

import os
import sys

import libtorrent as lt


if __name__ == '__main__':
    print sys.argv[1]
    e =  lt.bdecode(open(sys.argv[1], 'rb').read())
    torrent_file = lt.torrent_info(e)
    name = torrent_file.name()
    files = torrent_file.files()
    show_content = []
    if os.name == 'nt':
        name = name.decode('utf-8')
        files = [item.decode('utf-8') for item in files]

    show_content.append('  idx: name %s\n' % name)
    for file_item in files:
        show_content.append('       files(%.3f MB): %s\n' % 
                (file_item.size/(1024*1024.0), file_item.path))
    print '\n'.join(show_content)
