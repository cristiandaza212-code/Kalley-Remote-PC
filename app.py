import asyncio, ipaddress, json, os, queue, threading, sys, tkinter as tk
from pathlib import Path
from tkinter import messagebox
from androidtvremote2 import AndroidTVRemote

ROOT=Path(os.getenv("LOCALAPPDATA",str(Path.home())))/"KalleyRemotePC"
ROOT.mkdir(parents=True,exist_ok=True)
BG="#0b0c0b"; PANEL="#252825"; CYAN="#aeb5ae"; PINK="#245c38"
KEYS={"Arriba":"KEYCODE_DPAD_UP","Abajo":"KEYCODE_DPAD_DOWN","Izquierda":"KEYCODE_DPAD_LEFT","Derecha":"KEYCODE_DPAD_RIGHT","OK":"KEYCODE_DPAD_CENTER","Inicio":"KEYCODE_HOME","Atrás":"KEYCODE_BACK","Vol +":"KEYCODE_VOLUME_UP","Vol -":"KEYCODE_VOLUME_DOWN","Silencio":"KEYCODE_VOLUME_MUTE","Encender":"KEYCODE_POWER","Play/Pausa":"KEYCODE_MEDIA_PLAY_PAUSE","Entradas":"KEYCODE_TV_INPUT"}
class Remote:
 def __init__(self,notify):
  self.notify=notify;self.loop=asyncio.new_event_loop();self.tv=None;self.host=None;self.ready=False
  threading.Thread(target=self.loop.run_forever,daemon=True).start()
 def run(self,coro):
  future=asyncio.run_coroutine_threadsafe(coro,self.loop)
  def done(f):
   try:f.result()
   except Exception as e:self.notify("Error: "+str(e))
  future.add_done_callback(done)
 async def init(self,host):
  if self.tv is None or host!=self.host:
   self.ready=False;self.tv=AndroidTVRemote("Kalley Remote PC",str(ROOT/"cert.pem"),str(ROOT/"key.pem"),host);self.host=host
   await self.tv.async_generate_cert_if_missing()
 async def pair(self,host):
  await self.init(host);await self.tv.async_start_pairing();self.notify("Escribe el código que aparece en la TV")
 async def finish(self,code):
  await self.tv.async_finish_pairing(code);await self.connect(self.host)
 async def connect(self,host):
  await self.init(host);await self.tv.async_connect();self.ready=True;self.notify("Conectado a "+host)
 async def key(self,name):
  if not self.ready:self.notify("Primero conecta la TV");return
  self.tv.send_key_command(KEYS[name])
 async def type_text(self,text):
  if not self.ready:self.notify("Primero conecta la TV");return
  for ch in text:
   if ch.isascii() and ch.isalpha():key="KEYCODE_"+ch.upper()
   elif ch.isascii() and ch.isdigit():key="KEYCODE_"+ch
   elif ch==" ":key="KEYCODE_SPACE"
   elif ch=="\\b":key="KEYCODE_DEL"
   else:
    self.notify("Caracter no compatible: "+ch);continue
   self.tv.send_key_command(key)
   await asyncio.sleep(0.06)
  self.notify("Teclas enviadas; comprueba el texto en la TV")
class App:
 def __init__(self):
  self.root=tk.Tk();self.set_window_icon(self.root);self.root.title("Kalley Remote PC");self.root.geometry("440x680");self.root.configure(bg=BG)
  self.events=queue.Queue();self.remote=Remote(self.events.put)
  try:saved=json.loads((ROOT/"settings.json").read_text())
  except Exception:saved={}
  self.ip=tk.StringVar(value=saved.get("ip",""));self.code=tk.StringVar();self.status=tk.StringVar(value="Sin conexión")
  self.label(self.root,"KALLEY REMOTE PC",22,CYAN).pack(pady=(20,0))
  self.label(self.root,"GOOGLE TV  /  DARK EDITION",10,PINK).pack(pady=(0,14))
  self.btn(self.root,"Configurar TV",self.show_settings).pack(pady=(0,12))
  self.label(self.root,"ESTADO",10,PINK).pack(pady=(12,0))
  tk.Label(self.root,textvariable=self.status,bg=BG,fg=CYAN,wraplength=390).pack(pady=(0,12))
  grid=tk.Frame(self.root,bg=BG);grid.pack()
  rows=[["Encender","Inicio","Atrás"],["","Arriba",""],["Izquierda","OK","Derecha"],["","Abajo",""],["Vol -","Silencio","Vol +"],["","Play/Pausa",""],["","Entradas",""]]
  for i,row in enumerate(rows):
   for j,name in enumerate(row):
    if name:self.btn(grid,name,lambda n=name:self.remote.run(self.remote.key(n))).grid(row=i,column=j,padx=4,pady=4)
  self.btn(self.root,"Teclado TV",self.show_keyboard).pack(pady=(12,3))
  self.text_to_send=tk.StringVar()
  self.label(self.root,"Flechas / Enter / Esc / Home / + y -",9).pack(pady=12)
  self.root.bind("<KeyPress>",self.keyboard);self.root.after(100,self.poll)
  if self.ip.get().strip():
   self.status.set("Conectando automáticamente...")
   self.root.after(350,self.auto_connect)
 def show_keyboard(self):
  if hasattr(self,"keyboard_window") and self.keyboard_window.winfo_exists():
   self.keyboard_window.lift();self.keyboard_window.focus_force();return
  win=tk.Toplevel(self.root);self.set_window_icon(win);self.keyboard_window=win
  win.title("Teclado de Google TV");win.geometry("440x190");win.configure(bg=BG);win.resizable(False,False)
  self.label(win,"ESCRIBIR EN GOOGLE TV",16,CYAN).pack(pady=(15,8))
  self.text_entry=tk.Entry(win,textvariable=self.text_to_send,font=("Segoe UI",13))
  self.text_entry.pack(fill="x",padx=18,pady=5)
  self.btn(win,"Enviar texto",self.send_text).pack(pady=7)
  self.text_entry.bind("<Return>",lambda event:self.send_text())
  self.text_entry.focus_set()
 def auto_connect(self):
  try:host=str(ipaddress.ip_address(self.ip.get().strip()))
  except ValueError:self.status.set("IP guardada inválida: usa Configurar TV");return
  self.remote.run(self.remote.connect(host))
 def set_window_icon(self,window):
  base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
  icon=base/"kalley.ico"
  if icon.is_file():
   try:window.iconbitmap(str(icon))
   except tk.TclError:pass
 def show_settings(self):
  if hasattr(self,"settings_window") and self.settings_window.winfo_exists():
   self.settings_window.lift();self.settings_window.focus_force();return
  win=tk.Toplevel(self.root);self.set_window_icon(win);self.settings_window=win
  win.title("Configurar Google TV");win.geometry("430x310");win.configure(bg=BG);win.resizable(False,False)
  self.label(win,"CONFIGURAR GOOGLE TV",17,CYAN).pack(pady=(15,10))
  panel=tk.Frame(win,bg=PANEL,padx=12,pady=12);panel.pack(fill="x",padx=15)
  self.label(panel,"IP de Google TV",11).pack(anchor="w")
  tk.Entry(panel,textvariable=self.ip,font=("Segoe UI",13)).pack(fill="x",pady=5)
  r=tk.Frame(panel,bg=PANEL);r.pack()
  self.btn(r,"Vincular",self.pair).pack(side="left",padx=5)
  self.btn(r,"Conectar",self.connect).pack(side="left",padx=5)
  self.label(panel,"Código (6 letras o números)",11).pack(anchor="w",pady=(10,0))
  r=tk.Frame(panel,bg=PANEL);r.pack()
  tk.Entry(r,textvariable=self.code,width=16,font=("Segoe UI",13)).pack(side="left")
  self.btn(r,"Confirmar",self.confirm).pack(side="left",padx=5)
  self.label(win,"El estado de conexión aparece en la ventana principal",9).pack(pady=12)
 def label(self,parent,value,size=11,color="#f0f8ff"):
  return tk.Label(parent,text=value,bg=parent["bg"],fg=color,font=("Segoe UI",size,"bold"))
 def btn(self,parent,name,command):
  icons={"Encender":"⏻","Inicio":"⌂","Atrás":"↩","Arriba":"▲","Abajo":"▼","Izquierda":"◀","Derecha":"▶","OK":"●","Vol +":"🔊 +","Vol -":"🔉 −","Silencio":"🔇","Play/Pausa":"⏯","Entradas":"▣","Configurar TV":"⚙","Teclado TV":"⌨"}
  shown=icons.get(name,name)
  width=64 if name in KEYS else 126;height=38;radius=12
  canvas=tk.Canvas(parent,width=width,height=height,bg=parent["bg"],highlightthickness=0,bd=0,cursor="hand2")
  special=name in ("OK","Vincular","Confirmar")
  def paint(hover=False):
   canvas.delete("all")
   fill="#344c39" if special or hover else PANEL
   outline=PINK if not hover else "#398b53"
   r=radius;w=width;h=height
   # Esquinas redondeadas reales con contorno y fondo
   for x,y in ((r,r),(w-r,r),(r,h-r),(w-r,h-r)):
    canvas.create_oval(x-r,y-r,x+r,y+r,fill=outline,outline=outline)
   canvas.create_rectangle(r,0,w-r,h,fill=outline,outline=outline)
   canvas.create_rectangle(0,r,w,h-r,fill=outline,outline=outline)
   inset=2;ri=r-inset
   for x,y in ((r,r),(w-r,r),(r,h-r),(w-r,h-r)):
    canvas.create_oval(x-ri,y-ri,x+ri,y+ri,fill=fill,outline=fill)
   canvas.create_rectangle(r,inset,w-r,h-inset,fill=fill,outline=fill)
   canvas.create_rectangle(inset,r,w-inset,h-r,fill=fill,outline=fill)
   canvas.create_text(w/2,h/2,text=shown,fill="#f0f2f0",font=("Segoe UI Symbol",15 if name in KEYS else 10,"bold"))
  paint()
  canvas.bind("<Enter>",lambda e:paint(True))
  canvas.bind("<Leave>",lambda e:paint(False))
  canvas.bind("<Button-1>",lambda e:command())
  return canvas
 def host(self):
  try:
   ip=str(ipaddress.ip_address(self.ip.get().strip()));(ROOT/"settings.json").write_text(json.dumps({"ip":ip}));return ip
  except ValueError:messagebox.showerror("IP","Introduce una dirección IP válida")
 def pair(self):
  h=self.host()
  if h:self.remote.run(self.remote.pair(h))
 def connect(self):
  h=self.host()
  if h:self.remote.run(self.remote.connect(h))
 def confirm(self):
  c=self.code.get().strip().upper()
  if len(c)!=6 or not c.isalnum():messagebox.showerror("Código","Introduce los 6 caracteres (letras y números)");return
  self.remote.run(self.remote.finish(c))
 def send_text(self):
  text=self.text_to_send.get()
  if text:self.remote.run(self.remote.type_text(text))
  if hasattr(self,"text_entry") and self.text_entry.winfo_exists():self.text_entry.focus_set()
 def keyboard(self,event):
  if isinstance(event.widget,tk.Entry):return
  mapping={"Up":"Arriba","Down":"Abajo","Left":"Izquierda","Right":"Derecha","Return":"OK","Escape":"Atrás","Home":"Inicio","F10":"Vol -","F11":"Vol +","plus":"Vol +","KP_Add":"Vol +","minus":"Vol -","KP_Subtract":"Vol -"}
  if event.keysym in mapping:self.remote.run(self.remote.key(mapping[event.keysym]))
  elif event.char=="+":self.remote.run(self.remote.key("Vol +"))
  elif event.keysym=="BackSpace":self.remote.run(self.remote.type_text("\\b"))
  elif event.char and event.char.isascii() and (event.char.isalnum() or event.char==" "):self.remote.run(self.remote.type_text(event.char))
 def poll(self):
  while not self.events.empty():self.status.set(self.events.get_nowait())
  self.root.after(100,self.poll)
if __name__=="__main__":
 App().root.mainloop()
