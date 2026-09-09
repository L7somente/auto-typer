import os, sys, time, threading, datetime as dt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageGrab, ImageTk

try:
    import pyautogui
except ImportError:
    pyautogui = None
try:
    import pyperclip
except ImportError:
    pyperclip = None

APP_NAME = "Auto Typer"
APP_VERSION = "1.0.0"
DEFAULT_CONFIDENCE = 0.80
RETRY_INTERVAL_SECONDS = 1.5
RETRY_TIMEOUT_SECONDS = 30
CLICK_TO_TYPE_DELAY = 0.35

C = {
    "bg":"#0B1020","surface":"#11182A","surface2":"#151E33","hover":"#1A2640",
    "border":"#263451","primary":"#6D7CFF","primary2":"#8190FF","success":"#2AC769",
    "danger":"#FF5C70","warning":"#FFBE55","text":"#F4F7FF","muted":"#9AA7C2",
    "soft":"#72809B","input":"#0E1628"
}

class RegionCaptureOverlay:
    def __init__(self, master, on_captured):
        self.on_captured = on_captured
        self.start_x = self.start_y = 0
        self.rect_id = None
        self.top = tk.Toplevel(master)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.32)
        self.top.configure(bg="black")
        w, h = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        self.top.geometry(f"{w}x{h}+0+0")
        self.canvas = tk.Canvas(self.top, bg="#111827", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        tk.Label(self.top, text="Arraste para selecionar o campo  •  ESC para cancelar",
                 bg=C["surface"], fg="white", font=("Segoe UI",12,"bold"), padx=18, pady=10
        ).place(relx=.5, y=24, anchor="n")
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.top.bind("<Escape>", lambda _e: self.top.destroy())
        self.top.focus_force()

    def _press(self, e):
        self.start_x, self.start_y = e.x, e.y
        if self.rect_id: self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(e.x,e.y,e.x,e.y,outline=C["primary"],width=3)

    def _drag(self, e):
        if self.rect_id:
            self.canvas.coords(self.rect_id,self.start_x,self.start_y,e.x,e.y)

    def _release(self, e):
        left, right = sorted((self.start_x, e.x)); top, bottom = sorted((self.start_y, e.y))
        if right-left < 5 or bottom-top < 5:
            self.top.destroy(); return
        self.top.withdraw(); self.top.update(); time.sleep(.25)
        img = ImageGrab.grab(bbox=(left,top,right,bottom))
        self.top.destroy(); self.on_captured(img)

class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        root.title(f"{APP_NAME} • Automação agendada")
        root.geometry("760x820"); root.minsize(720,760); root.configure(bg=C["bg"])
        self.image_path = tk.StringVar()
        self.time_str = tk.StringVar(value=self._now_plus(1))
        self.confidence = tk.DoubleVar(value=DEFAULT_CONFIDENCE)
        self.status_text = tk.StringVar(value="Pronto para configurar")
        self.cancel_event = threading.Event(); self.worker_thread = None; self.preview_photo = None
        self._styles(); self._ui(); self._check_dependencies()

    def _styles(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except tk.TclError: pass
        for name,bg in [("App",C["bg"]),("Card",C["surface"])]: s.configure(f"{name}.TFrame",background=bg)
        s.configure("Title.TLabel",background=C["bg"],foreground=C["text"],font=("Segoe UI",24,"bold"))
        s.configure("Subtitle.TLabel",background=C["bg"],foreground=C["muted"],font=("Segoe UI",10))
        s.configure("CardTitle.TLabel",background=C["surface"],foreground=C["text"],font=("Segoe UI",11,"bold"))
        s.configure("CardText.TLabel",background=C["surface"],foreground=C["muted"],font=("Segoe UI",9))
        s.configure("Meta.TLabel",background=C["bg"],foreground=C["soft"],font=("Segoe UI",8))
        s.configure("Primary.TButton",font=("Segoe UI",10,"bold"),padding=(16,10),background=C["primary"],foreground="white",borderwidth=0)
        s.map("Primary.TButton",background=[("active",C["primary2"]),("disabled","#36405E")])
        s.configure("Secondary.TButton",font=("Segoe UI",9,"bold"),padding=(12,8),background=C["surface2"],foreground=C["text"],borderwidth=0)
        s.map("Secondary.TButton",background=[("active",C["hover"])])
        s.configure("Danger.TButton",font=("Segoe UI",10,"bold"),padding=(16,10),background="#3A1C2A",foreground="#FF9AAA",borderwidth=0)
        s.map("Danger.TButton",background=[("active","#4A2031"),("disabled","#262C3B")])
        s.configure("Modern.Horizontal.TScale",background=C["surface"],troughcolor=C["input"])

    def _card(self,parent):
        return tk.Frame(parent,bg=C["surface"],highlightthickness=1,highlightbackground=C["border"])

    def _section(self,parent,title,subtitle):
        tk.Label(parent,text=title,bg=C["surface"],fg=C["text"],font=("Segoe UI",11,"bold")).pack(anchor="w",padx=18,pady=(15,2))
        tk.Label(parent,text=subtitle,bg=C["surface"],fg=C["muted"],font=("Segoe UI",9)).pack(anchor="w",padx=18,pady=(0,8))

    def _ui(self):
        outer = ttk.Frame(self.root,style="App.TFrame",padding=(28,24)); outer.pack(fill="both",expand=True)
        header = ttk.Frame(outer,style="App.TFrame"); header.pack(fill="x",pady=(0,18))
        hw = ttk.Frame(header,style="App.TFrame"); hw.pack(side="left",fill="x",expand=True)
        ttk.Label(hw,text=APP_NAME,style="Title.TLabel").pack(anchor="w")
        ttk.Label(hw,text="Automação visual agendada para preencher campos na tela.",style="Subtitle.TLabel").pack(anchor="w",pady=(3,0))
        tk.Label(header,text=f"v{APP_VERSION}",bg=C["surface2"],fg=C["muted"],font=("Segoe UI",8,"bold"),padx=10,pady=5).pack(side="right",anchor="n")

        card = self._card(outer); card.pack(fill="x",pady=(0,12)); self._section(card,"1  Imagem de referência","Selecione uma imagem ou capture o campo diretamente da tela.")
        body = ttk.Frame(card,style="Card.TFrame"); body.pack(fill="x",padx=18,pady=(4,18))
        pf = tk.Frame(body,bg=C["input"],width=118,height=74,highlightthickness=1,highlightbackground=C["border"]); pf.pack(side="left",padx=(0,14)); pf.pack_propagate(False)
        self.preview_label = tk.Label(pf,text="SEM\nIMAGEM",bg=C["input"],fg=C["soft"],font=("Segoe UI",8,"bold")); self.preview_label.pack(fill="both",expand=True)
        actions = ttk.Frame(body,style="Card.TFrame"); actions.pack(side="left",fill="both",expand=True)
        self.image_name_label = ttk.Label(actions,text="Nenhuma imagem selecionada",style="CardTitle.TLabel"); self.image_name_label.pack(anchor="w",pady=(2,8))
        row = ttk.Frame(actions,style="Card.TFrame"); row.pack(anchor="w")
        ttk.Button(row,text="Selecionar arquivo",command=self._select_file,style="Secondary.TButton").pack(side="left",padx=(0,8))
        ttk.Button(row,text="Capturar da tela",command=self._capture_region,style="Secondary.TButton").pack(side="left")

        card = self._card(outer); card.pack(fill="x",pady=(0,12)); self._section(card,"2  Texto a ser enviado","Esse conteúdo será colado quando o horário chegar.")
        self.text_box = tk.Text(card,height=4,wrap="word",bg=C["input"],fg=C["text"],insertbackground=C["text"],selectbackground=C["primary"],relief="flat",highlightthickness=1,highlightbackground=C["border"],highlightcolor=C["primary"],font=("Segoe UI",10),padx=12,pady=10)
        self.text_box.pack(fill="x",padx=18,pady=(4,18))

        card = self._card(outer); card.pack(fill="x",pady=(0,12))
        split = ttk.Frame(card,style="Card.TFrame"); split.pack(fill="x",padx=18,pady=18); split.columnconfigure(0,weight=1); split.columnconfigure(1,weight=1)
        left = ttk.Frame(split,style="Card.TFrame"); left.grid(row=0,column=0,sticky="nsew",padx=(0,18))
        right = ttk.Frame(split,style="Card.TFrame"); right.grid(row=0,column=1,sticky="nsew")
        ttk.Label(left,text="3  Horário",style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(left,text="Formato HH:MM ou HH:MM:SS",style="CardText.TLabel").pack(anchor="w",pady=(2,8))
        tk.Entry(left,textvariable=self.time_str,bg=C["input"],fg=C["text"],insertbackground=C["text"],relief="flat",highlightthickness=1,highlightbackground=C["border"],highlightcolor=C["primary"],font=("Segoe UI",15,"bold"),justify="center").pack(fill="x",ipady=8)
        ttk.Label(right,text="4  Reconhecimento",style="CardTitle.TLabel").pack(anchor="w")
        line = ttk.Frame(right,style="Card.TFrame"); line.pack(fill="x",pady=(4,0))
        ttk.Label(line,text="Sensibilidade",style="CardText.TLabel").pack(side="left")
        self.conf_value_label = tk.Label(line,text="80%",bg=C["surface"],fg=C["primary2"],font=("Segoe UI",9,"bold")); self.conf_value_label.pack(side="right")
        ttk.Scale(right,from_=.5,to=1.0,variable=self.confidence,orient="horizontal",style="Modern.Horizontal.TScale",command=self._confidence_changed).pack(fill="x",pady=(8,0))
        ttk.Label(right,text="Menor = tolerante • Maior = preciso",style="CardText.TLabel").pack(anchor="w",pady=(6,0))

        row = ttk.Frame(outer,style="App.TFrame"); row.pack(fill="x",pady=(2,12))
        self.btn_start = ttk.Button(row,text="Agendar automação",command=self._start_schedule,style="Primary.TButton"); self.btn_start.pack(side="left")
        self.btn_cancel = ttk.Button(row,text="Cancelar",command=self._cancel_schedule,state="disabled",style="Danger.TButton"); self.btn_cancel.pack(side="left",padx=(10,0))

        self.status_bar = tk.Frame(outer,bg=C["surface"],highlightthickness=1,highlightbackground=C["border"]); self.status_bar.pack(fill="x",pady=(0,12))
        self.status_dot = tk.Label(self.status_bar,text="●",bg=C["surface"],fg=C["soft"],font=("Segoe UI",10)); self.status_dot.pack(side="left",padx=(14,8),pady=10)
        tk.Label(self.status_bar,textvariable=self.status_text,bg=C["surface"],fg=C["muted"],font=("Segoe UI",9,"bold")).pack(side="left",pady=10)

        card = self._card(outer); card.pack(fill="both",expand=True); self._section(card,"Atividade","Acompanhe o que o Auto Typer está fazendo.")
        self.log_box = scrolledtext.ScrolledText(card,height=8,state="disabled",bg=C["input"],fg=C["muted"],insertbackground=C["text"],relief="flat",highlightthickness=1,highlightbackground=C["border"],font=("Consolas",9),padx=10,pady=8)
        self.log_box.pack(fill="both",expand=True,padx=18,pady=(4,18))
        ttk.Label(outer,text="Dica: mantenha o campo de referência visível no horário agendado.",style="Meta.TLabel").pack(anchor="center",pady=(12,0))

    def _now_plus(self, minutes):
        return (dt.datetime.now()+dt.timedelta(minutes=minutes)).strftime("%H:%M:%S")

    def _confidence_changed(self,_=None):
        self.conf_value_label.config(text=f"{int(self.confidence.get()*100)}%")

    def _set_status(self,msg,kind="idle"):
        colors={"idle":C["soft"],"running":C["primary2"],"success":C["success"],"warning":C["warning"],"error":C["danger"]}
        self.status_text.set(msg); self.status_dot.config(fg=colors.get(kind,C["soft"]))

    def _log(self,msg):
        self.log_box.config(state="normal"); self.log_box.insert("end",f"[{dt.datetime.now().strftime('%H:%M:%S')}]  {msg}\n"); self.log_box.see("end"); self.log_box.config(state="disabled")

    def _check_dependencies(self):
        missing=[]
        if pyautogui is None: missing.append("pyautogui")
        if pyperclip is None: missing.append("pyperclip")
        if missing:
            self._set_status("Dependências ausentes","warning"); self._log("AVISO: instale com python -m pip install -r requirements.txt")

    def _update_preview(self,path):
        try:
            img=Image.open(path); img.thumbnail((112,68),Image.Resampling.LANCZOS); self.preview_photo=ImageTk.PhotoImage(img); self.preview_label.config(image=self.preview_photo,text="")
        except Exception:
            self.preview_photo=None; self.preview_label.config(image="",text="IMAGEM\nCARREGADA")

    def _select_file(self):
        path=filedialog.askopenfilename(title="Selecione a imagem do campo",filetypes=[("Imagens","*.png *.jpg *.jpeg *.bmp"),("Todos os arquivos","*.*")])
        if path:
            self.image_path.set(path); self.image_name_label.config(text=os.path.basename(path)); self._update_preview(path); self._log(f"Imagem selecionada: {path}")

    def _capture_region(self):
        self.root.withdraw(); time.sleep(.2)
        def done(img):
            os.makedirs("field_captures",exist_ok=True)
            filename=os.path.join("field_captures",f"campo_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            img.save(filename); path=os.path.abspath(filename); self.image_path.set(path); self.image_name_label.config(text=os.path.basename(filename)); self._update_preview(path); self._log(f"Região capturada: {filename}"); self.root.deiconify()
        overlay=RegionCaptureOverlay(self.root,done); self.root.wait_window(overlay.top); self.root.deiconify()

    def _parse_target_time(self):
        try:
            parts=[int(p) for p in self.time_str.get().strip().split(":")]
            if len(parts)==2: h,m=parts; s=0
            elif len(parts)==3: h,m,s=parts
            else: raise ValueError
            if not (0<=h<=23 and 0<=m<=59 and 0<=s<=59): raise ValueError
        except ValueError:
            raise ValueError("Horário inválido. Use HH:MM ou HH:MM:SS.")
        now=dt.datetime.now(); target=now.replace(hour=h,minute=m,second=s,microsecond=0)
        return target+dt.timedelta(days=1) if target<=now else target

    def _start_schedule(self):
        if pyautogui is None or pyperclip is None:
            messagebox.showerror("Dependências ausentes","Instale com:\npython -m pip install -r requirements.txt"); return
        if not self.image_path.get() or not os.path.isfile(self.image_path.get()):
            messagebox.showwarning("Imagem necessária","Selecione ou capture uma imagem válida do campo."); return
        text=self.text_box.get("1.0","end").rstrip("\n")
        if not text: messagebox.showwarning("Texto necessário","Digite o texto que será enviado ao campo."); return
        try: target=self._parse_target_time()
        except ValueError as e: messagebox.showerror("Horário inválido",str(e)); return
        self.cancel_event.clear(); self.btn_start.config(state="disabled"); self.btn_cancel.config(state="normal")
        self._set_status(f"Agendado para {target.strftime('%d/%m/%Y às %H:%M:%S')}","running"); self._log(f"Automação agendada para {target.strftime('%d/%m/%Y %H:%M:%S')}")
        self.worker_thread=threading.Thread(target=self._run_schedule,args=(target,text),daemon=True); self.worker_thread.start()

    def _cancel_schedule(self):
        self.cancel_event.set(); self.btn_start.config(state="normal"); self.btn_cancel.config(state="disabled"); self._set_status("Agendamento cancelado","warning"); self._log("Agendamento cancelado pelo usuário.")

    def _run_schedule(self,target,text):
        while dt.datetime.now()<target:
            if self.cancel_event.is_set(): return
            time.sleep(.5)
        if self.cancel_event.is_set(): return
        self.root.after(0,lambda:self._set_status("Procurando o campo na tela...","running")); self.root.after(0,lambda:self._log("Horário atingido. Procurando o campo..."))
        deadline=time.time()+RETRY_TIMEOUT_SECONDS; location=None
        while time.time()<deadline and not self.cancel_event.is_set():
            try: location=pyautogui.locateCenterOnScreen(self.image_path.get(),confidence=self.confidence.get(),grayscale=True)
            except Exception as e: self.root.after(0,lambda e=e:self._log(f"Erro ao procurar imagem: {e}")); location=None
            if location: break
            time.sleep(RETRY_INTERVAL_SECONDS)
        if self.cancel_event.is_set(): return
        if not location:
            self.root.after(0,lambda:self._set_status("Campo não encontrado","error")); self.root.after(0,lambda:self._log("Campo não encontrado dentro do tempo limite.")); self.root.after(0,lambda:self.btn_start.config(state="normal")); self.root.after(0,lambda:self.btn_cancel.config(state="disabled")); return
        try:
            pyautogui.click(location); time.sleep(CLICK_TO_TYPE_DELAY); pyperclip.copy(text)
            pyautogui.hotkey("command" if sys.platform=="darwin" else "ctrl","v"); time.sleep(.2); pyautogui.press("enter")
            self.root.after(0,lambda:self._set_status("Automação concluída com sucesso","success")); self.root.after(0,lambda:self._log("Campo localizado, texto colado e Enter enviado."))
        except Exception as e:
            self.root.after(0,lambda:self._set_status("Erro ao executar a automação","error")); self.root.after(0,lambda e=e:self._log(f"Erro ao executar a ação: {e}"))
        finally:
            self.root.after(0,lambda:self.btn_start.config(state="normal")); self.root.after(0,lambda:self.btn_cancel.config(state="disabled"))

def main():
    root=tk.Tk(); AutoTyperApp(root); root.mainloop()

if __name__=="__main__":
    main()
