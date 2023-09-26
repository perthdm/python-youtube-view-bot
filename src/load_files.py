"""
MIT License

Copyright (c) 2021-2022 MShawon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from random import choices, shuffle


class proxy_info:
    def __init__(self, index, proxy):
        self.index = index
        self.proxy = proxy


def load_url():
    with open('urls.txt', encoding="utf-8") as fh:
        links = [x.strip() for x in fh if x.strip() != '']

    links = choices(links, k=len(links)*3) + links

    return links


def load_search():
    with open('search.txt', encoding="utf-8") as fh:
        search = [[y.strip() for y in x.strip().split('::::')]
                  for x in fh if x.strip() != '' and '::::' in x]

    search = choices(search, k=len(search)*3) + search
    
    return search

def load_proxy():
    proxies = []

    with open('proxy_list.txt', encoding="utf-8") as fh:
            loaded = [x.strip() for x in fh if x.strip() != '']

    for proxy in loaded:
        id = 0
        if proxy.count(':') == 3:
            split_index = proxy.split('|')
            split_proxy = split_index[0].split(':')
            proxy = f'{split_proxy[2]}:{split_proxy[-1]}@{split_proxy[0]}:{split_proxy[1]}'
            index = split_index[1]
        proxies.append(proxy_info(index=index,proxy=proxy))

    proxies = list(filter(None, proxies))
    shuffle(proxies)

    return proxies

