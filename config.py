import dotenv
import os

dotenv.load_dotenv('./.env')
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
             'AppleWebKit/537.36 (KHTML, like Gecko)' \
             ' Chrome/91.0.4472.106 YaBrowser/21.6.0.616' \
             ' Yowser/2.5 Safari/537.36'
