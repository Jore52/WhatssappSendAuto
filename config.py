import os

# --- RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "chrome_user_data")

# --- UI COLORS ---
COLOR_PRIMARY = "#1a73e8"  # Azul estilo Google
COLOR_SUCCESS = "#188038"  # Verde estilo WhatsApp/Excel
COLOR_ERROR = "red"
COLOR_WARNING = "orange"
THEME_MODE = "Light"

# --- SELENIUM ---
# Tiempo máximo de espera para elementos críticos (QR, carga de chat)
WAIT_TIMEOUT = 40