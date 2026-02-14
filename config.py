import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
SERYOZHA_ID = int(os.getenv("SERYOZHA_ID"))
ANGEL_ID = int(os.getenv("ANGEL_ID"))