#!/usr/bin/env python
# coding: utf-8

import libtorrent as lt
import time
import os


class SimpleDownloader(object):
    '''
    一个简单的 bt 下载工具，依赖开源库 libtorrent.
    '''
    # 主循环 sleep 时间
    _sleep_time = 1
    # session
    _session = None
    # 下载的 torrent handle 列表
    _handle_list = []
    # 默认下载配置
    _upload_rate_limit = 100000
    _download_rate_limit = 0
    _active_downloads = 8
    _torrent_upload_limit = 50000
    _torrent_download_limit = 0
    _info_hash_set = {}
    def __init__(self, session_file='session.state', delay_interval=5):
        self._session_file = session_file
        self._delay_interval = delay_interval

    # 辅助函数
    # 事件通知处理函数
    def _handle_alerts(self, alerts):
        while len(alerts):
            alert = alerts.pop()
            #print 'message: ', alert.msage()
            if isinstance(alert, lt.add_torrent_alert):
                alert.handle.set_upload_limit(self._torrent_upload_limit)
                alert.handle.set_download_limit(self._torrent_download_limit)
                self._handle_list.append(alert.handle)
            elif isinstance(alert, lt.dht_announce_alert):
                info_hash = alert.info_hash.to_string().encode('hex')
                self._info_hash_set[info_hash] = (alert.ip, alert.port)

    # 从文件中载入 session 状态
    def _load_state(self, ses_file):
        if os.path.isfile(ses_file):
            with open(ses_file, 'rb') as f:
                content = f.read()
                print 'load session state. len%d' % len(content)
                entry = lt.bdecode(content)
                self._session.load_state(entry)
                print 'load session state. nodes=%d' % self._session.status().dht_nodes
                print self._session.get_settings()
        else:
            print 'new session state.'

    # 创建 session 对象
    def create_session(self, tcp_port=32881, udp_port=32881):
        self._session = lt.session()
        self._session.set_alert_mask(lt.alert.category_t.all_categories)
        self._session.listen_on(tcp_port, udp_port)
        self._session.add_dht_router('router.bittorrent.com', 6881)
        self._session.add_dht_router('router.utorrent.com', 6881)
        self._session.add_dht_router('router.bitcomet.com', 6881)
        settings = self._session.get_settings()
        settings['upload_rate_limit'] = self._upload_rate_limit
        settings['download_rate_limit'] = self._download_rate_limit
        settings['active_downloads'] = self._active_downloads
        self._session.set_settings(settings)
        return self._session


    # 添加磁力链接
    def add_magnet(self, link):
        params = {'save_path': os.curdir,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                'paused': False,
                'auto_managed': True,
                'duplicate_is_error': True,
                'url': link}
        self._session.async_add_torrent(params)


    # 添加种子文件
    def add_torrent(self, torrent_file):
        e =  lt.bdecode(open(torrent_file, 'rb').read())
        info  = lt.torrent_info(e)
        params = {'save_path': os.curdir,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                'paused': False,
                'auto_managed': True,
                'duplicate_is_error': True,
                'ti': info }
        self._session.async_add_torrent(params)


    # 下载工作的状, 示循环
    def start_work(self):
        # 清理屏幕
        clear = lambda: os.system(['clear','cls'][os.name == 'nt'])
        self._load_state(self._session_file)
        show_interval = self._delay_interval
        while True:
            self._session.post_torrent_updates()
            self._handle_alerts(self._session.pop_alerts())
            time.sleep(self._sleep_time)
            if show_interval > 0:
                show_interval -= 1
                continue
            show_interval = self._delay_interval
            clear()
            # 下载信息显示
            show_content = ['torrents:\n']
            for (i, h) in enumerate(self._handle_list):
                s = h.status()
                name = 'unknown'
                if h.torrent_file() is not None:
                    name = h.torrent_file().name()
                    if os.name == 'nt':
                        name = name.decode('utf-8')
                show_content.append('  idx: %d => name %s\n'
                        '       %.2f%% complete state: %s\n' %
                        (i, 
                            name,
                            s.progress * 100, 
                            [s.state, 'paused'][s.paused]))
                show_content.append('       info => %s\n' %
                        h.info_hash().to_string().encode('hex'))
                show_content.append('       down: %.1f kB/s up: %.1f kB/s\n'
                        '       peers: %d all_peers: %d\n'
                        '       total_download: %.3f MB/s '
                        'total_upload: %.3f MB/s\n' %
                        (s.download_rate / 1000, 
                            s.upload_rate / 1000,
                            s.num_peers,
                            s.list_peers,
                            s.total_download / 1000000.0,
                            s.total_upload / 1000000.0))
            # 统计信息显示
            ses_state = self._session.status()
            show_content.append('\nstatistics:\n')
            show_content.append('  session state file: %s\n' %
                    self._session_file)
            show_content.append('  download rate limit: %.3f KB/s\n' % 
                    (self._download_rate_limit / 1000.0))
            show_content.append('  upload rate limit: %.3f KB/s\n' % 
                    (self._upload_rate_limit / 1000.0))
            show_content.append('  download torrent rate limit: %.3f KB/s\n' % 
                    (self._torrent_download_limit / 1000.0))
            show_content.append('  upload torrent rate limit: %.3f KB/s\n' % 
                    (self._torrent_upload_limit / 1000.0))
            show_content.append('  work numbers active(all): %d(%d)\n' % 
                    (min(self._active_downloads, len(self._handle_list)), 
                        len(self._handle_list)))
            show_content.append('  DHT node-id: %s\n' %
                    self._session.dht_state()['node-id'].encode('hex'))
            show_content.append('  DHT nodes: %d\n' % 
                    ses_state.dht_nodes)
            show_content.append('  DHT cache nodes: %d\n' % 
                    ses_state.dht_node_cache)
            show_content.append('  DHT global nodes: %d\n' % 
                    ses_state.dht_global_nodes)
            show_content.append('  download rate: %.1f kB/s\n' %
                    (ses_state.download_rate / 1000))
            show_content.append('  upload rate: %.1f kB/s\n' %
                    (ses_state.upload_rate / 1000))
            show_content.append('  info hash collection: %d, %r\n' %
                    (len(self._info_hash_set), self._info_hash_set))
            show_content.append('\n')
            print ''.join(show_content)


if __name__ == '__main__':
    link = 'magnet:?xt=urn:btih:0951c8405728344220872c2311a2bfa53b3c54ef&tr=udp://open.demonii.com:1337&tr=udp://tracker.publicbt.com:80/announce&tr=udp://tracker.openbittorrent.com:80/announce&tr=udp://tracker.istole.it:80/announce&tr=http://tracker.torrentfrancais.com/announce'
    link1 = 'magnet:?xt=urn:btih:3a3fcce9700086fdac36c30dce2b8f2fd7ba85f2&tr=udp://open.demonii.com:1337&tr=udp://tracker.publicbt.com:80/announce&tr=udp://tracker.openbittorrent.com:80/announce&tr=udp://tracker.istole.it:80/announce&tr=http://tracker.torrentfrancais.com/announce'
    link2 = 'magnet:?xt=urn:btih:d4f99b9dfc5cbfd6565db7d86d8905fb778701aa&tr=udp://open.demonii.com:1337&tr=udp://tracker.publicbt.com:80/announce&tr=udp://tracker.openbittorrent.com:80/announce&tr=udp://tracker.istole.it:80/announce&tr=http://tracker.torrentfrancais.com/announce'
    link3 = 'magnet:?xt=urn:btih:04e96c38e0a3c91b55182efd24c5c7e21cdcb75b&tr.0=udp://open.demonii.com:1337&tr.1=udp://tracker.publicbt.com:80/announce&tr.2=udp://tracker.openbittorrent.com:80/announce&tr.3=udp://tracker.istole.it:80/announce&tr.4=http://tracker.torrentfrancais.com/announce'
    #link3 = 'magnet:?xt=urn:btih:fe3c19e9867e0385774e33ad84c6b6eeb238deed'
    testlink = 'magnet:?xt=urn:btih:f5b642f55aa44634b96521ba271ecce7b4ed5e99'
    testlink2 = 'magnet:?xt=urn:btih:29c29ffb940a104e70425fe58175e1df54f48088'
    testlink3 = 'magnet:?xt=urn:btih:f5a89268388ad3fe59719f76e560267d1715bcfd'
    torrent_file = './test.torrent'
    torrent_file1 = './010314-515.torrent'
    torrent_file2 = '58.DDK082.torrent'
    torrent_file3 = '36.DANDY-327.torrent'

    sd = SimpleDownloader()
    sd.create_session()
    #sd.add_torrent(torrent_file)
    #sd.add_torrent(torrent_file1)
    #sd.add_torrent(torrent_file2)
    #sd.add_torrent(torrent_file3)
    #sd.add_magnet(link)
    #sd.add_magnet(link1)
    #sd.add_magnet(link2)
    #sd.add_magnet(link3)
    sd.add_magnet(testlink)
    sd.add_magnet(testlink2)
    sd.add_magnet(testlink3)
    sd.start_work()

