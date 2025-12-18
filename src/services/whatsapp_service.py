import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import config

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None

    def start_browser(self):
        """Inicia el navegador con configuración robusta"""
        opts = Options()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-infobars")
        opts.add_argument(f"user-data-dir={config.USER_DATA_DIR}")
        opts.add_argument("--disable-gpu")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.wait = WebDriverWait(self.driver, 30) # Timeout aumentado para subida de imágenes
        self.driver.get("https://web.whatsapp.com")

    def is_logged_in(self):
        try:
            return len(self.driver.find_elements(By.ID, "pane-side")) > 0
        except:
            return False

    def get_qr_screenshot(self, save_path="temp_qr.png"):
        try:
            qr = self.driver.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!'], div[data-ref]")
            if qr:
                qr[0].screenshot(save_path)
                return True
        except: pass
        return False

    def reload_qr(self):
        try:
            self.driver.find_element(By.CSS_SELECTOR, "button, span[data-icon='refresh-large']").click()
        except: pass

    def send_message(self, phone, message, image_path=None):
        """Orquestador principal de envíos"""
        clean_n = phone.replace("+", "").replace(" ", "").strip()
        if not clean_n.isdigit():
            raise Exception("Número mal formado")

        url = f"https://web.whatsapp.com/send?phone={clean_n}"
        self.driver.get(url)

        # 1. Esperar Carga (Chat o Popup error)
        try:
            self.wait.until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "#main div[contenteditable='true']") or 
                          d.find_elements(By.CSS_SELECTOR, "div[data-animate-modal-popup='true']")
            )
        except TimeoutException:
            raise Exception("Timeout esperando carga del chat")

        # 2. Validar Número
        invalid = self.driver.find_elements(By.CSS_SELECTOR, "div[data-animate-modal-popup='true']")
        if invalid:
            if "inválido" in invalid[0].text.lower() or "invalid" in invalid[0].text.lower():
                try: invalid[0].find_element(By.CSS_SELECTOR, "div[role='button']").click()
                except: pass
                raise Exception("Número Inválido")

        time.sleep(1) # Estabilización

        # 3. Enviar Contenido
        if image_path and os.path.exists(image_path):
            self._send_attachment(image_path, message)
        elif message:
            self._send_text_only(message)
        
        time.sleep(1) # Pausa técnica

    def _send_attachment(self, path, caption):
        """
        Lógica CRÍTICA de envío de imagen + caption.
        Maneja el Editor de Medios de forma explícita.
        """
        # A. Cargar Imagen (Input oculto estándar)
        # Aunque el flujo manual sea Ctrl+V, send_keys al input es más estable para automatización
        try:
            input_box = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            input_box.send_keys(path)
        except Exception as e:
            raise Exception(f"No se pudo cargar la imagen al input: {e}")

        # B. Esperar al Editor de Medios
        # El indicador más fiable de que el editor cargó es el botón de enviar (círculo verde con avión)
        send_icon_selector = (By.CSS_SELECTOR, "span[data-icon='send']")
        try:
            self.wait.until(EC.visibility_of_element_located(send_icon_selector))
        except TimeoutException:
            raise Exception("Timeout: La imagen no cargó o el editor no apareció.")

        # C. Manejar Caption (Si existe)
        if caption:
            try:
                # Buscar input visible en el editor (evitar el input del chat de fondo)
                # El input del editor suele tener clases específicas, pero contenteditable es universal
                text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
                caption_box = None
                
                # Iterar para encontrar el que está visible y activo
                for inp in text_inputs:
                    if inp.is_displayed():
                        # Un check extra: altura razonable (el del chat fondo a veces reporta displayed)
                        if inp.size['height'] > 10: 
                            caption_box = inp
                            break
                
                if caption_box:
                    caption_box.click()
                    time.sleep(0.3)
                    # Escribir mensaje
                    for line in caption.split('\n'):
                        caption_box.send_keys(line)
                        caption_box.send_keys(Keys.SHIFT + Keys.ENTER)
                else:
                    print("⚠️ Warning: No se encontró cuadro de texto para el caption.")
            
            except Exception as e:
                print(f"⚠️ Error escribiendo caption (se enviará solo imagen): {e}")

        # D. ENVIAR (Click Prioritario)
        time.sleep(0.5) # Pequeña espera para que el botón se habilite tras escribir
        sent = False
        
        try:
            # 1. Intentar Click Nativo
            btn_send = self.wait.until(EC.element_to_be_clickable(send_icon_selector))
            btn_send.click()
            sent = True
        except ElementClickInterceptedException:
            # 2. Respaldo: Click Javascript (Si algo tapa el botón)
            try:
                btn_send = self.driver.find_element(*send_icon_selector)
                self.driver.execute_script("arguments[0].click();", btn_send)
                sent = True
            except: pass
        
        if not sent:
             # 3. Respaldo Final: Enter en el caption box
             try:
                 webdriver.ActionChains(self.driver).send_keys(Keys.ENTER).perform()
             except: pass

        # E. Validación de Salida
        try:
            # Esperar a que el botón de enviar DESAPAREZCA (significa que el editor se cerró)
            self.wait.until(EC.invisibility_of_element_located(send_icon_selector))
        except TimeoutException:
            raise Exception("❌ Error Crítico: El mensaje se quedó trabado en el editor (No se envió).")

    def _send_text_only(self, message):
        """Envío robusto para solo texto"""
        box_selector = (By.CSS_SELECTOR, "#main footer div[contenteditable='true']")
        try:
            chat_box = self.wait.until(EC.element_to_be_clickable(box_selector))
            chat_box.click()
            
            # Limpiar y Escribir
            chat_box.send_keys(Keys.CONTROL + "a")
            chat_box.send_keys(Keys.BACKSPACE)
            
            lines = message.split('\n')
            for i, line in enumerate(lines):
                chat_box.send_keys(line)
                if i < len(lines) - 1:
                    chat_box.send_keys(Keys.SHIFT + Keys.ENTER)
            
            time.sleep(0.5)
            chat_box.send_keys(Keys.ENTER)
            
            # Confirmar envío (caja vacía)
            WebDriverWait(self.driver, 3).until(lambda d: chat_box.text.strip() == "")
            
        except Exception:
            # Fallback Click
            try:
                self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Send'], span[data-icon='send']").click()
            except:
                pass

    def close(self):
        if self.driver:
            self.driver.quit()