import re

def clean_phone_number(phone):
    """Limpia el número y asegura formato internacional básico."""
    clean = str(phone).replace(" ", "").replace("-", "").strip()
    if not clean.startswith("+") and len(clean) > 5:
        clean = "+" + clean
    return clean

def extract_numbers_from_text(text):
    """Extrae números de teléfono de un texto crudo usando Regex."""
    return re.findall(r'(?:\+|)\d[\d -]{8,14}\d', text)