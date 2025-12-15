import re

def clean_phone_number(phone):
    """
    Limpia el número y asegura formato internacional básico.
    Elimina caracteres basura (paréntesis, guiones, espacios).
    """
    if not phone: return ""
    
    # Mantiene solo dígitos y el símbolo +
    clean = re.sub(r'[^\d+]', '', str(phone))
    
    # Auto-completar '+' si parece un número internacional sin prefijo explícito
    # (Asumiendo longitud > 9 como criterio básico)
    if not clean.startswith("+") and len(clean) > 9:
        clean = "+" + clean
        
    return clean

def extract_numbers_from_text(text):
    """
    Extrae números de teléfono de un texto crudo usando Regex.
    Soporta formatos: +51 999..., 999-999-999, etc.
    """
    # Regex: Opcional(+), digitos pais, separadores opcionales, digitos cuerpo
    return re.findall(r'(?:\+|)\d{1,4}[\s.-]?\d{3,}[\s.-]?\d{3,}', text)