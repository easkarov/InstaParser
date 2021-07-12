import os
from time import sleep
from typing import List, Optional, Dict
import random
# from multiprocessing.pool import ThreadPool

import pickle

from selenium.webdriver import Chrome, ChromeOptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

from config import LOGIN, PASSWORD, USER_AGENT
import app_logger

logger = app_logger.get_logger(__name__)


class InstaParser:
    """Bot that collects Instagram posts"""

    COOKIE_PATH = './cookies'

    def __init__(self, username: str, password: str):
        self._username, self._password = username, password
        chrome_options = ChromeOptions()
        self.disable_webdriver_mode(chrome_options)
        self.set_user_agent(chrome_options, USER_AGENT)
        self._browser = Chrome(options=chrome_options)

    def login(self):
        """Log in to Instagram"""

        self._browser.get('https://www.instagram.com/')

        if self._load_cookies():
            sleep(5)
            return

        logger.info('логинимся...')

        self._browser.implicitly_wait(10)

        username_input = self._browser.find_element_by_name('username')
        self.fill_in_field(username_input, self._username)

        password_input = self._browser.find_element_by_name('password')
        self.fill_in_field(password_input, self._password)

        password_input.send_keys(Keys.ENTER)

        sleep(5)

    def search_posts_by_hashtag(self, hashtag: str, n: int = 100) -> List[str]:
        """This method searches for recent posts in the news feed"""

        self._browser.get(f'https://www.instagram.com/explore/tags/{hashtag}/')
        logger.info('загружена страница с лентой постов по хэштегу')
        sleep(7)

        posts_urls = [link.get_attribute('href')
                      for link in self._browser.find_elements_by_tag_name('a')
                      if '/p/' in link.get_attribute('href')]

        num_of_top_posts, len_posts = 9, len(posts_urls)

        while len_posts < (n + num_of_top_posts):
            links_on_page = self._browser.find_elements_by_tag_name('a')
            posts_links = [link.get_attribute('href') for link in links_on_page
                           if '/p/' in link.get_attribute('href')]
            posts_urls.extend(posts_links)
            len_posts = len(posts_urls)

            self._browser.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            sleep(random.randint(4, 7))

        return posts_urls[num_of_top_posts:]

    def filter_short_posts(self, urls: List[str], min_symbols: int = 100) -> List[str]:
        """This method filters out short posts, whose length is less than a certain number (min_symbols)"""

        long_posts_urls = []
        for url in urls:
            description = self.get_post_description(url)

            if (description is None) or (len(description) < min_symbols):
                continue

            long_posts_urls.append(url)
            logger.info(f'найден длинный пост: {url}')

            sleep(random.randint(2, 4))

        return long_posts_urls

    def get_post_description(self, url: str) -> Optional[str]:
        try:
            self._browser.get(url)
            block = self._browser.find_element_by_class_name('C4VMK')
            description = block.find_elements_by_tag_name('span')[1].text

            return description

        except NoSuchElementException:
            return None

    def get_long_posts_by_hashtag(self, hashtag: str, num_of_posts: int = 100) -> List[str]:
        """This method return a ready list of links of long posts"""

        posts_urls = self.search_posts_by_hashtag(hashtag, n=num_of_posts)
        logger.info(f'собрано всего ссылок на посты: {len(posts_urls)}')
        filtered_posts = self.filter_short_posts(posts_urls)
        logger.info(f'посты отфильтрованы. Кол-во длинных постов: {len(filtered_posts)}')

        return filtered_posts

    def check_if_xpath_exists(self, xpath: str) -> Optional[WebElement]:
        """Checking that the element xpath exists"""

        try:
            element = self._browser.find_element_by_xpath(xpath)
            return element
        except NoSuchElementException:
            return None

    def test_auto_mode(self):
        self._browser.get('https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html')

    def close_browser(self):
        """Close browser when work is finished"""

        self._dump_cookies(forced=False)

        self._browser.close()
        self._browser.quit()

    def get_browser(self):
        return self._browser

    def go_to(self, url):
        self._browser.get(url)

    def _load_cookies(self, path: Optional[str] = None):
        logger.info('получаем куки...')

        if path is None:
            path = InstaParser.COOKIE_PATH

        if os.path.exists(path):
            with open(path, 'rb') as file:
                cookies: List[Dict[str, str]] = pickle.load(file)
            for c in cookies:
                self._browser.add_cookie(c)
            return True

        logger.info('файл с куки не обнаружен')
        return False

    def _dump_cookies(self, path: Optional[str] = None, forced: bool = False):
        logger.info('выгружаем куки...')

        if path is None:
            path = InstaParser.COOKIE_PATH

        if forced | (not os.path.exists(path)):
            with open(path, 'wb') as file:
                pickle.dump(self._browser.get_cookies(), file)
                logger.info('куки успешно выгружены в файл')

    @staticmethod
    def disable_webdriver_mode(chrome_options: ChromeOptions):
        """This method turns off the auto mode"""

        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    @staticmethod
    def set_user_agent(chrome_options: ChromeOptions, user_agent: str):
        """Set up a custom user-agent"""

        chrome_options.add_argument('--user-agent=' + user_agent)

    @staticmethod
    def fill_in_field(element: WebElement, text: str):
        """Fills in input fields with data"""

        element.clear()
        element.send_keys(text)

    @classmethod
    def run(cls, hashtag):
        examp = cls(username=LOGIN, password=PASSWORD)
        examp.login()
        posts = examp.get_long_posts_by_hashtag(hashtag, num_of_posts=10)
        filename = 'tag_' + hashtag
        with open('./posts/' + filename, 'w') as file:
            file.write('\n'.join(posts))
        examp.close_browser()


def main():
    # hashtags = ['полезныесоветы', 'ремонт']
    #
    # pool = ThreadPool(processes=2)
    # pool.map(InstaParser.run, hashtags)
    hashtag = 'полезныесоветы'

    parser = InstaParser(username=LOGIN, password=PASSWORD)
    # if not parser.load_cookies():
    #     parser.login()
    # parser.go_to('https://instagram.com')

    # if os.path.exists('./cookies'):
    #     with open('cookies', 'rb') as file:
    #         cookies = pickle.load(file)
    #         parser.load_cookies(cookies)
    #         logger.info('куки успешно загрузились')
    # else:
    parser.login()
    logger.info('авторизация прошла успешно')

    links = parser.get_long_posts_by_hashtag(hashtag, num_of_posts=50)
    filename = 'tag_' + hashtag + '.txt'
    with open('./posts/' + filename, 'w') as file:
        file.write('\n'.join(links))
        logger.info('все найденные ссылки записаны в файлы')

    # parser.dump_cookies()

    parser.close_browser()

if __name__ == '__main__':
    main()
