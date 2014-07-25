#!/usr/bin/env python
# coding: utf-8


import os
import sys
import time
import json

import libtorrent as lt


class Collector(object):
    '''
    一个简单的 bt 下载工具，依赖开源库 libtorrent.
    '''
    # 主循环 sleep 时间
    _sleep_time = 1
    # 下载的 torrent handle 列表
    _handle_list = []
    # 默认下载配置
    _upload_rate_limit = 100000
    _download_rate_limit = 100000
    _active_downloads = 8
    _active_downloads_meta = 100
    _torrent_upload_limit = 10000
    _torrent_download_limit = 10000
    _sessiones = []
    _download_meta_session = None
    _info_hash_set = {}
    _meta_count = 0
    _meta_list = {}
    _tpath = None
    _auto_magnet_count = 0

    def __init__(self,
                 session_nums=50,
                 delay_interval=20,
                 # exit_time=2*60,
                 exit_time=30*60,
                 result_file=None,
                 stat_file=None):
        self._session_nums = session_nums
        self._delay_interval = delay_interval
        self._exit_time = exit_time
        self._result_file = result_file
        self._stat_file = stat_file
        if self._create_torrent_dir():
            self._backup_result()
        try:
            with open(self._result_file, 'rb') as f:
                self._meta_list = json.load(f)
        except Exception as err:
            pass

    def _create_torrent_dir(self):
        self._tpath = os.path.join('mytorrent', time.strftime('%Y%m%d'))
        if not os.path.isdir(self._tpath):
            os.mkdir(self._tpath)
            return True
        return False

    def _backup_result(self):
        os.system('cp %s %s_%s' %
                  (self._result_file,
                   time.strftime('%Y%m%d'),
                   self._result_file))

    def _get_runtime(self, interval):
        day = interval / (60*60*24)
        interval = interval % (60*60*24)
        hour = interval / (60*60)
        interval = interval % (60*60)
        minute = interval / 60
        interval = interval % 60
        second = interval
        return 'day: %d, hour: %d, minute: %d, second: %d' % \
               (day, hour, minute, second)

    # 辅助函数
    # 事件通知处理函数
    def _handle_alerts(self, alerts):
        while len(alerts):
            alert = alerts.pop()
            if isinstance(alert, lt.add_torrent_alert):
                alert.handle.set_upload_limit(self._torrent_upload_limit)
                alert.handle.set_download_limit(self._torrent_download_limit)
            elif isinstance(alert, lt.dht_announce_alert):
                info_hash = alert.info_hash.to_string().encode('hex')
                self._info_hash_set[info_hash] = (alert.ip, alert.port)
                if info_hash in self._meta_list:
                    self._meta_list[info_hash] += 1
                else:
                    self._add_magnet(info_hash)
            elif isinstance(alert, lt.metadata_received_alert):
                info_hash = alert.handle.info_hash().to_string().encode('hex')
                if info_hash in self._info_hash_set:
                    current_meta_counts = self._meta_list.get(info_hash, 0)
                    self._meta_list[info_hash] = current_meta_counts + 1
                    with open(os.path.join(self._tpath, info_hash), 'wb') as f:
                        info = alert.handle.get_torrent_info()
                        entry = lt.create_torrent(info).generate()
                        f.write(lt.bencode(entry))
                    self._meta_count += 1
                    self._download_meta_session.remove_torrent(alert.handle)

    # 从文件中载入 session 状态
    def _load_state(self, ses_file):
        if os.path.isfile(ses_file):
            with open(ses_file, 'rb') as f:
                content = f.read()
                entry = lt.bdecode(content)
                self._session.load_state(entry)

    # 创建 session 对象
    def create_session(self, begin_port=32801, download_meta_port=32800):
        for port in range(begin_port, begin_port + self._session_nums):
            session = lt.session()
            session.set_alert_mask(lt.alert.category_t.all_categories)
            session.listen_on(port, port)
            session.add_dht_router('router.bittorrent.com', 6881)
            session.add_dht_router('router.utorrent.com', 6881)
            session.add_dht_router('router.bitcomet.com', 6881)
            settings = session.get_settings()
            settings['upload_rate_limit'] = self._upload_rate_limit
            settings['download_rate_limit'] = self._download_rate_limit
            settings['active_downloads'] = self._active_downloads
            session.set_settings(settings)
            self._sessiones.append(session)

        # 创建下载 metadata 的session
        session = lt.session()
        session.set_alert_mask(lt.alert.category_t.all_categories)
        session.listen_on(download_meta_port, download_meta_port)
        session.add_dht_router('router.bittorrent.com', 6881)
        session.add_dht_router('router.utorrent.com', 6881)
        session.add_dht_router('router.bitcomet.com', 6881)
        settings = session.get_settings()
        settings['upload_rate_limit'] = self._upload_rate_limit
        settings['download_rate_limit'] = self._download_rate_limit
        settings['active_downloads'] = self._active_downloads_meta
        session.set_settings(settings)
        self._download_meta_session = session
        self._sessiones.append(self._download_meta_session)
        return self._sessiones

    def _add_magnet(self, info_hash):
        params = {'save_path': os.path.join(os.curdir,
                                            'collections',
                                            'magnet_' + info_hash),
                  'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                  'paused': False,
                  'auto_managed': True,
                  'duplicate_is_error': True,
                  'url': 'magnet:?xt=urn:btih:%s' % info_hash}
        self._download_meta_session.async_add_torrent(params)

    def add_hot_magnet(self, link=None):
        count = len(self._sessiones)
        hot_magnets = []
        step = count
        for info_hash in self._meta_list:
            if self._meta_list[info_hash] > 30:
                hot_magnets.append('magnet:?xt=urn:btih:%s' % info_hash)
                step -= 1
            if step <= 0:
                break
        self._auto_magnet_count = len(hot_magnets)
        if len(hot_magnets) < count:
            step = count - len(hot_magnets)
            if link:
                while True:
                    hot_magnets.append(link)
                    step -= 1
                    if step <= 0:
                        break
            else:
                for info_hash in self._meta_list:
                    hot_magnets.append('magnet:?xt=urn:btih:%s' % info_hash)
                    step -= 1
                    if step <= 0:
                        break

        count = 0
        for session in self._sessiones:
            params = {'save_path': os.path.join(os.curdir,
                                                'collections',
                                                'magnet_' + str(count)),
                      'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                      'paused': False,
                      'auto_managed': True,
                      'duplicate_is_error': True,
                      'url': hot_magnets[count]}
            session.async_add_torrent(params)
            count += 1

    # 添加磁力链接
    def add_magnet(self, link):
        count = 0
        for session in self._sessiones:
            params = {'save_path': os.path.join(os.curdir,
                                                'collections',
                                                'magnet_' + str(count)),
                      'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                      'paused': False,
                      'auto_managed': True,
                      'duplicate_is_error': True,
                      'url': link}
            session.async_add_torrent(params)
            count += 1

    # 添加种子文件
    def add_torrent(self, torrent_file):
        count = 0
        for session in self._sessiones:
            e = lt.bdecode(open(torrent_file, 'rb').read())
            info = lt.torrent_info(e)
            params = {'save_path': os.path.join(os.curdir,
                                                'collections',
                                                'torrent_' + str(count)),
                      'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                      'paused': False,
                      'auto_managed': True,
                      'duplicate_is_error': True,
                      'ti': info}
            session.async_add_torrent(params)
            count += 1

    def start_work(self):
        # 清理屏幕
        begin_time = time.time()
        show_interval = self._delay_interval
        while True:
            for session in self._sessiones:
                session.post_torrent_updates()
                self._handle_alerts(session.pop_alerts())
            time.sleep(self._sleep_time)
            if show_interval > 0:
                show_interval -= 1
                continue
            show_interval = self._delay_interval

            # 下载信息显示
            show_content = ['torrents:']
            # 统计信息显示
            interval = time.time() - begin_time
            torrents = self._download_meta_session.get_torrents()
            show_content.append('  run time: %s' % self._get_runtime(interval))
            show_content.append('  auto magnets: %d' % self._auto_magnet_count)
            show_content.append('  downloading meta: %d' % len(torrents))
            show_content.append('  info hash collection: %d (%f /minute)' %
                                (self._meta_count,
                                 self._meta_count * 60 / interval))
            show_content.append('  total metadata count: %d' %
                                len(self._meta_list))
            show_content.append('  current metadata count: %d' %
                                self._meta_count)
            show_content.append('\n')
            try:
                with open(self._stat_file, 'wb') as f:
                    f.write('\n'.join(show_content))
                with open(self._result_file, 'wb') as f:
                    json.dump(self._meta_list, f)
            except Exception as err:
                pass

            if interval >= self._exit_time:
                # stop
                break

            # 创建新的目录
            if self._create_torrent_dir():
                self._backup_result()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(-1)

    result_file = sys.argv[1]
    stat_file = sys.argv[2]

    link = 'magnet:?xt=urn:btih:ceab7a5dac14eef7a6614ac5927b90bbe8a2149d'\
           '&tr=udp://open.demonii.com:1337' \
           '&tr=udp://tracker.publicbt.com:80/announce' \
           '&tr=udp://tracker.openbittorrent.com:80/announce&' \
           'tr=udp://tracker.istole.it:80/announce&' \
           'tr=http://tracker.torrentfrancais.com/announce'
    testlink = 'magnet:?xt=urn:btih:f5b642f55aa44634b96521ba271ecce7b4ed5e99'
    torrent_file = './test.torrent'

    sd = Collector(session_nums=400,
                   result_file=result_file,
                   stat_file=stat_file)
    sd.create_session(32900)
    sd.add_hot_magnet(link)
    sd.start_work()
