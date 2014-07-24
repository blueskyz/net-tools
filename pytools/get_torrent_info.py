#!/usr/bin/env /python
# coding: utf-8

import os
import sys

import libtorrent as lt


def show_torrent_file(torrent_file):
    print torrent_file
    e =  lt.bdecode(open(torrent_file, 'rb').read())
    torrent_file = lt.torrent_info(e)
    name = torrent_file.name()
    files = torrent_file.files()
    show_content = []
    if os.name == 'nt':
        try:
            name = name.decode('utf-8').encode('gbk')
        except Exception as err:
            name = 'unknown'
        for file_item in files:
            try:
                file_item.path = \
                        file_item.path.decode('utf-8').encode('gbk')
            except Exception as err:
                pass

    show_content.append('  idx: name %s\n' % name)
    for file_item in files:
        if (file_item.size / (1024*1024.0)) > 50:
            show_content.append('       files(%.3f MB): %s\n' % 
                    (file_item.size/(1024*1024.0), file_item.path))
    show_content.append('-' * 70)
    show_content.append('\n')
    print '\n'.join(show_content)


def show_torrent_dir(torrent_dir):
    for current_dir, subdirs, torrent_files in os.walk(torrent_dir):
        for subdir in subdirs:
            show_torrent_dir(os.path.join(current_dir, subdir))
        for torrent_file in torrent_files:
            print os.path.join(current_dir, torrent_file)
            show_torrent_file(os.path.join(current_dir, torrent_file))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'argument err!'
        print 'input torrent file or directory.'
    elif os.path.isfile(sys.argv[1]):
        show_torrent_file(sys.argv[1])
    elif os.path.isdir(sys.argv[1]):
        show_torrent_dir(sys.argv[1])

