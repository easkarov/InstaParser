# -*- coding: utf-8 -*-

import asyncio
import os
import shutil
from itertools import zip_longest
from pickle import dump
from random import random
from re import sub
from typing import NamedTuple, List, Tuple

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from requests_html import HTML

from config import USER_AGENT, CW_PASSWORD, CW_LOGIN

ARTICLES_LIMIT = 5


class CwUrls(NamedTuple):
    login = 'https://content-watch.ru/public/php/loginv2.php'
    main_page = 'https://content-watch.ru/text/'
    checker_start = 'https://content-watch.ru/public/php/checker_start.php'
    check = 'https://content-watch.ru/public/php/check_text.php'
    progress = 'https://content-watch.ru/public/php/checker_progress.php'
    result = 'https://content-watch.ru/public/php/checker_result.php'


URLS = CwUrls()


async def login(s: ClientSession):
    headers = {'User-Agent': USER_AGENT}
    s.headers.update(headers)

    await s.post(URLS.login, data={'login': CW_LOGIN, 'password': CW_PASSWORD})

    cookies = s.cookie_jar.__dict__.copy()
    del cookies['_loop']

    with open('../Cookies/cw_cookies.txt', 'wb') as file:
        dump(cookies, file)


async def get_checker_code(session: ClientSession) -> int:
    async with session.get(URLS.main_page) as response:
        main_page = await response.text()
        html = HTML(html=main_page, async_=True)

    params = {'json': '', 'r': random()}
    async with session.get(URLS.checker_start, params=params) as response:
        json_response = await response.json(content_type='text/html')
        code_script = json_response['code']
        code: int = await html.arender(script=code_script)

    return code


async def get_csrf_token(session: ClientSession) -> str:
    async with session.get(URLS.main_page) as response:
        main_page = await response.text()
        bs = BeautifulSoup(main_page, 'html.parser')
        csrf_token: str = bs.find(id='csrf').get('value')

    return csrf_token


async def send_article_for_review(text: str, *, session: ClientSession, checker_code: int,
                                  csrf_token: str) -> str:
    data = {'text': text, 'val': len(text),
            'ignore': 0,
            'save_ignore': '0',
            'csrf': csrf_token,
            'code': checker_code, 'r': random()}

    async with session.post(URLS.check, data=data) as response:
        check_text = await response.text()
        print(check_text)
        json_response = await response.json(content_type='text/html')

    return json_response['hash']


async def get_result_of_the_check(text_hash: str, session: ClientSession) -> str:
    params = {'check': 'text', 'json': '', 'hash': text_hash}

    async with session.get(URLS.result, params=params) as response:
        json_response = await response.json(content_type='text/html')
        uniqueness = sub('[^0-9.]', '', json_response['global']['uniq'])
        print(uniqueness)

    return uniqueness


async def get_check_progress(text_hash: str, session: ClientSession) -> int:
    params = {'check': 'text', 'json': '',
              'hash': text_hash}

    async with session.get(URLS.progress, params=params) as response:
        json_response = await response.json()
        progress = int(json_response['progress'])

    return progress


async def check_article(s: ClientSession, data: Tuple[Tuple[str, str, str], str]):
    (path, hashtag, filename), text = data

    csrf_token = await get_csrf_token(s)
    code = await get_checker_code(s)

    text_hash = await send_article_for_review(text, session=s, checker_code=code,
                                              csrf_token=csrf_token)

    while (percent := await get_check_progress(text_hash, session=s)) != 500:
        await asyncio.sleep(5)
        print(str(percent) + '%')

    result = float(await get_result_of_the_check(text_hash, session=s))
    print(result)

    if result == 100:
        dst = os.path.join(os.path.dirname(__file__), '../UniquePosts', hashtag, filename)
        shutil.copy(os.path.join(path, hashtag, filename), dst)


def get_data() -> List[Tuple[Tuple[str, str, str], str]]:
    texts = []

    path = os.path.join(os.path.dirname(__file__), '../Posts')
    for hashtag in os.listdir(path)[:1]:
        hashtag_path = os.path.join(path, hashtag)

        for article in os.listdir(hashtag_path)[:3]:
            if article.startswith('tag_'):
                continue

            with open(os.path.join(hashtag_path, article)) as file:
                text = file.read()

            texts.append(((path, hashtag, article), text))

    return texts


async def main():
    data = iter(get_data())
    groups = tuple(zip_longest(*[data for _ in range(ARTICLES_LIMIT)]))

    async with ClientSession() as session:
        logging = asyncio.create_task(login(session))
        await logging
        print('logged in')
        print(groups)
        tasks = []
        for group in groups:
            for elem in group:
                if elem is None:
                    continue
                tasks.append(asyncio.create_task(check_article(session, elem)))

        await asyncio.gather(*tasks)

    print('texts is successfully checked')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
