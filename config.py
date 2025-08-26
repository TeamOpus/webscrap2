BOT_TOKEN = ""


API_ID =   
API_HASH = ""

# Optional: Proxy Configuration (if needed)
PROXIES = [
    # "http://username:password@proxy1:port",
    # "http://username:password@proxy2:port",
    # "socks5://username:password@proxy3:port"
]

# Optional: Advanced Settings
MAX_CONCURRENT_DOWNLOADS = 10
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
MAX_FILE_SIZE_MB = 100  # Maximum file size to download

# Optional: User Agent Pool
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0'
]

# Optional: Logging Configuration
import logging

LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
