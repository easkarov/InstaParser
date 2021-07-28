# -*- coding: utf-8 -*-

import os
import re
import shutil
from time import sleep
from queue import Queue
from threading import Thread
from typing import Optional

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ChromeOptions, Chrome
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement

from config import CW_PASSWORD, CW_LOGIN, USER_AGENT
from app_logger import get_logger
from exceptions import AttemptsLimitExceeded


logger = get_logger(__name__)


class Checker:
    URL_CHECK = 'https://content-watch.ru/text/'
    URL_LOGIN = 'https://content-watch.ru/login/'

    def __init__(self):
        options = ChromeOptions()
        self.get_options_in_order(options)
        self._browser = Chrome(options=options)
        self._browser.implicitly_wait(10)
        self.auth_attempts = 0

    @staticmethod
    def get_options_in_order(options: ChromeOptions):
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=' + USER_AGENT)
        options.add_argument('--headless')
        options.add_argument('--disable-logging')

    def login(self, *, login: str, password: str):
        self.auth_attempts += 1
        self._browser.get(Checker.URL_LOGIN)

        try:
            input_login = self._browser.find_element_by_css_selector('input[name=\'login\'')
            self.fill_in_field(input_login, login)
            sleep(1)

            input_pwd = self._browser.find_element_by_css_selector('input[name=\'password\'')
            self.fill_in_field(input_pwd, password)
            sleep(1)

            self.fill_in_field(input_pwd, Keys.ENTER, clear=False)
            sleep(1)

        except NoSuchElementException:
            if self.auth_attempts == 5:
                raise AttemptsLimitExceeded
            self.login(login=login, password=password)

    @staticmethod
    def fill_in_field(element: WebElement, text: str, *, clear: bool = True):
        if clear:
            element.clear()
        element.send_keys(text)

    def send_article_for_review(self, text: str):
        self._browser.get(Checker.URL_CHECK)

        text_area = self._browser.find_element_by_id('text')
        formatted_text = self.format_text(text)
        self.fill_in_field(text_area, formatted_text)

        sleep(1)
        check_div = self._browser.find_element_by_class_name('check-btn')
        check_btn = check_div.find_element_by_tag_name('a')
        check_btn.click()

    def check_result(self) -> Optional[str]:
        try:
            label = self._browser.find_element_by_class_name('global-result')
            return label.text

        except NoSuchElementException:
            return

    @staticmethod
    def format_text(text):
        symbols = '\s\-.:,!?=+@#$%&*)(\'"'
        new_text = re.sub('[^0-9a-zA-Zа-яА-Я' + symbols + ']', '', text)

        return new_text


def get_queue() -> Queue:
    queue = Queue()

    path = os.path.join(os.path.dirname(__file__), 'Posts')
    for hashtag in os.listdir(path)[1:]:
        hashtag_path = os.path.join(path, hashtag)

        for article in os.listdir(hashtag_path):
            if article.startswith('tag_'):
                continue

            with open(os.path.join(hashtag_path, article), 'rt', encoding='utf-16') as file:
                text: str = file.read()

            queue.put(((path, hashtag, article), text))

    return queue


class CheckerThread(Thread):
    def __init__(self, /, browser: Checker, queue: Queue):
        self.browser, self.queue = browser, queue

        super().__init__(daemon=True)

    def run(self):
        self.browser.login(login=CW_LOGIN, password=CW_PASSWORD)

        logger.info('logged in successfully')

        while True:
            if self.queue.empty():
                break

            (path, hashtag, filename), text = self.queue.get()
            self.browser.send_article_for_review(text)

            while (result := self.browser.check_result()) is None:
                logger.info('article is still unchecked. Waiting...')
                sleep(5)

            uniqueness = float(re.sub('[^0-9.]', '', result))

            if uniqueness != 100:
                logger.warning(f'Uniqueness is {uniqueness} (less than 100%)')

            if uniqueness == 100:
                logger.info(f'Uniqueness is {uniqueness}!')

                dst = os.path.join(os.path.dirname(__file__), 'UniquePosts', hashtag)
                if not os.path.exists(dst):
                    os.mkdir(dst)
                shutil.copy(os.path.join(path, hashtag, filename), dst)

                logger.info('Original file was copied and saved')

            self.queue.task_done()


def main():
    queue = get_queue()

    threads = [CheckerThread(browser=Checker(), queue=queue) for _ in range(5)]

    for th in threads:
        th.start()

    for th in threads:
        th.join()


if __name__ == '__main__':
    main()


