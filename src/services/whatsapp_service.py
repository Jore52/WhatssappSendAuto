import time
import os
import sys
import subprocess
import platform
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import config

# --- CONFIGURACIÓN DE LOGS ---
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOG_FILE = os.path.join(ROOT_DIR, "registro_bot.txt")

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.os_name = platform.system()

    def start_browser(self):
        log("Iniciando navegador...")
        opts = Options()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-infobars")
        opts.add_argument(f"user-data-dir={config.USER_DATA_DIR}")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--ignore-certificate-errors")
        
        opts.add_experimental_option("prefs", {
            "profile.default_content_setting_values.clipboard": 1
        })

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.wait = WebDriverWait(self.driver, config.WAIT_TIMEOUT)
        self.driver.get("https://web.whatsapp.com")
        log("Navegador abierto.")

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
        log(f"--- Iniciando envío a {phone} ---")
        clean_n = phone.replace("+", "").replace(" ", "").strip()
        if not clean_n.isdigit():
            raise Exception("Número mal formado")

        url = f"https://web.whatsapp.com/send?phone={clean_n}"
        self.driver.get(url)

        try:
            self.wait.until(
                lambda d: d.find_elements(By.ID, "main") or 
                          d.find_elements(By.CSS_SELECTOR, "div[data-animate-modal-popup='true']")
            )
            log("Chat cargado.")
        except TimeoutException:
            log("Error: Timeout esperando carga del chat")
            raise Exception("Timeout esperando carga del chat")

        time.sleep(1)
        invalid = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'inválido') or contains(text(), 'invalid')]")
        if invalid:
            log("Número inválido.")
            try: invalid[0].find_element(By.CSS_SELECTOR, "div[role='button']").click()
            except: pass
            raise Exception("Número Inválido")

        if image_path and os.path.exists(image_path):
            self._send_attachment(image_path, message)
        elif message:
            self._send_text_only(message)
        
        log("--- Envío finalizado ---")
        time.sleep(1)

    def _copy_image_to_clipboard(self, image_path):
        abs_path = os.path.abspath(image_path)
        log(f"Copiando imagen: {abs_path}")
        if self.os_name == 'Windows':
            cmd = f"powershell -c \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_path}'))\""
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif self.os_name == 'Darwin':
            cmd = f"osascript -e 'tell application \"Finder\" to set the clipboard to (POSIX file \"{abs_path}\")'"
            subprocess.run(cmd, shell=True, check=True)
        elif self.os_name == 'Linux':
            mime = "image/png" if abs_path.lower().endswith(".png") else "image/jpeg"
            subprocess.run(["xclip", "-selection", "clipboard", "-t", mime, "-i", abs_path], check=True)

    def _copy_text_to_clipboard(self, text):
        log("Copiando texto...")
        if self.os_name == 'Windows':
            text_b64 = base64.b64encode(text.encode('utf-16le')).decode()
            cmd = f"powershell -c \"$str = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('{text_b64}')); Set-Clipboard -Value $str\""
            subprocess.run(cmd, shell=True)
        elif self.os_name == 'Darwin':
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p.communicate(input=text.encode('utf-8'))
        elif self.os_name == 'Linux':
            p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            p.communicate(input=text.encode('utf-8'))

    def _send_attachment(self, path, caption):
        """Flujo estricto: Pegar Imagen -> VALIDAR MODAL -> Pegar Texto -> Enter"""
        modifier = Keys.COMMAND if self.os_name == 'Darwin' else Keys.CONTROL
        
        # 1. PEGAR IMAGEN
        try:
            self._copy_image_to_clipboard(path)
            time.sleep(1.0)
            
            # Click en chat principal
            log("Enfocando chat principal...")
            main_chat_box = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#main footer div[contenteditable='true']")))
            main_chat_box.click()
            time.sleep(0.5)
            
            log("Pegando imagen (Ctrl+V)...")
            actions = ActionChains(self.driver)
            actions.key_down(modifier).send_keys('v').key_up(modifier).perform()
            
        except Exception as e:
            log(f"Error pegando imagen: {e}")
            raise Exception(f"Fallo imagen: {e}")

        # 2. ESPERAR AL EDITOR (CRÍTICO)
        # Esperamos a que aparezca un input de texto que NO sea el del chat principal.
        # Esto confirma que el modal se abrió.
        log("Esperando a que se abra el editor de imagen...")
        modal_opened = False
        try:
            # Buscamos un contenteditable que NO tenga ancestro 'main'
            # Ojo: El editor de imagen vive fuera de #main
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][not(ancestor::div[@id='main'])]"))
            )
            log("¡Editor de imagen detectado!")
            modal_opened = True
        except TimeoutException:
            log("ALERTA: No se detectó el editor de imagen en 10s. Posiblemente la imagen no se pegó.")
            # Si no abre el modal, no intentamos pegar el texto para evitar enviarlo al chat equivocado
            raise Exception("La imagen no cargó el editor. Abortando envío de texto.")

        # 3. PEGAR TEXTO (Solo si el modal abrió)
        if caption and modal_opened:
            try:
                log("Copiando caption al portapapeles...")
                self._copy_text_to_clipboard(caption)
                time.sleep(1.0) # Tiempo para que el SO cambie el portapapeles
                
                # Buscar el input DEL MODAL (Excluyendo el del chat principal)
                caption_box = self.driver.find_element(By.XPATH, "//div[@contenteditable='true'][not(ancestor::div[@id='main'])]")
                
                if caption_box:
                    log("Enfocando input del caption...")
                    caption_box.click()
                    time.sleep(0.5)
                    
                    # Verificamos foco activo por si acaso
                    active_elem = self.driver.switch_to.active_element
                    if active_elem != caption_box:
                        log("El foco no estaba en el caption, forzando con JS...")
                        self.driver.execute_script("arguments[0].focus();", caption_box)
                    
                    log("Pegando texto en la descripción...")
                    actions = ActionChains(self.driver)
                    actions.key_down(modifier).send_keys('v').key_up(modifier).perform()
                    time.sleep(1.0) 
                    
                    log("Enviando ENTER...")
                    actions.send_keys(Keys.ENTER).perform()
                else:
                    log("No se encontró el input del caption en el modal.")

            except Exception as e:
                log(f"Error pegando texto: {e}")

        elif not caption and modal_opened:
            # Solo imagen, dar enter
            log("Sin caption. Enviando imagen...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

        # 4. VALIDAR ENVÍO
        time.sleep(2)
        # Si el editor sigue abierto (botón send visible), hacemos click
        try:
            send_btn = self.driver.find_elements(By.CSS_SELECTOR, "span[data-icon='send']")
            # Filtramos los visibles
            visible_btns = [btn for btn in send_btn if btn.is_displayed()]
            if visible_btns:
                log("El mensaje no se fue con Enter. Haciendo click en botón enviar...")
                visible_btns[-1].click()
        except: pass

        log("Proceso de adjunto finalizado.")

    def _send_text_only(self, message):
        try:
            box = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#main footer div[contenteditable='true']")))
            box.click()
            box.send_keys(Keys.CONTROL + "a")
            box.send_keys(Keys.BACKSPACE)
            
            self._copy_text_to_clipboard(message)
            modifier = Keys.COMMAND if self.os_name == 'Darwin' else Keys.CONTROL
            
            actions = ActionChains(self.driver)
            actions.key_down(modifier).send_keys('v').key_up(modifier).perform()
            time.sleep(0.5)
            actions.send_keys(Keys.ENTER).perform()
            log("Texto enviado.")
        except Exception as e:
            log(f"Error texto: {e}")

    def close(self):
        log("Cerrando.")
        if self.driver:
            self.driver.quit()