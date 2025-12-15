import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from PIL import Image, ImageTk
import customtkinter as ctk

import config
from src.services.whatsapp_service import WhatsAppBot
from src.services.data_service import DataService

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Estado
        self.bot = WhatsAppBot()
        self.contacts_data = [] # Lista de dicts: {'id': 0, 'numero': '...', 'estado': '...', 'widgets': {...}}
        self.next_id = 0
        self.is_running = True
        self.is_sending = False
        self.image_path = None

        # Configuración Ventana
        self.title("WhatsApp Sender Pro - Modular")
        self.geometry("1100x750")
        ctk.set_appearance_mode(config.THEME_MODE)
        ctk.set_default_color_theme("blue")
        
        # Construir UI
        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_area()
        
        # Iniciar Hilo del Bot
        self.after(200, self.start_bot_thread)

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkScrollableFrame(self, width=280, corner_radius=0, fg_color="#E0E0E0", label_text="")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.main_frame = ctk.CTkFrame(self, fg_color="white")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

    def _setup_sidebar(self):
        # Logo, Botones Importar, Mensaje, Imagen, Botón Acción
        # (Código resumido de tu UI original, adaptado)
        ctk.CTkLabel(self.sidebar, text="🤖 WA Sender", font=("Roboto", 24, "bold"), text_color="#333").pack(pady=20)
        
        self.btn_excel = ctk.CTkButton(self.sidebar, text="📂 Excel", command=self.import_excel, fg_color=config.COLOR_PRIMARY)
        self.btn_excel.pack(pady=5, padx=10, fill="x")
        
        self.btn_pdf = ctk.CTkButton(self.sidebar, text="📄 PDF", command=self.import_pdf, fg_color="#e37400")
        self.btn_pdf.pack(pady=5, padx=10, fill="x")
        
        self.lbl_count = ctk.CTkLabel(self.sidebar, text="Contactos: 0", text_color="gray")
        self.lbl_count.pack()

        ctk.CTkLabel(self.sidebar, text="Mensaje:", text_color="#333").pack(pady=(10,0), anchor="w", padx=10)
        self.txt_msg = ctk.CTkTextbox(self.sidebar, height=100, fg_color="white", border_color="#ccc", border_width=1)
        self.txt_msg.pack(padx=10, fill="x")
        
        self.btn_img = ctk.CTkButton(self.sidebar, text="📷 Imagen", command=self.select_image)
        self.btn_img.pack(pady=10, padx=10, fill="x")
        self.lbl_img = ctk.CTkLabel(self.sidebar, text="", text_color="gray", font=("Arial", 10))
        self.lbl_img.pack()

        self.btn_run = ctk.CTkButton(self.sidebar, text="⏳ Iniciando...", state="disabled", command=self.start_sending, fg_color=config.COLOR_SUCCESS, height=50)
        self.btn_run.pack(pady=20, padx=10, side="bottom", fill="x")

    def _setup_main_area(self):
        # Area QR
        self.top_frame = ctk.CTkFrame(self.main_frame, height=250, fg_color="#f8f9fa")
        self.top_frame.grid(row=0, column=0, sticky="ew")
        
        self.qr_label = ctk.CTkLabel(self.top_frame, text="Cargando...", width=200, height=200, fg_color="white")
        self.qr_label.pack(pady=20)
        self.qr_label.bind("<Button-1>", lambda e: self.bot.reload_qr())

        # Area Tabla
        self.scroll_table = ctk.CTkScrollableFrame(self.main_frame, fg_color="white")
        self.scroll_table.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

    # --- LÓGICA DE UI ---
    def add_contact(self, number, status="Pendiente"):
        uid = self.next_id
        self.next_id += 1
        
        row = ctk.CTkFrame(self.scroll_table, fg_color="white", height=40)
        row.pack(fill="x", pady=1)
        
        ent = ctk.CTkEntry(row, border_width=0, fg_color="#f1f3f4")
        ent.insert(0, number)
        ent.pack(side="left", fill="x", expand=True, padx=5)
        
        lbl = ctk.CTkLabel(row, text=status, width=100)
        lbl.pack(side="left")
        
        # Guardamos referencias
        self.contacts_data.append({
            'id': uid, 'widgets': {'row': row, 'entry': ent, 'lbl': lbl},
            'estado': status
        })
        self.lbl_count.configure(text=f"Contactos: {len(self.contacts_data)}")

    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if path:
            nums = DataService.load_excel(path)
            for n in nums: self.add_contact(n)

    def import_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            nums = DataService.load_pdf(path)
            for n in nums: self.add_contact(n)

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Img", "*.jpg;*.png;*.jpeg")])
        if path:
            self.image_path = path
            self.lbl_img.configure(text=path.split("/")[-1])

    # --- HILOS DE CONTROL ---
    def start_bot_thread(self):
        threading.Thread(target=self._bot_init_process, daemon=True).start()

    def _bot_init_process(self):
        try:
            self.bot.start_browser()
            # Loop de vigilancia del QR
            while self.is_running:
                if self.bot.is_logged_in():
                    self.qr_label.configure(image=None, text="✅ CONECTADO", font=("Arial", 30))
                    self.btn_run.configure(state="normal", text="🚀 ENVIAR")
                    break
                
                # Actualizar QR en UI
                if self.bot.get_qr_screenshot():
                    try:
                        img = Image.open("temp_qr.png").resize((200, 200))
                        ph = ImageTk.PhotoImage(img)
                        self.qr_label.configure(image=ph, text="")
                        self.qr_label.image = ph
                    except: pass
                time.sleep(1)
        except Exception as e:
            print(e)

    def start_sending(self):
        self.is_sending = True
        self.btn_run.configure(state="disabled")
        threading.Thread(target=self._sending_process, daemon=True).start()

    def _sending_process(self):
        msg = self.txt_msg.get("0.0", "end").strip()
        
        for c in self.contacts_data:
            if not self.is_sending: break
            if c['estado'] == "Enviado ✅": continue
            
            # Update UI
            c['widgets']['lbl'].configure(text="Enviando...", text_color="orange")
            number = c['widgets']['entry'].get()
            
            try:
                self.bot.send_message(number, msg, self.image_path)
                c['estado'] = "Enviado ✅"
                c['widgets']['lbl'].configure(text="Enviado ✅", text_color="green")
            except Exception as e:
                print(e)
                c['widgets']['lbl'].configure(text="Error", text_color="red")
            
            time.sleep(3) # Anti-ban

        self.btn_run.configure(state="normal")
        self.is_sending = False
        messagebox.showinfo("Fin", "Proceso terminado")

    def on_close(self):
        self.is_running = False
        self.bot.close()
        self.destroy()