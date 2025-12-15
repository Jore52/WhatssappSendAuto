import os

# --- RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "chrome_user_data")

# --- UI COLORS ---
COLOR_PRIMARY = "#1a73e8"
COLOR_SUCCESS = "#188038"
COLOR_ERROR = "red"
COLOR_WARNING = "orange"
THEME_MODE = "Light"

# --- SELENIUM ---
WAIT_TIMEOUT = 35