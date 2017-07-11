#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pickle
import os
import requests
import bs4
import sys


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

    def __init__(self):
        # deserialize cookies and token
        try:
            with open(self.cookie_jar, 'rb') as cache:
                self.cookies = pickle.load(cache)
                self.cookies.clear_expired_cookies()
                if 'XSRF-TOKEN' in self.cookies and 'laravel_session' in self.cookies:
                    self.token = pickle.load(cache)
            with open(self.supported_languages, 'r') as cache:
                self.languages = json.load(cache)
        except (IOError, OSError):
            pass
        # everything is loaded
        if self.token is not None and self.languages is not None:
            return
        # something is not current or missing, so refresh all cache
        resp = requests.get(self.base_url, headars=self.headers)
        if resp.ok:
            bs = bs4.BeautifulSoup(resp.text, 'html.parser')
            if self.token is None:
                tag = bs.find('input', attrs={'name': '_token'})
                self.serialize_cookies(resp.cookies, tag.attrs[u'value'])
            if self.languages is None:
                self.update_languages(bs)

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
        except (IOError, OSError) as e:
            pass

    def update_languages(self, bs=None):
        self.languages = []
        ajax_url = self.base_url + '/ajax/getSecondLanguage/'
        if bs is None:
            r = requests.get(self.base_url, cookies=self.cookies, headers=self.headers)
            if r.ok:
                bs = bs4.BeautifulSoup(r.text, 'html.parser')
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

    def print_lang_to(self, l):
        if l['to'] is not None:
            for t in l['to']:
                print('\t' + self.lang_str(t))

    def list_languages(self):
        for l in self.languages:
            print(self.lang_str(l))
            self.print_lang_to(l)

    def print_trans(self, search_word, lng_from, lng_to):
        data = {
            '_token': self.token,
            'lngFrom': int(lng_from),
            'lngTo': int(lng_to),
            'sourceWord': search_word,
            '_search': ''
        }
        resp = requests.post(self.search_url, data=data, cookies=self.cookies, headers=self.headers)
        if resp.ok:
            bs = bs4.BeautifulSoup(resp.text, 'html.parser')
            tag = bs.find('input', attrs={'name': '_token'})
            self.serialize_cookies(resp.cookies, tag.attrs[u'value'])
            res = bs.find('div', class_='translate-word')
            print(res)
            res = bs.find('div', id='trans_dictionary')
            print(res)
        else:
            print('<h2>Search failed: ' + resp.reason + ' (' + str(resp.status_code) + ')</h2>')

    def translate(self, word, lng_from=2, lng_to=1):
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
                print('<html><head><meta charset="utf-8"/><title>' + word + '</title><style>')
                print('''.translate-word { font-size:16px; font-weight: bold; margin-left:25px; display: inline-block; }
                .translate-trans { color: #e6343d; font-weight: normal; }''')
                print('</style></head><body>')
                self.print_trans(word, lng_from, lng_to)
                print('</body></html>')
            else:
                if src is not None:
                    print('Invalid destination language!')
                    print('Supported destination languages for ' + src['lng_name'] + ' (' + src['lng_id'] +') are:')
                    self.print_lang_to(src)
                else:
                    print('Invalid source language!')
                    print('Supported languages are:')
                    for l in self.languages:
                        print('\t' + self.lang_str(l))
                print('You can start the program with --update-languages parameter to update languages mapping.')


def print_usage():
    print('usage eurodict-scrapper.py [options] [<word> [<lang_id_from> <lang_id_to>]]')
    print('\tIf lang_id_from or lang_id_to are not set program will translate from English to Bulgarian:')
    print('\tOptions:')
    print('\t\t-l, --list-languages     show supported languages')
    print('\t\t-u, --update-languages   update supported languages from server')
    print('\t\t-h, --help               print this message')


def main():
    if len(sys.argv) < 2:
        print_usage()
        return
    if '-h' in sys.argv or '--help' in sys.argv:
        print_usage()
        return

    e = Eurodict()
    if '-u' in sys.argv or '--update-languages' in sys.argv:
        if e.update_languages():
            e.list_languages()
        else:
            print('Language mappings update failed!')
        return
    if '-l' in sys.argv or '--list-languages' in sys.argv:
        e.list_languages()
        return
    if len(sys.argv) < 4:
        print_usage()
    else:
        e.translate(sys.argv[1], sys.argv[2], sys.argv[3])

main()
