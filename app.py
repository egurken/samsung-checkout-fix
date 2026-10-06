import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import subprocess
import webbrowser
import os
import sys

BG_COLOR = "#0D1117"
CARD_BG = "#161B22"
CARD_BORDER = "#30363D"
TEXT_COLOR = "#F0F6FC"
TEXT_MUTED = "#8B949E"
ACCENT_GREEN = "#2EA043"
ACCENT_GREEN_HOVER = "#3FB950"
ACCENT_RED = "#DA3633"
ACCENT_RED_HOVER = "#F85149"
ACCENT_RED_LIGHT = "#F85149"
ACCENT_BLUE = "#58A6FF"
ENTRY_BG = "#0D1117"

BLOCKED_DOMAINS = [
    "i.konduto.com",
    "konduto.com",
    "api.konduto.com"
]

def get_adb_path():
    candidates = []
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "bin", "adb.exe"))
        candidates.append(os.path.join(exe_dir, "adb.exe"))
        if hasattr(sys, '_MEIPASS'):
            candidates.append(os.path.join(sys._MEIPASS, "bin", "adb.exe"))
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(script_dir, "bin", "adb.exe"))
    candidates.append(os.path.join(script_dir, "adb.exe"))

    for c in candidates:
        if os.path.isfile(c):
            return c
    return "adb"

ADB_BIN = get_adb_path()


class ProxyEngine:
    def __init__(self, port=8888, log_callback=None):
        self.port = port
        self.log_callback = log_callback or (lambda msg: None)
        self.server_socket = None
        self.is_running = False
        self.thread = None

    def log(self, msg):
        self.log_callback(msg)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(100)
        self.log(f"[Proxy] Servidor iniciado na porta {self.port}.")

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.is_running:
            try:
                client_sock, client_addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except:
                break

    def _handle_client(self, client_sock):
        try:
            req = b""
            while b"\r\n\r\n" not in req and len(req) < 8192:
                chunk = client_sock.recv(4096)
                if not chunk:
                    break
                req += chunk

            if not req:
                client_sock.close()
                return

            lines = req.split(b"\r\n")
            first_line = lines[0].decode('latin1', errors='ignore')
            parts = first_line.split()
            if len(parts) < 2:
                client_sock.close()
                return

            method, target = parts[0], parts[1]

            if method.upper() == "CONNECT":
                host_port = target.split(":")
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 443

                if any(b in host.lower() for b in BLOCKED_DOMAINS):
                    self.log(f"[BLOQUEADO] {host} interceptado com sucesso! Checkout liberado.")
                    client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                    client_sock.close()
                    return

                try:
                    remote_sock = socket.create_connection((host, port), timeout=10)
                    client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                except Exception:
                    client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    client_sock.close()
                    return

                def pipe(src, dst):
                    try:
                        while self.is_running:
                            data = src.recv(65536)
                            if not data:
                                break
                            dst.sendall(data)
                    except:
                        pass
                    finally:
                        try: src.close()
                        except: pass
                        try: dst.close()
                        except: pass

                threading.Thread(target=pipe, args=(client_sock, remote_sock), daemon=True).start()
                threading.Thread(target=pipe, args=(remote_sock, client_sock), daemon=True).start()
            else:
                client_sock.close()
        except:
            try: client_sock.close()
            except: pass

    def stop(self):
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.log("[Proxy] Servidor parado.")


class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Galaxy Checkout Fixer")
        self.root.configure(bg=BG_COLOR)

        self._configure_window_size()

        self.proxy = ProxyEngine(port=8888, log_callback=self.log_message)
        self.is_adb_active = False
        self.is_busy = False

        self._get_local_ip()
        self._setup_styles()
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(200, self.async_check_device)

    def _configure_window_size(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(560, max(480, screen_w - 60))
        win_h = min(590, max(460, screen_h - 100))
        pos_x = (screen_w - win_w) // 2
        pos_y = max(15, (screen_h - win_h - 60) // 2)
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(480, 450)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
            s.close()
        except:
            self.local_ip = "127.0.0.1"

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD_BG, foreground=TEXT_MUTED, padding=[12, 6], font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", CARD_BORDER), ("active", CARD_BG)],
                  foreground=[("selected", TEXT_COLOR), ("active", TEXT_COLOR)])

        style.configure("Horizontal.TProgressbar", background=ACCENT_BLUE, troughcolor=CARD_BG, borderwidth=0, thickness=4)

    def _build_ui(self):
        header_frame = tk.Frame(self.root, bg=BG_COLOR, padx=16, pady=10)
        header_frame.pack(fill=tk.X)

        title = tk.Label(header_frame, text="Galaxy Checkout Fixer", font=("Segoe UI", 16, "bold"), fg=TEXT_COLOR, bg=BG_COLOR)
        title.pack(anchor="w")

        subtitle = tk.Label(header_frame, text="Correção do erro de checkout e acesso não autorizado na Galaxy Store", font=("Segoe UI", 9), fg=ACCENT_BLUE, bg=BG_COLOR)
        subtitle.pack(anchor="w", pady=(1, 0))

        dev_card = tk.Frame(self.root, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=12, pady=8)
        dev_card.pack(fill=tk.X, padx=16, pady=(0, 6))

        dev_left = tk.Frame(dev_card, bg=CARD_BG)
        dev_left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        dev_title = tk.Label(dev_left, text="Dispositivo USB:", font=("Segoe UI", 9, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        dev_title.pack(anchor="w")

        self.lbl_device = tk.Label(dev_left, text="Verificando...", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG)
        self.lbl_device.pack(anchor="w")

        dev_actions = tk.Frame(dev_card, bg=CARD_BG)
        dev_actions.pack(side=tk.RIGHT)

        self.btn_refresh = tk.Button(dev_actions, text="↻ Atualizar", font=("Segoe UI", 9), fg=TEXT_COLOR, bg=CARD_BORDER, relief=tk.FLAT, padx=8, pady=3, command=self.async_check_device, cursor="hand2")
        self.btn_refresh.pack(side=tk.LEFT, padx=3)

        self.btn_reboot = tk.Button(dev_actions, text="🔄 Reiniciar Celular", font=("Segoe UI", 9), fg="#FFFFFF", bg="#8B5CF6", activebackground="#7C3AED", relief=tk.FLAT, padx=8, pady=3, command=self.async_reboot_device, cursor="hand2")
        self.btn_reboot.pack(side=tk.LEFT, padx=3)

        notebook_frame = tk.Frame(self.root, bg=BG_COLOR)
        notebook_frame.pack(fill=tk.X, padx=16, pady=2)

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.X)

        tab1 = tk.Frame(self.notebook, bg=CARD_BG, padx=12, pady=10)
        self.notebook.add(tab1, text="Modo Rápido USB")

        m1_desc = tk.Label(tab1, text="Aplica a correção via cabo USB e remove as regras de proxy ao desativar.", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG)
        m1_desc.pack(anchor="w", pady=(0, 8))

        self.btn_toggle_adb = tk.Button(tab1, text="▶ ATIVAR CORREÇÃO NO CELULAR", font=("Segoe UI", 10, "bold"), fg="#FFFFFF", bg=ACCENT_GREEN, activebackground=ACCENT_GREEN_HOVER, activeforeground="#FFFFFF", relief=tk.FLAT, pady=8, command=self.async_toggle_adb, cursor="hand2")
        self.btn_toggle_adb.pack(fill=tk.X)

        tab2 = tk.Frame(self.notebook, bg=CARD_BG, padx=12, pady=10)
        self.notebook.add(tab2, text="Solução Permanente")

        m2_desc = tk.Label(tab2, text="Configura o DNS Privado no Android para manter a correção no Wi-Fi e dados móveis.", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG)
        m2_desc.pack(anchor="w", pady=(0, 6))

        dns_box = tk.Frame(tab2, bg=CARD_BG)
        dns_box.pack(fill=tk.X, pady=2)

        lbl_nextdns = tk.Label(dns_box, text="ID NextDNS:", font=("Segoe UI", 9, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        lbl_nextdns.pack(side=tk.LEFT)

        self.ent_nextdns = tk.Entry(dns_box, font=("Segoe UI", 9), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.ent_nextdns.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        btn_open_nextdns = tk.Button(dns_box, text="Criar Perfil Grátis", font=("Segoe UI", 8), fg=ACCENT_BLUE, bg=CARD_BG, relief=tk.FLAT, command=lambda: webbrowser.open("https://nextdns.io"), cursor="hand2")
        btn_open_nextdns.pack(side=tk.RIGHT)

        dns_actions = tk.Frame(tab2, bg=CARD_BG)
        dns_actions.pack(fill=tk.X, pady=(8, 0))

        self.btn_apply_dns = tk.Button(dns_actions, text="Gravar no Celular", font=("Segoe UI", 9, "bold"), fg="#FFFFFF", bg=ACCENT_BLUE, relief=tk.FLAT, pady=5, command=self.async_apply_dns, cursor="hand2")
        self.btn_apply_dns.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self.btn_reset_dns = tk.Button(dns_actions, text="Restaurar DNS Padrão", font=("Segoe UI", 9), fg=TEXT_COLOR, bg=CARD_BORDER, relief=tk.FLAT, pady=5, command=self.async_reset_dns, cursor="hand2")
        self.btn_reset_dns.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(3, 0))

        tab3 = tk.Frame(self.notebook, bg=CARD_BG, padx=12, pady=10)
        self.notebook.add(tab3, text="Modo Wi-Fi")

        m3_desc = tk.Label(tab3, text=f"Para conexão sem cabo: configure Proxy Manual no Wi-Fi do celular em {self.local_ip}:{self.proxy.port} enquanto esta ferramenta estiver aberta.", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG, wraplength=480, justify="left")
        m3_desc.pack(anchor="w")

        status_bar_frame = tk.Frame(self.root, bg=BG_COLOR, padx=16, pady=4)
        status_bar_frame.pack(fill=tk.X)

        self.lbl_status = tk.Label(status_bar_frame, text="Pronto", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_COLOR)
        self.lbl_status.pack(side=tk.LEFT)

        self.progressbar = ttk.Progressbar(status_bar_frame, mode="indeterminate", style="Horizontal.TProgressbar")

        log_frame = tk.Frame(self.root, bg=BG_COLOR, padx=16, pady=2)
        log_frame.pack(fill=tk.BOTH, expand=True)

        lbl_log = tk.Label(log_frame, text="Terminal de Atividades:", font=("Segoe UI", 9, "bold"), fg=TEXT_MUTED, bg=BG_COLOR)
        lbl_log.pack(anchor="w")

        log_subframe = tk.Frame(log_frame, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1)
        log_subframe.pack(fill=tk.BOTH, expand=True, pady=(2, 8))

        log_scroll = tk.Scrollbar(log_subframe)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.txt_log = tk.Text(log_subframe, bg=CARD_BG, fg=TEXT_COLOR, font=("Consolas", 9), relief=tk.FLAT, yscrollcommand=log_scroll.set)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.txt_log.yview)

    def log_message(self, msg):
        def _append():
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
        self.root.after(0, _append)

    def set_loading(self, active, message="Processando..."):
        def _update():
            self.is_busy = active
            if active:
                self.progressbar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
                self.progressbar.start(12)
                self.lbl_status.config(text=message, fg=ACCENT_BLUE)
                self.btn_refresh.config(state=tk.DISABLED)
                self.btn_reboot.config(state=tk.DISABLED)
                self.btn_toggle_adb.config(state=tk.DISABLED)
                self.btn_apply_dns.config(state=tk.DISABLED)
                self.btn_reset_dns.config(state=tk.DISABLED)
            else:
                self.progressbar.stop()
                self.progressbar.pack_forget()
                self.lbl_status.config(text=message, fg=TEXT_MUTED)
                self.btn_refresh.config(state=tk.NORMAL)
                self.btn_reboot.config(state=tk.NORMAL)
                self.btn_toggle_adb.config(state=tk.NORMAL)
                self.btn_apply_dns.config(state=tk.NORMAL)
                self.btn_reset_dns.config(state=tk.NORMAL)
        self.root.after(0, _update)

    def run_adb(self, cmd_args):
        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            res = subprocess.run([ADB_BIN] + cmd_args, capture_output=True, text=True, timeout=10, creationflags=creation_flags)
            return res.returncode == 0, res.stdout.strip()
        except Exception as e:
            return False, str(e)

    def async_check_device(self):
        if self.is_busy:
            return
        def _work():
            self.set_loading(True, "Buscando dispositivos...")
            ok, out = self.run_adb(["devices"])
            device_found = False
            device_label = "Nenhum aparelho detectado via USB"
            label_color = ACCENT_RED_LIGHT

            if ok:
                lines = [l for l in out.splitlines()[1:] if l.strip()]
                for l in lines:
                    if "device" in l and "unauthorized" not in l:
                        _, brand = self.run_adb(["shell", "getprop", "ro.product.brand"])
                        _, model = self.run_adb(["shell", "getprop", "ro.product.model"])
                        b = brand.strip().capitalize() if brand else "Samsung"
                        m = model.strip() if model else "Galaxy"
                        device_label = f"✓ {b} {m} conectado"
                        label_color = ACCENT_GREEN
                        device_found = True
                        break
                    elif "unauthorized" in l:
                        device_label = "⚠ Desbloqueie a tela do celular para autorizar"
                        label_color = "#E3B341"
                        break

            def _done():
                self.lbl_device.config(text=device_label, fg=label_color)
                self.set_loading(False, "Pronto")
            self.root.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def async_toggle_adb(self):
        if self.is_busy:
            return
        def _work():
            if not self.is_adb_active:
                self.set_loading(True, "Ativando correção no celular...")
                ok, out = self.run_adb(["devices"])
                if not any("device" in l and "unauthorized" not in l for l in out.splitlines()[1:] if l.strip()):
                    self.set_loading(False, "Falha na conexão USB")
                    messagebox.showwarning("Aviso", "Conecte o celular com a Depuração USB ativada ou use o modo Wi-Fi.")
                    return

                self.proxy.start()
                self.run_adb(["reverse", f"tcp:{self.proxy.port}", f"tcp:{self.proxy.port}"])
                self.run_adb(["shell", "settings", "put", "global", "http_proxy", f"127.0.0.1:{self.proxy.port}"])

                self.is_adb_active = True
                def _update_ui():
                    self.btn_toggle_adb.config(text="⏹ DESATIVAR CORREÇÃO NO CELULAR", bg=ACCENT_RED, activebackground=ACCENT_RED_HOVER)
                    self.log_message("[ADB] Correção ativada com sucesso. Abra o jogo e conclua sua compra.")
                    self.set_loading(False, "Correção ativa")
                self.root.after(0, _update_ui)
            else:
                self.set_loading(True, "Desativando correção e restaurando rede...")
                self._cleanup_adb()
                self.proxy.stop()
                self.is_adb_active = False
                def _update_ui():
                    self.btn_toggle_adb.config(text="▶ ATIVAR CORREÇÃO NO CELULAR", bg=ACCENT_GREEN, activebackground=ACCENT_GREEN_HOVER)
                    self.log_message("[ADB] Correção desativada. Rede restaurada ao padrão.")
                    self.set_loading(False, "Pronto")
                self.root.after(0, _update_ui)

        threading.Thread(target=_work, daemon=True).start()

    def _cleanup_adb(self):
        self.run_adb(["shell", "settings", "delete", "global", "http_proxy"])
        self.run_adb(["shell", "settings", "delete", "global", "global_http_proxy_host"])
        self.run_adb(["shell", "settings", "delete", "global", "global_http_proxy_port"])
        self.run_adb(["shell", "settings", "delete", "global", "global_http_proxy_exclusion_list"])
        self.run_adb(["reverse", "--remove", f"tcp:{self.proxy.port}"])

    def async_apply_dns(self):
        if self.is_busy:
            return
        dns_id = self.ent_nextdns.get().strip()
        if not dns_id:
            messagebox.showwarning("Atenção", "Digite o ID do seu perfil NextDNS, por exemplo: 12ab34.")
            return

        def _work():
            self.set_loading(True, "Gravando DNS Privado no celular...")
            hostname = f"{dns_id}.dns.nextdns.io"
            self.run_adb(["shell", "settings", "put", "global", "private_dns_mode", "hostname"])
            ok, _ = self.run_adb(["shell", "settings", "put", "global", "private_dns_specifier", hostname])

            def _done():
                if ok:
                    self.log_message(f"[DNS] Gravado com sucesso no celular: {hostname}")
                    self.set_loading(False, "DNS gravado")
                    messagebox.showinfo("Sucesso", f"O DNS Privado foi gravado no aparelho:\n{hostname}\n\nLembre-se de adicionar 'i.konduto.com' na Denylist do NextDNS.")
                else:
                    self.set_loading(False, "Erro ao gravar DNS")
                    messagebox.showerror("Erro", "Não foi possível gravar a configuração de DNS via USB.")
            self.root.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def async_reset_dns(self):
        if self.is_busy:
            return
        def _work():
            self.set_loading(True, "Restaurando DNS padrão...")
            self.run_adb(["shell", "settings", "put", "global", "private_dns_mode", "off"])
            self.run_adb(["shell", "settings", "delete", "global", "private_dns_specifier"])

            def _done():
                self.log_message("[DNS] Configuração de DNS Privado restaurada ao padrão do Android.")
                self.set_loading(False, "DNS restaurado")
                messagebox.showinfo("Restaurado", "O DNS Privado do aparelho foi restaurado ao padrão do sistema.")
            self.root.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def async_reboot_device(self):
        if self.is_busy:
            return
        if not messagebox.askyesno("Reiniciar Aparelho", "Deseja reiniciar o celular agora para zerar a memória de rede e reiniciar os aplicativos?"):
            return

        def _work():
            self.set_loading(True, "Enviando comando de reinicialização...")
            self.log_message("[Aparelho] Enviando comando para reiniciar o celular...")
            self._cleanup_adb()
            ok, out = self.run_adb(["reboot"])

            def _done():
                if ok:
                    self.log_message("[Aparelho] Comando enviado. O celular está reiniciando.")
                    self.lbl_device.config(text="Aparelho reiniciando...", fg=ACCENT_BLUE)
                    self.set_loading(False, "Aparelho reiniciando")
                    messagebox.showinfo("Reiniciando", "O celular está reiniciando. Aguarde o aparelho ligar para concluir a restauração completa.")
                else:
                    self.log_message(f"[Aparelho] Falha ao enviar reboot: {out}")
                    self.set_loading(False, "Falha ao reiniciar")
                    messagebox.showwarning("Aviso", "Não foi possível reiniciar o aparelho via USB. Verifique a conexão.")
            self.root.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def on_close(self):
        if self.is_adb_active:
            self._cleanup_adb()
            self.proxy.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
