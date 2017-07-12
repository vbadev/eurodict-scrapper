#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import pickle
import os
import requests
import bs4
import sys


class Render(object):
    soup = None
    empty_ipa = '[  ]'

    def __init__(self):
        pass

    def set_soup(self, soup):
        self.soup = soup

    def render(self, word, ipa, tr):
        return ''


class HtmlRender(Render):
    def render(self, word, ipa, tr):
        res = '<html><head><meta charset="utf-8"/><title>' + word + '</title><style>\n'
        res += '''.word { font-size:16px; font-weight: bold; display: inline-block; }
                       .ipa { color: #e6343d; font-weight: normal; }\n'''
        res += '</style></head><body>\n'
        res += '<div class="word">' + word
        if ipa != self.empty_ipa:
            res += ' <span class="ipa">' + ipa + '</span>'
        res += '</div>\n'
        self.__fix_tree(tr)
        for x in tr.contents:
            res += str(x)
        res += '</body></html>'
        return res

    def __fix_tree(self, tr):
        if self.soup is None or tr is None:
            return
        if len(tr.findAll('p')) == 0:
            p = self.soup.new_tag(name='p')
            while len(tr.contents) > 0:
                tag = tr.contents[0].extract()
                p.append(tag)
            tr.append(p)


class TextRender(Render):
    def render(self, word, ipa, tr):
        res = word
        if ipa != self.empty_ipa:
            res += ' ' + ipa
        res += '\n'
        for s in tr.strings:
            res += s
        return res


class Eurodict(object):
    base_url = 'http://www.eurodict.com'
    search_url = base_url + '/dictionary/translate'
    app_name = 'eurodict-scrapper'
    cache_dir = os.path.expanduser('~/.local/cache/' + app_name + '/')
    cookie_jar = cache_dir + 'cookie_jar.bin'
    supported_languages = cache_dir + 'languages.json'
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'}

    cookies = None
    token = None
    languages = None
    render = None

    def __init__(self):
        # deserialize cookies and token
        try:
            with open(self.cookie_jar, 'rb') as cache:
                self.cookies = pickle.load(cache)
                self.cookies.clear_expired_cookies()
                if 'XSRF-TOKEN' in self.cookies and 'laravel_session' in self.cookies:
                    self.token = pickle.load(cache)
        except (IOError, OSError):
            pass
        try:
            with open(self.supported_languages, 'r') as cache:
                self.languages = json.load(cache)
        except (IOError, OSError):
            pass
        # everything is loaded
        if self.token is not None and self.languages is not None:
            return
        # something is not current or missing, so refresh all cache
        resp = requests.get(self.base_url, headers=self.headers)
        if resp.ok:
            bs = self.get_soup(resp.text)
            if self.token is None:
                tag = bs.find('input', attrs={'name': '_token'})
                self.serialize_cookies(resp.cookies, tag.attrs[u'value'])
            if self.languages is None:
                self.update_languages(bs)

    def set_render(self, render):
        self.render = render

    def serialize_cookies(self, new_cookies=None, new_token=None):
        if new_cookies is not None:
            self.cookies = new_cookies
        if new_token is not None:
            self.token = new_token
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
            with open(self.cookie_jar, 'wb') as cache:
                pickle.dump(self.cookies, cache)
                pickle.dump(self.token, cache)
        except (IOError, OSError):
            pass

    @staticmethod
    def get_soup(text):
        try:
            res = bs4.BeautifulSoup(text, 'lxml')
        except bs4.FeatureNotFound:
            res = bs4.BeautifulSoup(text, 'html.parser')
        return res

    def update_languages(self, bs=None):
        self.languages = []
        ajax_url = self.base_url + '/ajax/getSecondLanguage/'
        if bs is None:
            r = requests.get(self.base_url, cookies=self.cookies, headers=self.headers)
            if r.ok:
                bs = self.get_soup(r.text)
        if bs is None:
            return False
        tags = bs.find_all('a', attrs={'data-type': 'from'})
        for l in tags:
            r = requests.get(ajax_url + l['data-lngid'], cookies=self.cookies, headers=self.headers)
            lng = {'lng_id': l['data-lngid'], 'lng_name': l.contents[0]}
            if r.ok:
                lng['to'] = json.loads(r.text)
            self.languages.append(lng)
        with open(self.supported_languages, 'w') as cache:
            json.dump(self.languages, cache)
        return True

    @staticmethod
    def lang_str(l):
        return l['lng_id'] + '. ' + l['lng_name']

    def dst_languages_to_str(self, l):
        res = ''
        if l['to'] is not None:
            for t in l['to']:
                res += '\t' + self.lang_str(t) + '\n'
        return res

    def list_languages(self):
        res = 'Format is <id>. <language>\n'
        for l in self.languages:
            res += self.lang_str(l) + '\n'
            res += self.dst_languages_to_str(l)
        return res

    def translate(self, word, lng_from, lng_to):
        if self.token is not None:
            src = None
            dst = None
            for l in self.languages:
                if l['lng_id'] == lng_from:
                    src = l
                    for t in l['to']:
                        if t['lng_id'] == lng_to:
                            dst = t
                            break
                    break
            if dst is not None:
                data = {
                    '_token': self.token,
                    'lngFrom': int(lng_from),
                    'lngTo': int(lng_to),
                    'sourceWord': word,
                    '_search': ''
                }
                resp = requests.post(self.search_url, data=data, cookies=self.cookies, headers=self.headers)
                if resp.ok:
                    bs = self.get_soup(resp.text)
                    tag = bs.find('input', attrs={'name': '_token'})
                    self.serialize_cookies(resp.cookies, tag.attrs[u'value'])
                    res = bs.find('div', class_='translate-word')
                    word = res.contents[0].strip()
                    res = bs.find('span', class_='translate-trans')
                    ipa = res.contents[0]
                    tr = bs.find('div', id='trans_dictionary')
                    if self.render is None:
                        self.render = HtmlRender()
                    self.render.set_soup(bs)
                    return self.render.render(word, ipa, tr)
                else:
                    return 'Search failed: ' + resp.reason + ' (' + str(resp.status_code) + ')'
            else:
                if src is not None:
                    res = 'Invalid destination language!\n'
                    res += 'Supported destination languages for ' + src['lng_name'] + ' (' + src['lng_id'] + ') are:\n'
                    res += self.dst_languages_to_str(src)
                    return res
                else:
                    res = 'Invalid source language!\nSupported languages are:\n'
                    for l in self.languages:
                        res += '\t' + self.lang_str(l) + '\n'
                    return res
        else:
            return 'Internal error: session information is not available'


def main():
    parser = argparse.ArgumentParser(description='Console client for eurodict.com')
    parser.add_argument('-f', '--from', default='2', dest='src', metavar='FROM', help='Language id to translate from')
    parser.add_argument('-t', '--to', default='1', dest='dst', metavar='TO', help='Language id to translate to')
    parser.add_argument('-o', '--output-format', default='html', metavar='FORMAT',
                        help='Output format. Currently only supported formats are html and text.')
    parser.add_argument('-l', '--list-languages', action='store_true', help='Show supported languages')
    parser.add_argument('-u', '--update-languages', action='store_true', help='Update supported languages from server')
    parser.add_argument('word', nargs='?', help='Word to translate')

    if len(sys.argv) == 1:
        parser.print_help()
        return
    args = parser.parse_args()

    e = Eurodict()
    if args.update_languages:
        if e.update_languages():
            print('Languages updated. You can run the program again with --list-languages argument to list them.')
    if args.list_languages:
        print(e.list_languages())
    if args.word is not None:
        render = None
        if args.output_format == 'html':
            render = HtmlRender()
        elif args.output_format == 'text':
            render = TextRender()
        if render is not None:
            e.set_render(render)
            print(e.translate(args.word, args.src, args.dst))
        else:
            print('Invalid output format "' + args.output_format + '" specified.')


main()
