import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk

import config
from src.services.whatsapp_service import WhatsAppBot
from src.services.data_service import DataService

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- Estado ---
        self.bot = WhatsAppBot()
        self.contacts_data = [] # Lista de dicts: {'id': int, 'widgets': dict, 'estado': str}
        self.next_id = 0
        self.is_running = True
        self.is_sending = False
        self.image_path = None
        self.syncing_text = False # Flag para evitar bucles de sincronización

        # --- Configuración Ventana ---
        self.title("WhatsApp Sender Pro - Modular")
        self.geometry("1200x800")
        ctk.set_appearance_mode(config.THEME_MODE)
        ctk.set_default_color_theme("blue")
        
        # --- Eventos Globales ---
        self.bind("<Control-v>", self.handle_paste_event)

        # --- Construir UI ---
        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_area()
        
        # Iniciar Hilo del Bot
        self.after(200, self.start_bot_thread)

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkScrollableFrame(self, width=300, corner_radius=0, fg_color="#E0E0E0", label_text="")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Main Area
        self.main_frame = ctk.CTkFrame(self, fg_color="white")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(2, weight=1) # La tabla se expande
        self.main_frame.grid_columnconfigure(0, weight=1)

    def _setup_sidebar(self):
        ctk.CTkLabel(self.sidebar, text="🤖 WA Sender", font=("Roboto", 24, "bold"), text_color="#333").pack(pady=20)
        
        # --- Botones Importar ---
        self.btn_excel = ctk.CTkButton(self.sidebar, text="📂 Importar Excel", command=self.import_excel, fg_color=config.COLOR_PRIMARY)
        self.btn_excel.pack(pady=5, padx=10, fill="x")
        
        self.btn_pdf = ctk.CTkButton(self.sidebar, text="📄 Importar PDF", command=self.import_pdf, fg_color="#e37400")
        self.btn_pdf.pack(pady=5, padx=10, fill="x")

        self.btn_paste = ctk.CTkButton(self.sidebar, text="📋 Pegar del Portapapeles", command=self.paste_from_button, fg_color="#555")
        self.btn_paste.pack(pady=5, padx=10, fill="x")
        
        self.lbl_count = ctk.CTkLabel(self.sidebar, text="Contactos: 0", text_color="gray")
        self.lbl_count.pack(pady=(10, 5))

        # --- Área de Mensaje (Editor) ---
        ctk.CTkLabel(self.sidebar, text="Mensaje (usa {nombre}):", text_color="#333", anchor="w").pack(pady=(10,0), padx=10, fill="x")
        
        self.txt_msg = ctk.CTkTextbox(self.sidebar, height=150, fg_color="white", border_color="#ccc", border_width=1)
        self.txt_msg.pack(padx=10, fill="x")
        self.txt_msg.bind("<KeyRelease>", self.sync_preview_from_input)

        # --- Selección de Imagen ---
        self.btn_img = ctk.CTkButton(self.sidebar, text="📷 Seleccionar Imagen", command=self.select_image)
        self.btn_img.pack(pady=10, padx=10, fill="x")
        self.lbl_img = ctk.CTkLabel(self.sidebar, text="Sin imagen", text_color="gray", font=("Arial", 10))
        self.lbl_img.pack()

        # --- Botón Enviar ---
        self.btn_run = ctk.CTkButton(self.sidebar, text="⏳ Iniciando Motor...", state="disabled", command=self.start_sending, fg_color=config.COLOR_SUCCESS, height=50)
        self.btn_run.pack(pady=20, padx=10, side="bottom", fill="x")

    def _setup_main_area(self):
        # 1. Área Superior (QR y Estado)
        self.top_frame = ctk.CTkFrame(self.main_frame, height=180, fg_color="#f8f9fa")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.qr_label = ctk.CTkLabel(self.top_frame, text="Cargando QR...", width=150, height=150, fg_color="#ddd", corner_radius=10)
        self.qr_label.pack(side="left", padx=20, pady=10)
        self.qr_label.bind("<Button-1>", lambda e: self.bot.reload_qr())

        # Instrucciones
        info_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="y", pady=10)
        ctk.CTkLabel(info_frame, text="Estado del Bot:", font=("Arial", 14, "bold"), text_color="#333").pack(anchor="w")
        self.lbl_status_bot = ctk.CTkLabel(info_frame, text="Desconectado", text_color="red")
        self.lbl_status_bot.pack(anchor="w")

        # 2. Área Vista Previa (Editable y Sincronizada)
        self.preview_frame = ctk.CTkFrame(self.main_frame, fg_color="white", border_width=1, border_color="#eee")
        self.preview_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        ctk.CTkLabel(self.preview_frame, text="Vista Previa Mensaje:", text_color="gray", font=("Arial", 11)).pack(anchor="w", padx=10, pady=(5,0))
        
        self.preview_box = ctk.CTkTextbox(self.preview_frame, height=60, fg_color="#e5fada", text_color="#333", activate_scrollbars=False)
        self.preview_box.pack(padx=10, pady=5, fill="x")
        self.preview_box.bind("<KeyRelease>", self.auto_resize_preview) # Sincronización inversa opcional

        # 3. Área Tabla (Encabezados + Scroll)
        self.table_header = ctk.CTkFrame(self.main_frame, height=30, fg_color="#333")
        self.table_header.grid(row=2, column=0, sticky="ew", padx=20, pady=(10,0))
        
        # Headers
        headers = [("Número", 0.3), ("Nombre (Opcional)", 0.3), ("Estado", 0.2), ("Acción", 0.1)]
        for text, weight in headers:
            lbl = ctk.CTkLabel(self.table_header, text=text, text_color="white", font=("Arial", 12, "bold"))
            lbl.pack(side="left", fill="x", expand=True, padx=2)

        self.scroll_table = ctk.CTkScrollableFrame(self.main_frame, fg_color="#fdfdfd")
        self.scroll_table.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 10))


    # --- LÓGICA DE UI Y TABLA ---
    
    def add_contact(self, number, name="", status="Pendiente"):
        uid = self.next_id
        self.next_id += 1
        
        row = ctk.CTkFrame(self.scroll_table, fg_color="white", height=40)
        row.pack(fill="x", pady=1)
        
        # Input Número
        ent_num = ctk.CTkEntry(row, border_width=1, fg_color="#f1f3f4", placeholder_text="Ej: 51999...")
        ent_num.insert(0, str(number))
        ent_num.pack(side="left", fill="x", expand=True, padx=2)
        
        # Input Nombre
        ent_name = ctk.CTkEntry(row, border_width=1, fg_color="#fff", placeholder_text="Nombre...")
        ent_name.insert(0, str(name))
        ent_name.pack(side="left", fill="x", expand=True, padx=2)
        
        # Label Estado
        lbl_stat = ctk.CTkLabel(row, text=status, width=100)
        lbl_stat.pack(side="left", padx=2)
        
        # Botón Acción (Eliminar)
        btn_del = ctk.CTkButton(row, text="✖", width=30, fg_color="#ff4444", 
                                command=lambda: self.delete_row(uid, row))
        btn_del.pack(side="left", padx=5)
        
        # Guardar Referencia
        self.contacts_data.append({
            'id': uid,
            'widgets': {'row': row, 'entry_num': ent_num, 'entry_name': ent_name, 'lbl_stat': lbl_stat},
            'estado': status
        })
        self.update_count()

    def delete_row(self, uid, row_widget):
        row_widget.destroy()
        self.contacts_data = [c for c in self.contacts_data if c['id'] != uid]
        self.update_count()

    def update_count(self):
        self.lbl_count.configure(text=f"Contactos: {len(self.contacts_data)}")

    def handle_paste_event(self, event):
        self.paste_contacts()

    def paste_from_button(self):
        self.paste_contacts()

    def paste_contacts(self):
        try:
            content = self.clipboard_get()
            rows = content.strip().split('\n')
            
            count = 0
            for row_str in rows:
                if not row_str.strip(): continue
                # Detectar separadores (Tab para Excel, Coma para CSV simple, o espacio)
                if '\t' in row_str:
                    parts = row_str.split('\t')
                    num = parts[0]
                    name = parts[1] if len(parts) > 1 else ""
                elif ',' in row_str:
                    parts = row_str.split(',')
                    num = parts[0]
                    name = parts[1] if len(parts) > 1 else ""
                else:
                    num = row_str
                    name = ""
                
                # Limpiar
                num = num.strip()
                name = name.strip()
                if num:
                    self.add_contact(num, name)
                    count += 1
            
            if count > 0:
                messagebox.showinfo("Pegado", f"Se agregaron {count} contactos.")
        except Exception as e:
            pass # Clipboard vacío o error de formato

    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if path:
            data = DataService.load_excel(path) # Asumiendo que ahora devuelve tuplas o dicts si se mejora DataService
            # Si DataService devuelve solo lista de nums, adaptamos:
            for item in data:
                if isinstance(item, tuple) or isinstance(item, list):
                    self.add_contact(item[0], item[1] if len(item)>1 else "")
                else:
                    self.add_contact(item)

    def import_pdf(self):
        # Mantiene lógica simple original
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            nums = DataService.load_pdf(path)
            for n in nums: self.add_contact(n)

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Img", "*.jpg;*.png;*.jpeg")])
        if path:
            self.image_path = path
            self.lbl_img.configure(text=path.split("/")[-1])

    # --- Sincronización Vista Previa ---
    def sync_preview_from_input(self, event=None):
        if self.syncing_text: return
        self.syncing_text = True
        
        text = self.txt_msg.get("0.0", "end").strip()
        
        # Actualizar preview
        self.preview_box.delete("0.0", "end")
        self.preview_box.insert("0.0", text)
        self.auto_resize_preview()
        
        self.syncing_text = False

    def auto_resize_preview(self, event=None):
        # Lógica para sincronizar edición inversa si se desea
        text = self.preview_box.get("0.0", "end")
        num_lines = int(self.preview_box.index('end-1c').split('.')[0])
        # Ajustar altura (aprox 20px por linea)
        new_height = min(max(60, num_lines * 20), 150)
        self.preview_box.configure(height=new_height)

    # --- HILOS DE CONTROL ---
    def start_bot_thread(self):
        threading.Thread(target=self._bot_init_process, daemon=True).start()

    def _bot_init_process(self):
        try:
            self.bot.start_browser()
            while self.is_running:
                if self.bot.is_logged_in():
                    self.qr_label.configure(image=None, text="✅", font=("Arial", 50))
                    self.lbl_status_bot.configure(text="Conectado ✅", text_color="green")
                    self.btn_run.configure(state="normal", text="🚀 ENVIAR MENSAJES")
                    break
                
                if self.bot.get_qr_screenshot():
                    try:
                        img = Image.open("temp_qr.png").resize((180, 180))
                        ph = ImageTk.PhotoImage(img)
                        self.qr_label.configure(image=ph, text="")
                        self.qr_label.image = ph
                    except: pass
                time.sleep(1)
        except Exception as e:
            self.lbl_status_bot.configure(text=f"Error: {str(e)}", text_color="red")

    def start_sending(self):
        if not self.contacts_data:
            messagebox.showwarning("Vacío", "No hay contactos para enviar.")
            return

        self.is_sending = True
        self.btn_run.configure(state="disabled", text="Enviando...")
        threading.Thread(target=self._sending_process, daemon=True).start()

    def _sending_process(self):
        base_msg = self.txt_msg.get("0.0", "end").strip()
        
        for c in self.contacts_data:
            if not self.is_sending: break
            if c['estado'] == "Enviado ✅": continue
            
            # Obtener datos frescos de la UI
            number = c['widgets']['entry_num'].get().strip()
            name = c['widgets']['entry_name'].get().strip()
            
            # Update UI
            c['widgets']['lbl_stat'].configure(text="Enviando...", text_color="orange")
            self.scroll_table.update_idletasks() # Forzar refresco UI
            
            try:
                # Personalización del mensaje
                final_msg = base_msg.replace("{nombre}", name)
                
                self.bot.send_message(number, final_msg, self.image_path)
                
                c['estado'] = "Enviado ✅"
                c['widgets']['lbl_stat'].configure(text="Enviado ✅", text_color="green")
            except Exception as e:
                print(f"Error con {number}: {e}")
                c['estado'] = "Error ❌"
                c['widgets']['lbl_stat'].configure(text="Error ❌", text_color="red")
            
            time.sleep(2) # Pausa entre mensajes

        self.btn_run.configure(state="normal", text="🚀 ENVIAR MENSAJES")
        self.is_sending = False
        messagebox.showinfo("Fin", "Proceso de envío terminado")

    def on_close(self):
        self.is_running = False
        self.bot.close()
        self.destroy()