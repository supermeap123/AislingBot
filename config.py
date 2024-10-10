import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    raise EnvironmentError("Missing DISCORD_TOKEN or OPENROUTER_API_KEY in environment variables.")

# Set up logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logger = logging.getLogger('aisling_bot')
logger.setLevel(logging.DEBUG)

# File handler
file_handler = RotatingFileHandler('logs/aisling_bot.log', maxBytes=5*1024*1024, backupCount=5)
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
logger.addHandler(console_handler)
