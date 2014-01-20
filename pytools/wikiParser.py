#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import re
from urllib import urlopen
from BeautifulSoup import BeautifulSoup as bsoup

def compileReg():
    #char200E = u'\ufeff'
    char200E = codecs.BOM_UTF8.decode('utf-8')
    charBOM = u'\u200e'
    charComment = u'\[[^\]]*\]'
    pattern = u'%s|%s|%s' % (char200E, charBOM, charComment)
    #print {pattern}
    pattern = re.compile(pattern)
    return pattern

pattern = compileReg()

def filterInvalidChar(pattern, text):
    """
    text must be unicode character.
    """
    text = pattern.sub('', text)
    return text

def parseWikiContent(text):
    soup = bsoup(text)
    # check exists
    noarticle = soup('div', {"class" : "noarticletext"})
    if len(noarticle) != 0:
        print 'not exist!!!'
        return None
    pSet = soup('div', {'id' : 'mw-content-text'})[0].findChildren('p', recursive=False)
    loops = 3
    contents = ''
    for p in pSet:
        if loops == 0:
            break
        #print p
        content = p.getText()
        #print content
        if len(content) >= 4 and content[0:6].find(u'坐标') == -1:
            content = filterInvalidChar(pattern, content)
            contents += content.encode('utf-8') + '\n'
        loops -= 1
    if len(contents) > 0:
        return contents
    else:
        return None


if __name__ == '__main__':
    while True:
        name = raw_input('> ')
        #name = name.decode('gbk').encode('utf-8')
        if len(name) > 0:
            url = 'http://zh.wikipedia.org/zh-cn/%s' % (name)
            #print url.decode('utf-8').encode('gbk')
            print url
            text = urlopen(url).read()
            content = parseWikiContent(text)
            if content is not None:
                print content
            else:
                print "can't get content!"
        else:
            break

