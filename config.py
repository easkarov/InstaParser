import dotenv
import os

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
             '(KHTML, like Gecko)' \
             'Chrome/91.0.4472.135 YaBrowser/21.6.2.855 Yowser/2.5 Safari/537.36'

CW_LOGIN = os.getenv('CW_LOGIN')
CW_PASSWORD = os.getenv('CW_PASSWORD')