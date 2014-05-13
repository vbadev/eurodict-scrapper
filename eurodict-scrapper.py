#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
import sys
import urllib2
import cookielib

urlopen = urllib2.urlopen
Request = urllib2.Request
cj = cookielib.LWPCookieJar()

# Now we need to get our Cookie Jar installed in the opener for fetching URLs
if cookielib is not None:
    # if we use cookielib then we get the HTTPCookieProcessor and install the opener in urllib2
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)

url = (u'http://www.eurodict.com/search.php?word=' + sys.argv[1].decode('utf-8') + u'&go=%D0%9F%D1%80%D0%B5%D0%B2%D0%BE%D0%B4&ok=1&diction=ed_en_bg').encode('utf-8')

txdata = None
txheaders = {'User-agent':'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'}

req = Request(url, txdata, txheaders)
response = urlopen(req)
html = response.read()

soup = BeautifulSoup(html)
tree = soup.find('td', attrs={'class':'meaning_container'})

deltags = tree.findAll('div')
deltags.extend(tree.findAll('center'))
deltags.extend(tree.findAll('h4'))
deltags.extend(tree.findAll('h5'))

for t in deltags:
	t.extract()

head = u'''<html>\n<head>
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
lidx = output.find('<span class="wordtitle">')
ridx = output.find('<span class="adcont">')
print head, output[lidx:ridx], u'\n</body>\n</html>'
