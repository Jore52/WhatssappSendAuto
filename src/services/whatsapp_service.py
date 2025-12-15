import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import config

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None

    def start_browser(self):
        """Inicia el navegador Chrome con opciones optimizadas"""
        opts = Options()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-infobars")
        opts.add_argument(f"user-data-dir={config.USER_DATA_DIR}")
        # Evita errores de renderizado en algunos sistemas
        opts.add_argument("--disable-gpu") 
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.wait = WebDriverWait(self.driver, 20) # Aumentado timeout global
        self.driver.get("https://web.whatsapp.com")

    def is_logged_in(self):
        """Verifica login buscando el panel lateral"""
        try:
            return len(self.driver.find_elements(By.ID, "pane-side")) > 0
        except:
            return False

    def get_qr_screenshot(self, save_path="temp_qr.png"):
        """Captura el canvas del QR"""
        try:
            qr = self.driver.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!'], div[data-ref]")
            if qr:
                qr[0].screenshot(save_path)
                return True
        except:
            pass
        return False

    def reload_qr(self):
        """Intenta recargar el QR si expiró"""
        try:
            self.driver.find_element(By.CSS_SELECTOR, "button, span[data-icon='refresh-large']").click()
        except: pass

    def send_message(self, phone, message, image_path=None):
        """
        Envía mensaje a un número.
        Maneja: Carga de chat, validación de número, escritura segura y confirmación.
        """
        clean_n = phone.replace("+", "").replace(" ", "").strip()
        if not clean_n.isdigit():
            raise Exception("Número mal formado")

        url = f"https://web.whatsapp.com/send?phone={clean_n}"
        self.driver.get(url)

        # 1. Detección de errores y carga (Loop de espera inteligente)
        try:
            # Esperamos o el input de chat O el popup de error
            self.wait.until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']") or 
                          d.find_elements(By.CSS_SELECTOR, "div[data-animate-modal-popup='true']")
            )
        except TimeoutException:
            raise Exception("Timeout esperando carga del chat")

        # 2. Verificar si es número inválido
        invalid_popups = self.driver.find_elements(By.CSS_SELECTOR, "div[data-animate-modal-popup='true']")
        if invalid_popups:
            # Intentamos leer el texto para estar seguros, pero la presencia del popup suele bastar
            text = invalid_popups[0].text.lower()
            if "url" in text or "invalid" in text or "inválido" in text:
                # Cerrar popup para no bloquear el siguiente
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "div[role='button']").click()
                except: pass
                raise Exception("Número Inválido (Popup detectado)")

        time.sleep(1) # Pequeña estabilización

        # 3. Enviar Imagen (Prioridad)
        if image_path and os.path.exists(image_path):
            self._send_attachment(image_path, message)
        
        # 4. Enviar Texto (Solo si hay mensaje y no se envió como caption de imagen)
        elif message:
            self._send_text_robust(message)
        
        time.sleep(1.5) # Pausa técnica post-envío

    def _send_attachment(self, path, caption):
        """Maneja subida de adjuntos"""
        # Input oculto para archivos
        input_box = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        input_box.send_keys(path)
        
        # Esperar a que cargue la vista previa de imagen
        send_btn_xpath = "//span[@data-icon='send']"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, send_btn_xpath)))
        
        if caption:
            # El foco suele estar en el input de caption
            try:
                caption_box = self.driver.switch_to.active_element
                # Escribimos el caption
                for line in caption.split('\n'):
                    caption_box.send_keys(line)
                    caption_box.send_keys(Keys.SHIFT + Keys.ENTER)
            except:
                print("No se pudo enfocar caption box")
        
        time.sleep(0.5)
        self.driver.find_element(By.XPATH, send_btn_xpath).click()
        # Esperar que desaparezca el editor de medios (confirmación de envío)
        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div[aria-label='Media Editor']")))

    def _send_text_robust(self, message):
        """Escribe y envía texto asegurando que el input está listo"""
        
        # Selector más robusto para el input de texto principal
        # Busca div contenteditable que tenga role textbox y esté en el panel principal
        input_selector = (By.CSS_SELECTOR, "#main div[contenteditable='true'][role='textbox']")
        
        chat_box = self.wait.until(EC.element_to_be_clickable(input_selector))
        chat_box.click()
        
        # Limpiar por seguridad (Ctrl+A -> Backspace)
        chat_box.send_keys(Keys.CONTROL + "a")
        chat_box.send_keys(Keys.BACKSPACE)
        
        # Escribir línea por línea
        for line in message.split('\n'):
            chat_box.send_keys(line)
            chat_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
        # Validar que se escribió algo antes de intentar enviar
        # (A veces Selenium escribe muy rápido y WA no registra el input)
        time.sleep(0.5)
        
        # Click en botón enviar
        btn_send_selector = (By.CSS_SELECTOR, "button[aria-label='Send'], span[data-icon='send']")
        btn_send = self.wait.until(EC.element_to_be_clickable(btn_send_selector))
        btn_send.click()

    def close(self):
        if self.driver:
            self.driver.quit()