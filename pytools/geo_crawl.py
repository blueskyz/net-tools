#!/usr/bin/env python
# coding: utf-8

import json
import urllib2

apiUrl = 'http://api.map.baidu.com/geocoder/v2/?address=%s&output=json&ak=xx&city=%s'

def name2Location(name, city):
    url = apiUrl % (name, city)
    print url
    req = urllib2.Request(url)
    req.add_header('Referer', 'www.xxx.com')
    result = urllib2.urlopen(req)
    result = json.loads(result.read())
    if result['status'] == 0: 
        if result.has_key('result') and len(result['result']) != 0:
            result = result['result']
        elif result.has_key('results') and len(result['results']) != 0:
            result = results[0]['result']
        else:
            return None
        location = result['location']
        return '%f,%f' % (location['lng'], location['lat'])
    return None

if __name__ == '__main__':
    while True:
        name = raw_input('> ')
        if len(name) > 0:
            result = name2Location(name, '上海')
            print result
        else:
            break

