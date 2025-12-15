import pandas as pd
from pypdf import PdfReader
from src.utils.helpers import extract_numbers_from_text, clean_phone_number

class DataService:
    @staticmethod
    def load_excel(file_path):
        data = []
        try:
            df = pd.read_excel(file_path)
            # Buscar columna con números automáticamente
            col_target = df.columns[0]
            for col in df.columns:
                if df[col].astype(str).str.contains(r'\d').any():
                    col_target = col
                    break
            
            for n in df[col_target].dropna():
                data.append(clean_phone_number(n))
            return data
        except Exception as e:
            raise Exception(f"Error Excel: {e}")

    @staticmethod
    def load_pdf(file_path):
        data = []
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            
            raw_nums = extract_numbers_from_text(text)
            for n in raw_nums:
                data.append(clean_phone_number(n))
            return data
        except Exception as e:
            raise Exception(f"Error PDF: {e}")