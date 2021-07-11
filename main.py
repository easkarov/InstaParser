from time import sleep
from typing import List, Optional
import random

from selenium.webdriver import Chrome, ChromeOptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

from config import LOGIN, PASSWORD, USER_AGENT
import app_logger

logger = app_logger.get_logger(__name__)


class InstaParser:
    """Bot that collects Instagram posts"""

    def __init__(self, username: str, password: str):
        self.username, self.password = username, password
        chrome_options = ChromeOptions()
        self.disable_webdriver_mode(chrome_options)
        self.set_user_agent(chrome_options, USER_AGENT)
        self.browser = Chrome(options=chrome_options)

    def login(self):
        """Log in to Instagram"""

        self.browser.get('https://www.instagram.com/')

        self.browser.implicitly_wait(10)

        username_input = self.browser.find_element_by_name('username')
        self.fill_in_field(username_input, self.username)

        password_input = self.browser.find_element_by_name('password')
        self.fill_in_field(password_input, self.password)

        password_input.send_keys(Keys.ENTER)

        sleep(5)

    def search_posts_by_hashtag(self, hashtag: str, n: int = 100) -> List[str]:
        """This method searches for recent posts in the news feed"""

        self.browser.get(f'https://www.instagram.com/explore/tags/{hashtag}/')
        logger.info(' на страницу постов по хэштегу')
        sleep(7)

        posts_urls = [link.get_attribute('href')
                      for link in self.browser.find_elements_by_tag_name('a')
                      if '/p/' in link.get_attribute('href')]
        num_of_top_posts = 9
        while len(posts_urls) < (n + num_of_top_posts):
            links_on_page = self.browser.find_elements_by_tag_name('a')
            posts_links = [link.get_attribute('href') for link in links_on_page
                           if '/p/' in link.get_attribute('href')]
            posts_urls.extend(posts_links)

            self.browser.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            sleep(random.randint(4, 7))

        return posts_urls[num_of_top_posts:]

    def filter_short_posts(self, urls: List[str], min_symbols: int = 500) -> List[str]:
        """This method filters out short posts, whose length is less than a certain number (min_symbols)"""

        long_posts_urls = []
        for url in urls:
            self.browser.get(url)
            description_xpath = '/html/body/div[5]/div[2]/div/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span'
            element = self.check_if_xpath_exists(description_xpath)

            if (element is None) or (len(element.text) < min_symbols):
                continue

            long_posts_urls.append(url)

            sleep(random.randint(2, 4))

        return long_posts_urls

    def get_long_posts_by_hashtag(self, hashtag: str, num_of_posts: int = 100) -> List[str]:
        """This method return a ready list of links of long posts"""

        posts_urls = self.search_posts_by_hashtag(hashtag, n=num_of_posts)
        filtered_posts = self.filter_short_posts(posts_urls)

        return filtered_posts

    def check_if_xpath_exists(self, xpath: str) -> Optional[WebElement]:
        """Checking that the element xpath exists"""

        try:
            element = self.browser.find_element_by_xpath(xpath)
            return element
        except NoSuchElementException:
            return None

    def test_auto_mode(self):
        self.browser.get('https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html')

    def close_browser(self):
        """Close browser when work is finished"""

        self.browser.close()
        self.browser.quit()

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

    a = InstaParser(username=LOGIN, password=PASSWORD)
    a.login()
    links = a.get_long_posts_by_hashtag('психология', num_of_posts=10)
    print(links)
    a.close_browser()


if __name__ == '__main__':
    main()
