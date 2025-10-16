import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

# Database
DATABASE_URL = "sqlite:///scheduler.db"

# Default Schedule
DEFAULT_SCHEDULE = {
    "08:00": "صبحانه",
    "09:00": "شروع کار/درس",
    "12:00": "ناهار", 
    "13:00": "استراحت",
    "14:00": "ادامه کار/درس",
    "18:00": "ورزش",
    "20:00": "مطالعه شخصی",
    "22:00": "استراحت و آماده شدن برای خواب"
}
