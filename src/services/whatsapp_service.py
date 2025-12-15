import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import config

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None

    def start_browser(self):
        """Inicia el navegador Chrome"""
        opts = Options()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-infobars")
        opts.add_argument(f"user-data-dir={config.USER_DATA_DIR}")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.wait = WebDriverWait(self.driver, config.WAIT_TIMEOUT)
        self.driver.get("https://web.whatsapp.com")

    def is_logged_in(self):
        """Verifica si ya cargó la lista de chats"""
        try:
            return len(self.driver.find_elements(By.ID, "pane-side")) > 0
        except:
            return False

    def get_qr_screenshot(self, save_path="temp_qr.png"):
        """Busca el QR y toma captura si existe"""
        try:
            qr = self.driver.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!'], div[data-ref]")
            if qr:
                qr[0].screenshot(save_path)
                return True
        except:
            pass
        return False

    def reload_qr(self):
        try:
            self.driver.find_element(By.CSS_SELECTOR, "button, span[data-icon='refresh-large']").click()
        except: pass

    def send_message(self, phone, message, image_path=None):
        """Lógica central de envío"""
        clean_n = phone.replace("+", "").replace(" ", "")
        url = f"https://web.whatsapp.com/send?phone={clean_n}"
        self.driver.get(url)

        # 1. Esperar carga del chat
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")))
        except TimeoutException:
            # Verificar si es número inválido
            if len(self.driver.find_elements(By.XPATH, "//div[contains(text(), 'url')]")) > 0:
                raise Exception("Número Inválido")
            raise Exception("Timeout carga chat")

        time.sleep(1)

        # 2. Enviar Imagen (Si existe)
        if image_path and os.path.exists(image_path):
            self._send_attachment(image_path, message)
        
        # 3. Enviar Texto (Solo si no se envió imagen con caption o es solo texto)
        elif message:
            self._send_text_only(message)
        
        time.sleep(2) # Pausa técnica

    def _send_attachment(self, path, caption):
        input_box = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        input_box.send_keys(path)
        
        # Esperar modal
        send_btn_xpath = "//span[@data-icon='send']"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, send_btn_xpath)))
        
        if caption:
            # Lógica para escribir caption
            caption_box = self.driver.switch_to.active_element
            # Simple typing
            for line in caption.split('\n'):
                caption_box.send_keys(line)
                caption_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
        time.sleep(1)
        self.driver.find_element(By.XPATH, send_btn_xpath).click()
        # Esperar que suba
        self.wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'media-editor')]")))

    def _send_text_only(self, message):
        chat_box = self.driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")
        chat_box.click()
        for line in message.split('\n'):
            chat_box.send_keys(line)
            chat_box.send_keys(Keys.SHIFT + Keys.ENTER)
        time.sleep(0.5)
        chat_box.send_keys(Keys.ENTER)

    def close(self):
        if self.driver:
            self.driver.quit()