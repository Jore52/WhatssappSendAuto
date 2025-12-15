import pandas as pd
from pypdf import PdfReader
from src.utils.helpers import extract_numbers_from_text, clean_phone_number

class DataService:
    @staticmethod
    def load_excel(file_path):
        """
        Carga Excel intentando identificar columnas de teléfono y nombre.
        Retorna: lista de tuplas [(numero, nombre), ...]
        """
        data = []
        try:
            # Leer como string para preservar ceros a la izquierda
            df = pd.read_excel(file_path, dtype=str)
            df.fillna("", inplace=True)
            
            # 1. Identificar columna de Teléfono
            col_phone = None
            # Prioridad A: Por encabezado
            for col in df.columns:
                c_low = col.lower()
                if any(x in c_low for x in ['tel', 'cel', 'phone', 'movil', 'number', 'whatsapp']):
                    col_phone = col
                    break
            
            # Prioridad B: Por contenido (si no encuentra encabezado)
            if not col_phone:
                for col in df.columns:
                    # Limpia no-dígitos y revisa si parece un teléfono (> 7 dígitos promedio)
                    sample = df[col].astype(str).str.replace(r'\D', '', regex=True)
                    if len(sample) > 0 and sample.str.len().mean() > 7:
                        col_phone = col
                        break
            
            # Fallback: Usar primera columna
            if not col_phone:
                col_phone = df.columns[0]

            # 2. Identificar columna de Nombre (Opcional)
            col_name = None
            for col in df.columns:
                if col == col_phone: continue
                c_low = col.lower()
                if any(x in c_low for x in ['nom', 'name', 'cliente', 'user', 'señor']):
                    col_name = col
                    break
            
            # 3. Extraer y limpiar datos
            for _, row in df.iterrows():
                raw_num = str(row[col_phone])
                clean_num = clean_phone_number(raw_num)
                
                name = ""
                if col_name:
                    name = str(row[col_name]).strip()
                
                # Filtrar números muy cortos o vacíos
                if len(clean_num) > 5: 
                    data.append((clean_num, name))
                    
            return data

        except Exception as e:
            print(f"Error leyendo Excel: {e}")
            raise Exception("Error al leer Excel. Verifique que el archivo no esté corrupto.")

    @staticmethod
    def load_pdf(file_path):
        """
        Extrae números de un PDF.
        Retorna: lista de tuplas [(numero, ""), ...]
        """
        data = []
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            
            raw_nums = extract_numbers_from_text(text)
            
            # Usar set para evitar duplicados del mismo PDF
            seen = set()
            for n in raw_nums:
                clean = clean_phone_number(n)
                if len(clean) > 5 and clean not in seen:
                    data.append((clean, "")) # Nombre vacío por defecto
                    seen.add(clean)
            return data
        except Exception as e:
            raise Exception(f"Error leyendo PDF: {e}")