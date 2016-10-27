#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import urllib
import urllib2
import cookielib
from BeautifulSoup import BeautifulSoup

# TODO: add option to print article text only without html, only <span>, <p>, <i> and <b> tags are used in body.

base_url = 'http://www.eurodict.com/'
# if we use cookielib then we get the HTTPCookieProcessor and install the opener in urllib2
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
urllib2.install_opener(opener)

if len(sys.argv) < 2:
    import os.path

    print('Usage: ', os.path.basename(sys.argv[0]), ' <word> [dictionary]')
    print('Available dictionaries:')
    response = urllib2.urlopen(base_url)
    soup = BeautifulSoup(response.read())
    select = soup.find('select', attrs={'name': 'diction'})
    for o in select.contents:
        print('    ', o['value'], ': ', o.contents[0])
    sys.exit()

word = sys.argv[1]
diction = 'ed_en_bg'
if len(sys.argv) > 2:
    diction = sys.argv[2]

url = base_url + 'search.php?' + urllib.urlencode({'word': sys.argv[1], 'go': 'Превод', 'ok': '1', 'diction': diction})
tx_data = None
tx_headers = {'User-agent': 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0;  rv:11.0) like Gecko'}

req = urllib2.Request(url, tx_data, tx_headers)
response = urllib2.urlopen(req)
html = response.read()

soup = BeautifulSoup(html, fromEncoding="utf-8")
tree = soup.find('td', attrs={'class': 'meaning_container'})

deltags = tree.findAll('div')
deltags.extend(tree.findAll('center'))
deltags.extend(tree.findAll('h4'))
deltags.extend(tree.findAll('h5'))

for t in deltags:
    t.extract()

head = '''<html>\n<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<style>
.wordtitle{
    font-weight:bold;
    color:navy;
}
.wordtrans{
    font-weight:bold;
    color:maroon;
}
.trans{
    font-family: "Lucida Sans Unicode", Tahoma, Verdana, Sans-serif;
    color:maroon;
}
</style>\n</head>\n<body>\n'''
output = str(tree)
left_index = output.find('<span class="wordtitle">')
right_index = output.find('<span class="adcont">')
print(head, output[left_index:right_index], '\n</body>\n</html>')
