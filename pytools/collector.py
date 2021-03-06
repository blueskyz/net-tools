#!/usr/bin/env python
# coding: utf-8


import os
import sys
import time
import json
import random
import traceback as tb

import libtorrent as lt


class Collector(object):
    '''
    一个简单的 bt 下载工具，依赖开源库 libtorrent.
    '''
    # 主循环 sleep 时间
    _sleep_time = 0.5
    # 下载的 torrent handle 列表
    _handle_list = []
    # 默认下载配置
    _upload_rate_limit = 200000
    _download_rate_limit = 200000
    _active_downloads = 30
    _alert_queue_size = 4000
    _dht_announce_interval = 60
    _torrent_upload_limit = 20000
    _torrent_download_limit = 20000
    _auto_manage_startup = 30
    _auto_manage_interval = 15

    _start_port = 32800
    _sessions = []
    _session_work_num = 3
    _download_metadata_nums = 0
    _infohash_queue_from_getpeers = []
    _info_hash_set = {}
    _meta_count = 0
    _meta_list = {}
    _tpath = None
    _auto_magnet_count = 0

    def __init__(self,
                 session_nums=50,
                 delay_interval=20,
                 # exit_time=2*60,
                 exit_time=5*60,
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
    def _handle_alerts(self, session, alerts):
        while len(alerts):
            alert = alerts.pop()
            if isinstance(alert, lt.add_torrent_alert):
                alert.handle.set_upload_limit(self._torrent_upload_limit)
                alert.handle.set_download_limit(self._torrent_download_limit)
            elif isinstance(alert, lt.dht_announce_alert):
                info_hash = alert.info_hash.to_string().encode('hex')
                if info_hash in self._meta_list:
                    self._meta_list[info_hash] += 1
                elif info_hash in self._info_hash_set:
                    pass
                else:
                    self._info_hash_set[info_hash] = (alert.ip, alert.port)
                    self._add_magnet(session, info_hash)
            elif isinstance(alert, lt.dht_get_peers_alert):
                info_hash = alert.info_hash.to_string().encode('hex')
                if info_hash in self._meta_list:
                    self._meta_list[info_hash] += 1
                elif info_hash in self._info_hash_set:
                    pass
                else:
                    self._info_hash_set[info_hash] = None
                    self._infohash_queue_from_getpeers.append(info_hash)
                    self._add_magnet(session, info_hash)
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
                    session.remove_torrent(alert.handle)
                    self._download_metadata_nums -= 1
                    # fixme: 当从同一个初始link下载时，
                    # 可能并不是_download_meta_session的handle，误删崩溃
                    # self._download_meta_session.remove_torrent(alert.handle)

    # 从文件中载入 session 状态
    def _load_state(self, ses_file):
        if os.path.isfile(ses_file):
            with open(ses_file, 'rb') as f:
                content = f.read()
                entry = lt.bdecode(content)
                self._session.load_state(entry)

    def _add_magnet(self, session, info_hash):
        params = {'save_path': os.path.join(os.curdir,
                                            'collections',
                                            'magnet_' + info_hash),
                  'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                  'paused': False,
                  'auto_managed': True,
                  'duplicate_is_error': True,
                  'url': 'magnet:?xt=urn:btih:%s' % info_hash}
        session.async_add_torrent(params)
        self._download_metadata_nums += 1

    # 创建 session 对象
    def create_session(self, begin_port=32800):
        self._start_port = begin_port
        for port in range(begin_port, begin_port + self._session_nums):
            session = lt.session()
            session.set_alert_mask(lt.alert.category_t.all_categories)
            session.listen_on(port, port)
            session.add_dht_router('router.bittorrent.com', 6881)
            session.add_dht_router('router.utorrent.com', 6881)
            session.add_dht_router('router.bitcomet.com', 6881)
            session.add_dht_router('dht.transmissionbt.com', 6881)
            settings = session.get_settings()
            settings['upload_rate_limit'] = self._upload_rate_limit
            settings['download_rate_limit'] = self._download_rate_limit
            settings['active_downloads'] = self._active_downloads
            settings['auto_manage_startup'] = self._auto_manage_startup
            settings['auto_manage_interval'] = self._auto_manage_interval
            settings['dht_announce_interval'] = self._dht_announce_interval
            settings['alert_queue_size'] = self._alert_queue_size
            session.set_settings(settings)
            self._sessions.append(session)
        return self._sessions

    def add_hot_magnet(self, link=None):
        count = len(self._sessions) * self._session_work_num
        hot_magnets = []
        for info_hash in self._meta_list:
            if self._meta_list[info_hash] > 50:
                hot_magnets.append('magnet:?xt=urn:btih:%s' % info_hash)

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
        else:
            random.shuffle(hot_magnets)

        count = 0
        workids = range(self._session_work_num)
        for session in self._sessions:
            for i in workids:
                url = hot_magnets[count]
                # if i == 0:
                #     url = link
                params = {'save_path': os.path.join(os.curdir,
                                                    'collections',
                                                    'magnet_' + str(count)),
                          'storage_mode':
                          lt.storage_mode_t.storage_mode_sparse,
                          'paused': False,
                          'auto_managed': True,
                          'duplicate_is_error': True,
                          'url': url}
                session.async_add_torrent(params)
                count += 1

    # 添加磁力链接
    def add_magnet(self, link):
        count = 0
        workids = range(self._session_work_num)
        for session in self._sessions:
            for i in workids:
                params = {'save_path': os.path.join(os.curdir,
                                                    'collections',
                                                    'magnet_' + str(count)),
                          'storage_mode':
                          lt.storage_mode_t.storage_mode_sparse,
                          'paused': False,
                          'auto_managed': True,
                          'duplicate_is_error': True,
                          'url': link}
                session.async_add_torrent(params)
                count += 1

    # 添加种子文件
    def add_torrent(self, torrent_file):
        count = 0
        for session in self._sessions:
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
            for session in self._sessions:
                session.post_torrent_updates()
                self._handle_alerts(session, session.pop_alerts())
            time.sleep(self._sleep_time)
            if show_interval > 0:
                show_interval -= 1
                continue
            show_interval = self._delay_interval

            # 下载信息显示
            show_content = ['torrents:']
            # 统计信息显示
            interval = time.time() - begin_time
            torrent_nums = self._download_metadata_nums
            show_content.append('  pid: %s' % os.getpid())
            show_content.append('  time: %s' %
                                time.strftime('%Y-%m-%d %H:%M:%S'))
            show_content.append('  run time: %s' % self._get_runtime(interval))
            show_content.append('  start port: %d' % self._start_port)
            show_content.append('  collect session num: %d' %
                                len(self._sessions))
            show_content.append('  session work num: %d' %
                                self._session_work_num)
            show_content.append('  auto magnets: %d' % self._auto_magnet_count)
            show_content.append('  new info hash nums: %d' %
                                len(self._info_hash_set))
            show_content.append('  info hash nums from get peers: %d' %
                                len(self._infohash_queue_from_getpeers))
            show_content.append('  downloading meta: %d' % torrent_nums)
            show_content.append('  torrent collection rate: %f /minute' %
                                (self._meta_count * 60 / interval))
            show_content.append('  current torrent count: %d' %
                                self._meta_count)
            show_content.append('  total torrent count: %d' %
                                len(self._meta_list))
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

        # destory
        for session in self._sessions:
            torrents = session.get_torrents()
            for torrent in torrents:
                session.remove_torrent(torrent)


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
    link = 'magnet:?xt=urn:btih:0cb0a5ac267d04b027997b6259592996221ee17d'
    testlink = 'magnet:?xt=urn:btih:f5b642f55aa44634b96521ba271ecce7b4ed5e99'
    torrent_file = './test.torrent'

    # 创建一个每小时固定的端口段，解决因get_peers收集过快，创建任务过多，
    # 带来的下载torrent文件过慢
    hour = time.localtime().tm_hour
    port = range(32800, 33800, 100)
    port = port[hour % len(port)]
    sd = Collector(session_nums=100,
                   result_file=result_file,
                   stat_file=stat_file)
    sd.create_session(port)
    sd.add_hot_magnet(link)
    # sd.add_magnet(link)
    sd.start_work()
