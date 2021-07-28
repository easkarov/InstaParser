# -*- coding: utf-8 -*-

import os
import shutil
from pickle import dump
from queue import Queue
from random import random
from re import sub
from threading import Thread
from time import sleep
from typing import NamedTuple
import asyncio

from bs4 import BeautifulSoup
from requests import Session
from requests_html import HTML

from config import USER_AGENT, CW_LOGIN, CW_PASSWORD


class CwUrls(NamedTuple):
    login = 'https://content-watch.ru/public/php/loginv2.php'
    main_page = 'https://content-watch.ru/text/'
    checker_start = 'https://content-watch.ru/public/php/checker_start.php'
    check = 'https://content-watch.ru/public/php/check_text.php'
    progress = 'https://content-watch.ru/public/php/checker_progress.php'
    result = 'https://content-watch.ru/public/php/checker_result.php'


URLS = CwUrls()


def login() -> Session:
    s = Session()
    headers = {'User-Agent': USER_AGENT}
    s.headers.update(headers)

    s.post(URLS.login,
           data={'login': CW_LOGIN,
                 'password':
                     CW_PASSWORD})

    with open('../Cookies/cw_cookies.txt', 'wb') as file:
        dump(s.cookies, file)

    return s


async def get_checker_code(session: Session) -> int:
    main_page = session.get(URLS.main_page)
    html = HTML(html=main_page.text, async_=True)
    code_script = session.get(URLS.checker_start,
                              params={'json': '', 'r': random()}).json()['code']
    code: int = await html.arender(script=code_script)

    return code


def get_csrf_token(session: Session) -> str:
    main_page = session.get(URLS.main_page)
    bs = BeautifulSoup(main_page.text, 'html.parser')
    csrf_token: str = bs.find(id='csrf').get('value')

    return csrf_token


def send_article_for_review(text: str, *, session: Session, checker_code: int,
                            csrf_token: str) -> str:
    check_text = session.post(URLS.check,
                              data={'text': text, 'val': len(text),
                                    'ignore': 0,
                                    'save_ignore': '0',
                                    'csrf': csrf_token,
                                    'code': checker_code, 'r': random()})
    print(check_text.text)
    text_hash = check_text.json()['hash']

    return text_hash


def get_result_of_the_check(text_hash: str, session: Session) -> str:
    url = URLS.result
    result = session.get(url, params={'check': 'text', 'json': '',
                                      'hash': text_hash}).json()['global']['uniq']
    result = sub('[^0-9.]', '', result)
    print(result)

    return result


def get_check_progress(text_hash: str, session: Session) -> int:
    params = {'check': 'text', 'json': '',
              'hash': text_hash}
    progress = int(session.get(URLS.progress, params=params).json()['progress'])

    return progress


async def get_code(session: Session):
    main_page = session.get(URLS.main_page)
    html = HTML(html=main_page.text)
    code_script = session.get(URLS.checker_start,
                              params={'json': '', 'r': random()}).json()['code']
    code: int = html.render(script=code_script)

    return code


class Checker(Thread):
    def __init__(self, s: Session, q: Queue, loop: asyncio.AbstractEventLoop = None):
        super().__init__()
        self.s = s
        self.q = q
        self.loop = loop

    def run(self):
        # loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon(self.check)
        self.loop.run_forever()

    def check(self):
        csrf_token = get_csrf_token(self.s)
        code = self.loop.create_task(get_checker_code(self.s))
        code = code.result()
        # code = '123'
        (path, hashtag, filename), text = self.q.get()

        text_hash = send_article_for_review(text, session=self.s, checker_code=code,
                                            csrf_token=csrf_token)

        while (percent := get_check_progress(text_hash, session=self.s)) != 500:
            sleep(5)
            print(str(percent) + '%')

        result = float(get_result_of_the_check(text_hash, session=self.s))
        print(result)

        if result == 100:
            dst = os.path.join(os.path.dirname(__file__), '../UniquePosts', hashtag, filename)
            shutil.copy(os.path.join(path, hashtag, filename), dst)

        self.q.task_done()


def main():
    queue = Queue()

    path = os.path.join(os.path.dirname(__file__), '../Posts')
    for hashtag in os.listdir(path)[:1]:
        hashtag_path = os.path.join(path, hashtag)

        for article in os.listdir(hashtag_path)[:3]:
            if article.startswith('tag_'):
                continue

            with open(os.path.join(hashtag_path, article)) as file:
                text = file.read()

            queue.put(((path, hashtag, article), text))

    session = login()
    # code = get_checker_code(session)
    loop = asyncio.get_event_loop()
    threads = [Checker(s=session, q=queue, loop=loop) for _ in range(3)]

    for th in threads:
        th.start()
        loop.call_soon_threadsafe(th.check)


    for th in threads:
        th.join()

    print('texts is successfully checked')


if __name__ == '__main__':
    main()
