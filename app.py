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
        self.root.geometry("640x730")
        self.root.minsize(580, 650)
        self.root.configure(bg=BG_COLOR)

        self.proxy = ProxyEngine(port=8888, log_callback=self.log_message)
        self.is_adb_active = False

        self._get_local_ip()
        self._build_ui()
        self.check_adb_device()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
            s.close()
        except:
            self.local_ip = "127.0.0.1"

    def _build_ui(self):
        header_frame = tk.Frame(self.root, bg=BG_COLOR, pady=16)
        header_frame.pack(fill=tk.X, padx=20)

        title = tk.Label(header_frame, text="Galaxy Checkout Fixer", font=("Segoe UI", 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR)
        title.pack(anchor="w")

        subtitle = tk.Label(header_frame, text="Solucione o erro de acesso não autorizado nas compras da Galaxy Store", font=("Segoe UI", 10), fg=ACCENT_BLUE, bg=BG_COLOR)
        subtitle.pack(anchor="w", pady=(2, 0))

        dev_card = tk.Frame(self.root, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=16, pady=12)
        dev_card.pack(fill=tk.X, padx=20, pady=6)

        dev_title = tk.Label(dev_card, text="Dispositivo USB / ADB Conectado:", font=("Segoe UI", 10, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        dev_title.pack(anchor="w")

        dev_subframe = tk.Frame(dev_card, bg=CARD_BG)
        dev_subframe.pack(fill=tk.X, pady=(4, 0))

        self.lbl_device = tk.Label(dev_subframe, text="Verificando...", font=("Segoe UI", 10), fg=TEXT_MUTED, bg=CARD_BG)
        self.lbl_device.pack(side=tk.LEFT)

        btn_refresh = tk.Button(dev_subframe, text="↻ Atualizar", font=("Segoe UI", 9), fg=TEXT_COLOR, bg=CARD_BORDER, relief=tk.FLAT, command=self.check_adb_device, cursor="hand2")
        btn_refresh.pack(side=tk.RIGHT)

        notebook_frame = tk.Frame(self.root, bg=BG_COLOR)
        notebook_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        mode1_card = tk.Frame(notebook_frame, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=16, pady=14)
        mode1_card.pack(fill=tk.X, pady=6)

        m1_title = tk.Label(mode1_card, text="1. Modo Rápido via USB", font=("Segoe UI", 11, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        m1_title.pack(anchor="w")

        m1_desc = tk.Label(mode1_card, text="Ativa a correção automaticamente no celular e desfaz as alterações ao terminar.", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG)
        m1_desc.pack(anchor="w", pady=(2, 10))

        btn_box = tk.Frame(mode1_card, bg=CARD_BG)
        btn_box.pack(fill=tk.X)

        self.btn_toggle_adb = tk.Button(btn_box, text="▶ ATIVAR CORREÇÃO NO CELULAR", font=("Segoe UI", 10, "bold"), fg="#FFFFFF", bg=ACCENT_GREEN, activebackground=ACCENT_GREEN_HOVER, activeforeground="#FFFFFF", relief=tk.FLAT, pady=8, command=self.toggle_adb_fix, cursor="hand2")
        self.btn_toggle_adb.pack(fill=tk.X)

        mode2_card = tk.Frame(notebook_frame, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=16, pady=14)
        mode2_card.pack(fill=tk.X, pady=6)

        m2_title = tk.Label(mode2_card, text="2. Solução Permanente", font=("Segoe UI", 11, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        m2_title.pack(anchor="w")

        m2_desc = tk.Label(mode2_card, text="Grava o DNS Privado no Android para bloquear a Konduto no Wi-Fi e dados móveis.", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG)
        m2_desc.pack(anchor="w", pady=(2, 8))

        dns_box = tk.Frame(mode2_card, bg=CARD_BG)
        dns_box.pack(fill=tk.X, pady=2)

        lbl_nextdns = tk.Label(dns_box, text="ID NextDNS:", font=("Segoe UI", 9, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        lbl_nextdns.pack(side=tk.LEFT)

        self.ent_nextdns = tk.Entry(dns_box, font=("Segoe UI", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.ent_nextdns.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        btn_open_nextdns = tk.Button(dns_box, text="Criar Perfil Grátis", font=("Segoe UI", 9), fg=ACCENT_BLUE, bg=CARD_BG, relief=tk.FLAT, command=lambda: webbrowser.open("https://nextdns.io"), cursor="hand2")
        btn_open_nextdns.pack(side=tk.RIGHT)

        dns_actions = tk.Frame(mode2_card, bg=CARD_BG)
        dns_actions.pack(fill=tk.X, pady=(10, 0))

        btn_apply_dns = tk.Button(dns_actions, text="Gravar no Celular", font=("Segoe UI", 9, "bold"), fg="#FFFFFF", bg=ACCENT_BLUE, relief=tk.FLAT, pady=6, command=self.apply_permanent_dns, cursor="hand2")
        btn_apply_dns.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        btn_reset_dns = tk.Button(dns_actions, text="Restaurar DNS Padrão", font=("Segoe UI", 9), fg=TEXT_COLOR, bg=CARD_BORDER, relief=tk.FLAT, pady=6, command=self.reset_permanent_dns, cursor="hand2")
        btn_reset_dns.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        mode3_card = tk.Frame(notebook_frame, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=16, pady=10)
        mode3_card.pack(fill=tk.X, pady=6)

        m3_title = tk.Label(mode3_card, text="3. Modo Wi-Fi", font=("Segoe UI", 10, "bold"), fg=TEXT_COLOR, bg=CARD_BG)
        m3_title.pack(anchor="w")

        info_wifi = f"Para uso sem cabo: configure Proxy Manual no Wi-Fi do celular apontando para {self.local_ip}:{self.proxy.port} enquanto este aplicativo estiver aberto."
        m3_desc = tk.Label(mode3_card, text=info_wifi, font=("Segoe UI", 9), fg=TEXT_MUTED, bg=CARD_BG, wraplength=540, justify="left")
        m3_desc.pack(anchor="w", pady=(2, 0))

        log_frame = tk.Frame(self.root, bg=BG_COLOR, padx=20, pady=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        lbl_log = tk.Label(log_frame, text="Log de Atividades:", font=("Segoe UI", 9, "bold"), fg=TEXT_MUTED, bg=CARD_BG)
        lbl_log.pack(anchor="w")

        self.txt_log = tk.Text(log_frame, bg=CARD_BG, fg=TEXT_COLOR, font=("Consolas", 9), height=7, relief=tk.FLAT, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=(2, 10))

    def log_message(self, msg):
        def _append():
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
        self.root.after(0, _append)

    def run_adb(self, cmd_args):
        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            res = subprocess.run([ADB_BIN] + cmd_args, capture_output=True, text=True, timeout=10, creationflags=creation_flags)
            return res.returncode == 0, res.stdout.strip()
        except Exception as e:
            return False, str(e)

    def check_adb_device(self):
        ok, out = self.run_adb(["devices"])
        if ok:
            lines = [l for l in out.splitlines()[1:] if l.strip() and "device" in l]
            if lines:
                _, brand = self.run_adb(["shell", "getprop", "ro.product.brand"])
                _, model = self.run_adb(["shell", "getprop", "ro.product.model"])
                b = brand.strip().capitalize() if brand else "Samsung"
                m = model.strip() if model else "Aparelho"
                info = f"✓ {b} {m} conectado via USB"
                self.lbl_device.config(text=info, fg=ACCENT_GREEN)
                return True
        self.lbl_device.config(text="Nenhum aparelho detectado via USB", fg=ACCENT_RED_LIGHT)
        return False

    def toggle_adb_fix(self):
        if not self.is_adb_active:
            if not self.check_adb_device():
                messagebox.showwarning("Aviso", "Conecte o celular com a Depuração USB ativada ou utilize o modo Wi-Fi.")
                return

            self.proxy.start()
            self.run_adb(["reverse", f"tcp:{self.proxy.port}", f"tcp:{self.proxy.port}"])
            self.run_adb(["shell", "settings", "put", "global", "http_proxy", f"127.0.0.1:{self.proxy.port}"])

            self.is_adb_active = True
            self.btn_toggle_adb.config(text="⏹ DESATIVAR CORREÇÃO NO CELULAR", bg=ACCENT_RED, activebackground=ACCENT_RED_HOVER)
            self.log_message("[ADB] Correção ativada! Abra o jogo e faça sua compra normalmente.")
        else:
            self._cleanup_adb()
            self.proxy.stop()
            self.is_adb_active = False
            self.btn_toggle_adb.config(text="▶ ATIVAR CORREÇÃO NO CELULAR", bg=ACCENT_GREEN, activebackground=ACCENT_GREEN_HOVER)
            self.log_message("[ADB] Correção desativada. Rede restaurada ao normal.")

    def _cleanup_adb(self):
        self.run_adb(["shell", "settings", "delete", "global", "http_proxy"])
        self.run_adb(["shell", "settings", "delete", "global", "global_http_proxy_host"])
        self.run_adb(["shell", "settings", "delete", "global", "global_http_proxy_port"])
        self.run_adb(["reverse", "--remove", f"tcp:{self.proxy.port}"])

    def apply_permanent_dns(self):
        dns_id = self.ent_nextdns.get().strip()
        if not dns_id:
            messagebox.showwarning("Atenção", "Digite o ID do seu perfil NextDNS, exemplo: 12ab34.")
            return

        if not self.check_adb_device():
            messagebox.showwarning("Aviso", "Conecte o celular via USB para aplicar a configuração definitiva.")
            return

        hostname = f"{dns_id}.dns.nextdns.io"
        self.run_adb(["shell", "settings", "put", "global", "private_dns_mode", "hostname"])
        ok, _ = self.run_adb(["shell", "settings", "put", "global", "private_dns_specifier", hostname])

        if ok:
            self.log_message(f"[Permanente] DNS Privado gravado com sucesso: {hostname}")
            messagebox.showinfo("Sucesso", f"O DNS Privado foi gravado no aparelho:\n{hostname}\n\nLembre-se de adicionar 'i.konduto.com' na Denylist do seu NextDNS. A correção agora é permanente!")
        else:
            messagebox.showerror("Erro", "Não foi possível gravar a configuração de DNS via ADB.")

    def reset_permanent_dns(self):
        if not self.check_adb_device():
            messagebox.showwarning("Aviso", "Conecte o celular via USB para restaurar o DNS.")
            return

        self.run_adb(["shell", "settings", "put", "global", "private_dns_mode", "hostname"])
        self.run_adb(["shell", "settings", "put", "global", "private_dns_specifier", "dns.google"])
        self.log_message("[Permanente] DNS Privado restaurado para o padrão.")
        messagebox.showinfo("Restaurado", "O DNS Privado do aparelho foi restaurado para o padrão.")

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
