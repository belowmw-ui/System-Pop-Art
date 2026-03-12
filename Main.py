from kivy.core.window import Window
Window.softinput_mode = 'below_target'

import os, time, socket, threading, json, struct, random, hashlib, re, math
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line, InstructionGroup
from kivy.utils import platform
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard

# --- MASTER CONFIG ---
COMMAND_NUM = "+27 71 886 6792"
GENERAL_PASS = "uvwe"
GROUPS = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL", "INDIA", "JULIET"]
BG_OBSIDIAN = [0, 0, 0, 1] 
ACCENT_CYAN = [0, 0.8, 1, 1]
USER_SIG = "IDLE (00*****000)"
ACTIVE_GROUP = "NONE"
MCAST_GRP = '224.1.1.1'
DATA_FILE = "sys_config.v47"
MAX_SLOTS = 56
MAX_PACKET_SIZE, PURGE_INTERVAL = 15360, 172800 

# --- DYNAMIC HOPPING CONFIG ---
BASE_UDP = 55550
BASE_TCP = 55560
PORT_RANGE = 10 

def get_hopped_ports():
    # Syncs everyone to the same channel based on the current date
    day_offset = time.localtime().tm_yday % PORT_RANGE
    return (BASE_UDP + day_offset, BASE_TCP + day_offset)

UDP_PORT, TCP_PORT = get_hopped_ports()

# --- UTILITIES ---
def get_user_color_list(sig):
    u_hex = hashlib.md5(sig.encode()).hexdigest()
    return [int(u_hex[0:2], 16)/255, int(u_hex[2:4], 16)/255, int(u_hex[4:6], 16)/255, 1]

def check_individual_expiry():
    now = time.time(); thirty_days = 30 * 24 * 60 * 60
    app_dir = App.get_running_app().user_data_dir if platform == 'android' else "."
    path = os.path.join(app_dir, DATA_FILE)
    if not os.path.exists(path):
        with open(path, "w") as f: json.dump({"install_date": now, "high_water": now}, f)
        return False, 0
    try:
        with open(path, "r") as f:
            data = json.load(f); start_date = data.get("install_date", now); high_water = data.get("high_water", now)
    except: start_date, high_water = now, now
    if now < (high_water - 600): return True, 999 
    data["high_water"] = now
    with open(path, "w") as f: json.dump(data, f)
    if (now - start_date) > thirty_days: return True, int(((start_date + 777) % 899) + 100)
    return False, 0

def refresh_lease():
    app_dir = App.get_running_app().user_data_dir if platform == 'android' else "."
    path = os.path.join(app_dir, DATA_FILE)
    with open(path, "w") as f: json.dump({"install_date": time.time(), "high_water": time.time()}, f)

if platform == 'android':
    from jnius import autoclass, cast
    WindowManager = autoclass('android.view.WindowManager$LayoutParams')

class TenDigitInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        s = re.sub('[^0-9]', '', substring)
        if len(self.text) + len(s) <= 10:
            return super(TenDigitInput, self).insert_text(s, from_undo=from_undo)

class SecureGuard:
    @staticmethod
    def enable():
        if platform != 'android': return
        try:
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def set_secure():
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                window = activity.getWindow()
                window.setFlags(WindowManager.FLAG_SECURE, WindowManager.FLAG_SECURE)
            set_secure()
        except: pass

class PowerGuard:
    _wakelock = None
    @staticmethod
    def acquire():
        if platform != 'android': return
        try:
            Context = autoclass('android.content.Context'); PM = autoclass('android.os.PowerManager')
            service = App.get_running_app()._android_context; pm = service.getSystemService(Context.POWER_SERVICE)
            PowerGuard._wakelock = pm.newWakeLock(PM.PARTIAL_WAKE_LOCK, "V58:PrimeLock")
            PowerGuard._wakelock.acquire()
        except: pass
    @staticmethod
    def release():
        try:
            if PowerGuard._wakelock: PowerGuard._wakelock.release()
        except: pass

def get_network_info():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(0); s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]; is_hot = ip.startswith("192.168.43")
        return ip, ("HOTSPOT" if is_hot else "MESH"), is_hot
    except: return "127.0.0.1", "OFFLINE", False

class StealthIdle(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_time = time.time()
        self.step = 0
        with self.canvas.before:
            Color(0,0,0,1); Rectangle(size=(5000, 5000))
        
        layout = BoxLayout(orientation='vertical', padding=dp(25), spacing=dp(10))
        self.header = Label(
            text="[b][color=FFFF00]SYSTEM[/color] [color=FF00FF]POP ART[/color][/b]\n[size=14sp]GEAR MOTOR MONITOR v4.7[/size]",
            markup=True, size_hint_y=None, height=dp(80), halign='center'
        )
        self.prop_feed = Label(
            text="Initializing System Hardware...",
            markup=True, font_size='14sp', halign='left', valign='top'
        )
        self.prop_feed.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        layout.add_widget(self.header); layout.add_widget(self.prop_feed)
        self.add_widget(layout)
        
        Clock.schedule_interval(self.refresh_stats, 1.0)
        self.tx, self.ty = 0, 0

    def refresh_stats(self, dt):
        if self.manager.current != 'idle': return
        uptime = int(time.time() - self.start_time); self.step += 0.1
        rpm = 1750.0 + random.uniform(-2.5, 3.1)
        torque = 2.45 + (math.sin(self.step) * 0.08)
        offset = (rpm * (uptime / 3600)) * 0.0125 
        
        self.prop_feed.text = (
            f"------------------------------------------\n"
            f"[b]STATUS:[/b] [color=00FF00]CORE_STABLE[/color]\n"
            f"[b]UPTIME:[/b] {uptime}s\n"
            f"------------------------------------------\n"
            f"[b][GEAR MOTOR PROPERTIES][/b]\n"
            f"ROTATION:  {rpm:.2f} RPM\n"
            f"TORQUE:    {torque:.3f} Nm\n"
            f"LOAD:      {42.1 + (math.cos(self.step)*3.5):.1f}%\n"
            f"------------------------------------------\n"
            f"[b][NETWORK MESH DATA][/b]\n"
            f"TX_PULSE:  {random.randint(10, 99)} pkts/s\n"
            f"OFFSET:    {offset:.6f} km\n"
            f"------------------------------------------\n"
            f"Hardware Sync: 100%\n"
            f"Awaiting Signal Trigger..."
        )

    def on_touch_down(self, t): self.tx, self.ty = t.x, t.y
    def on_touch_up(self, t):
        if (t.x - self.tx) > dp(150) and (t.y - self.ty) < -dp(100):
            exp, _ = check_individual_expiry()
            self.manager.current = 'stale' if exp else 'gate'

class DecoyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voices = [] 
        self.timer = 0
        self.burst_active = False
        self.burst_radius = 0

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=(5000, 5000))
            self.visual_group = InstructionGroup()
            self.canvas.add(self.visual_group)

        Clock.schedule_interval(self.update_sequence, 1/60.0)

    def update_sequence(self, dt):
        if self.manager.current != 'decoy': return
        self.timer += dt
        self.visual_group.clear()
        w, h = Window.width, Window.height
        cx, cy = w / 2, h / 2

        if self.timer <= 10:
            self.burst_active = False
            self.burst_radius = 0
            if random.random() < 0.15:
                main_screen = self.manager.get_screen('main')
                peers = list(main_screen.mesh_peers.keys())
                sig = random.choice(peers) if peers else "IDLE"
                u_hex = hashlib.md5(sig.encode()).hexdigest()
                u_color = [int(u_hex[0:2], 16)/255, int(u_hex[2:4], 16)/255, int(u_hex[4:6], 16)/255, 0.7]
                side = random.choice(['L', 'R', 'T', 'B'])
                self.voices.append({'pos': 0 if side in ['L', 'B'] else (w if side == 'R' else h), 'color': u_color, 'side': side, 'thick': dp(random.uniform(1, 4))})

            for v in self.voices[:]:
                self.visual_group.add(Color(*v['color']))
                move_step = dp(2)
                if v['side'] == 'L':
                    v['pos'] += move_step
                    self.visual_group.add(Rectangle(pos=(v['pos'], 0), size=(v['thick'], h)))
                elif v['side'] == 'R':
                    v['pos'] -= move_step
                    self.visual_group.add(Rectangle(pos=(v['pos'], 0), size=(v['thick'], h)))
                elif v['side'] == 'B':
                    v['pos'] += move_step
                    self.visual_group.add(Rectangle(pos=(0, v['pos']), size=(w, v['thick'])))
                elif v['side'] == 'T':
                    v['pos'] -= move_step
                    self.visual_group.add(Rectangle(pos=(0, v['pos']), size=(w, v['thick'])))
                if v['pos'] < -100 or v['pos'] > w + 100 or v['pos'] > h + 100: self.voices.remove(v)
        else:
            if not self.burst_active:
                self.voices = []; self.burst_active = True
            self.burst_radius += dp(15) 
            intensity = max(0, 1 - (self.timer - 10) / 2.5) 
            for i in range(6):
                ring_r = self.burst_radius - (i * dp(50))
                if ring_r > 0:
                    t = time.time() + i
                    r, g, b = (math.sin(t)+1)/2, (math.cos(t*0.5)+1)/2, 1
                    self.visual_group.add(Color(r, g, b, intensity))
                    self.visual_group.add(Line(circle=(cx, cy, ring_r), width=dp(3)))
            if self.timer > 13: self.timer = 0

    def on_touch_down(self, t):
        if t.is_double_tap: self.manager.current = 'gate'; return True
        return True

class MainInterface(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mesh_peers, self.known_peers = {}, {}
        self.last_full_wipe = time.time()
        self.is_ghost = False; self.pending_doc = None; self.wave_frame = 0; self.ripple_intensity = 0; self.bg_offset = 0; self.pulse_time = 0
        with self.canvas.before: 
            Color(0,0,0,1); self.bg_rect = Rectangle(size=(5000, 5000))
            self.grid_group = InstructionGroup(); self.canvas.before.add(self.grid_group)
            self.lattice_group = InstructionGroup(); self.canvas.before.add(self.lattice_group)
        with self.canvas.after:
            self.voice_group = InstructionGroup(); self.canvas.after.add(self.voice_group)
        
        self.layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(10))
        top = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(190), spacing=dp(6))
        self.id_bar = Button(text=f"// SIGNAL: [ SEARCHING ]", size_hint_y=None, height=dp(32), on_release=lambda x: setattr(self.manager, 'current', 'decoy'), background_normal='', background_color=[1, 1, 1, 0.04], font_size='9sp', color=ACCENT_CYAN)
        nav = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        self.btn_g = Button(text="< GLOBAL >", bold=True, on_release=lambda x: self.set_lane("GLOBAL"), background_color=[0, 0.5, 1, 0.7], background_normal='')
        self.btn_v = Button(text="< VAULT >", bold=True, on_release=lambda x: self.set_lane("VAULT"), background_color=[0.1, 0.1, 0.15, 0.5], background_normal='')
        nav.add_widget(self.btn_g); nav.add_widget(self.btn_v)
        self.input = TextInput(hint_text="// inject_data_", multiline=False, size_hint_y=None, height=dp(45), background_color=[1,1,1,0.03], foreground_color=[1,1,1,1], padding=[dp(12), dp(12)])
        self.input.bind(text=self.on_typing) 
        btn_row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        self.chat_btn = Button(text="TRANSMIT", background_color=[0, 0.6, 1, 0.9], background_normal='', on_release=self.send_chat)
        self.pdf_btn = Button(text="SYNC_DOC", background_color=[0.15, 0.15, 0.2, 0.5], background_normal='', disabled=True, on_release=self.click_file)
        btn_row.add_widget(self.chat_btn); btn_row.add_widget(self.pdf_btn)
        top.add_widget(self.id_bar); top.add_widget(nav); top.add_widget(self.input); top.add_widget(btn_row)
        self.scroll = ScrollView(do_scroll_x=False)
        self.feed = Label(text="[ NODE_STANDBY ]", color=[0.7, 0.8, 1, 1], valign='top', size_hint_y=None, padding=(20, 20), markup=True, line_height=1.3)
        self.feed.bind(size=lambda i,v: setattr(i, 'text_size', (v[0], None)), texture_size=lambda i,v: setattr(i, 'height', v[1]), on_ref_press=self.on_feed_click)
        self.scroll.add_widget(self.feed)
        self.wipe_label = Label(text="PURGE_CYCLE: 48:00", size_hint_y=None, height=dp(25), font_size='9sp', color=[0.3, 0.4, 0.5, 1])
        self.layout.add_widget(top); self.layout.add_widget(self.scroll); self.layout.add_widget(self.wipe_label)
        self.add_widget(self.layout); self.mode = "GLOBAL"; self.net_started = False; self.shared_file_path = None
        Clock.schedule_interval(self.animate_interface, 1/60.0)

    def on_enter(self):
        if USER_SIG.startswith("ROOT_"): self.is_ghost = True
        if not self.net_started:
            threading.Thread(target=self.listen, daemon=True).start()
            threading.Thread(target=self.file_server, daemon=True).start()
            self.net_started = True
        Clock.schedule_interval(self.check_purge_cycle, 60); Clock.schedule_interval(self.decay_ripple, 0.1); self.schedule_next_pulse()

    def get_spectrum_color(self, offset=0):
        t = (time.time() + offset) * 2.5
        return [(math.sin(t) + 1)/2 * self.ripple_intensity, (math.cos(t * 0.5) + 1)/2 * self.ripple_intensity, 1.0 * self.ripple_intensity, self.ripple_intensity]

    def on_typing(self, instance, value): self.ripple_intensity = min(1.0, self.ripple_intensity + 0.3)

    def animate_interface(self, dt):
        if self.manager.current != 'main': return
        self.pulse_time += dt; move_speed = 2.0 + (self.ripple_intensity * 10); amplitude = dp(5) + (self.ripple_intensity * dp(20)); self.bg_offset = math.sin(self.pulse_time * move_speed) * amplitude
        self.grid_group.clear(); glow = 0.05 + (max(0, self.bg_offset / dp(30)) * 0.2); grid_color = [0.7, 0, 1, glow] if self.mode == "VAULT" else [0, 0.8, 1, glow]
        self.grid_group.add(Color(*grid_color)); step = int(dp(45))
        for y in range(-step, int(Window.height) + step, step): self.grid_group.add(Line(points=[0, y + self.bg_offset, Window.width, y + self.bg_offset], width=1.1))
        for x in range(0, int(Window.width), step): self.grid_group.add(Line(points=[x, 0, x, Window.height], width=1.1))
        self.voice_group.clear()
        if self.ripple_intensity > 0.01:
            segments = 40; seg_height = Window.height / segments
            for i in range(segments):
                self.voice_group.add(Color(*self.get_spectrum_color(i * 0.05))); bar_width = (math.sin(time.time() * 15 + i) * dp(35)) * self.ripple_intensity
                self.voice_group.add(Line(points=[Window.width, i * seg_height, Window.width - abs(bar_width), i * seg_height], width=dp(2.5)))
        self.lattice_group.clear()
        for sig, last_seen in self.mesh_peers.items():
            u_hex = hashlib.md5(sig.encode()).hexdigest(); u_color = [int(u_hex[0:2], 16)/255, int(u_hex[2:4], 16)/255, int(u_hex[4:6], 16)/255, self.ripple_intensity]
            rad = math.radians(int(u_hex[6:10], 16) % 360); dist = dp(120) + (math.sin(time.time()*5) * dp(10))
            tx, ty = Window.width/2 + math.cos(rad) * dist, Window.height/2 + math.sin(rad) * dist
            self.lattice_group.add(Color(*u_color)); self.lattice_group.add(Line(circle=(tx, ty, dp(6)), width=1.5))
            self.lattice_group.add(Color(u_color[0], u_color[1], u_color[2], 0.15)); self.lattice_group.add(Line(points=[Window.width/2, Window.height/2, tx, ty], width=1))

    def decay_ripple(self, dt):
        if self.ripple_intensity > 0: self.ripple_intensity = max(0, self.ripple_intensity - 0.05)

    def schedule_next_pulse(self): Clock.schedule_once(self.network_pulse, 5.0)

    def set_lane(self, m): 
        self.mode = m; active_c = [0, 0.8, 1, 0.7] if m == "GLOBAL" else [0.7, 0, 1, 0.7]
        self.btn_g.background_color = active_c if m == "GLOBAL" else [0.1, 0.1, 0.15, 0.5]
        self.btn_v.background_color = active_c if m == "VAULT" else [0.1, 0.1, 0.15, 0.5]
        self.pdf_btn.disabled = (m != "VAULT"); self.post_sys(f"LATTICE_SWITCH: {m}")

    def check_purge_cycle(self, dt):
        rem = PURGE_INTERVAL - (time.time() - self.last_full_wipe)
        if rem <= 0: self.execute_full_purge()
        else: self.wipe_label.text = f"PURGE IN: {int(rem // 3600)}h {int((rem % 3600) // 60):02d}m"

    def execute_full_purge(self): self.feed.text = "[ SYSTEM PURGED ]"; self.last_full_wipe = time.time(); self.post_sys("AUTO-PURGE COMPLETED")

    def network_pulse(self, dt):
        ip, net_type, is_hot = get_network_info(); now = time.time(); self.wave_frame = (self.wave_frame + 1) % 4
        if net_type == "OFFLINE": w = "[ DEAD ]"; self.id_bar.color = [1, 0.2, 0.2, 1] 
        else: w = ["--~--", "-~-~-", "~-~-~", "~~~~~"][self.wave_frame]; self.id_bar.color = ACCENT_CYAN
        self.mesh_peers = {k: v for k, v in self.mesh_peers.items() if now - v < 90}
        self.id_bar.text = f"{w} // NODES: {len(self.mesh_peers)}/{MAX_SLOTS} // {USER_SIG}"
        if not self.is_ghost and net_type != "OFFLINE": self.broadcast("ALIVE", "PULSE")
        self.schedule_next_pulse()

    def incoming_handler(self, data, sender_ip):
        # --- GLOBAL-ONLY SELF DESTRUCT ---
        if data['msg'].startswith("!!"):
            # Only trigger on others, not the sender
            if data['sig'] == USER_SIG: return 
            
            cmd = data['msg'].replace("!!", "").strip().lower()
            if cmd == "self_destruct":
                app_dir = App.get_running_app().user_data_dir if platform == 'android' else "."
                path = os.path.join(app_dir, DATA_FILE)
                try: 
                    if os.path.exists(path): os.remove(path)
                except: pass
                Clipboard.copy("VOID_SIGNAL"); App.get_running_app().stop(); os._exit(0)

        if data['sig'] == USER_SIG: return 
        peer_sig = data['sig']; self.mesh_peers[peer_sig] = time.time(); self.ripple_intensity = 1.0 
        if peer_sig not in self.known_peers: self.known_peers[peer_sig] = sender_ip; self.post_sys(f"RADAR_ENTRY: {peer_sig}")
        if self.mode == "VAULT" and data['grp'] != ACTIVE_GROUP: return
        u_hex_color = hashlib.md5(peer_sig.encode()).hexdigest()[:6]
        tag = f"[ref={sender_ip}|{data['msg']}][color=00FF00][SYNC][/color][/ref]" if data['type'] == "DOC" else ""
        self.feed.text = (f"[color=445566]{time.strftime('%H:%M')} [/color][color={u_hex_color}][b]<{peer_sig}>[/b] // {tag} {data['msg']}[/color]\n[color=112233]---[/color]\n" + self.feed.text)[:4000]

    def send_chat(self, _):
        txt = self.input.text.strip()
        if txt == "/wipe": self.execute_full_purge(); self.input.text = ""; return
        if txt:
            self.broadcast(txt, "CHAT"); u_color = hashlib.md5(USER_SIG.encode()).hexdigest()[:6]
            self.feed.text = f"[color=445566]{time.strftime('%H:%M')} [/color][color={u_color}][b]<ME>[/b] // {txt}[/color]\n[color=112233]---[/color]\n" + self.feed.text
            self.input.text = ""

    def listen(self):
        global UDP_PORT
        attempts = 0
        while attempts < PORT_RANGE:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', UDP_PORT)); mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
                s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                self.post_sys(f"LATTICE_ACTIVE: PORT {UDP_PORT}")
                while True:
                    data, addr = s.recvfrom(2048); payload = json.loads(data.decode())
                    Clock.schedule_once(lambda dt: self.incoming_handler(payload, addr[0]))
                break
            except:
                attempts += 1; UDP_PORT = BASE_UDP + ((UDP_PORT - BASE_UDP + 1) % PORT_RANGE); continue

    def broadcast(self, msg, mtype):
        def task():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                p = json.dumps({"sig": USER_SIG, "msg": msg[:MAX_PACKET_SIZE], "type": mtype, "grp": ACTIVE_GROUP if self.mode == "VAULT" else "GLOBAL"})
                s.sendto(p.encode(), (MCAST_GRP, UDP_PORT)); s.close()
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def file_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM); server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); server.bind(('', TCP_PORT)); server.listen(5)
        while True:
            try:
                client, _ = server.accept(); req = json.loads(client.recv(1024).decode())
                if self.shared_file_path and os.path.exists(self.shared_file_path):
                    with open(self.shared_file_path, 'rb') as f: f.seek(req.get('offset', 0)); client.sendall(f.read())
                client.close()
            except: pass

    def on_feed_click(self, inst, val):
        if "|" in val: threading.Thread(target=self.download_engine, args=val.split('|'), daemon=True).start()
        else: self.open_file_externally(val)

    def download_engine(self, target_ip, filename):
        try:
            path = os.path.join("/sdcard/Download/" if platform == 'android' else "", f"SYNCED_{filename}")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(15); s.connect((target_ip, TCP_PORT))
            s.sendall(json.dumps({"file": filename, "offset": 0}).encode())
            with open(path, 'wb') as f:
                while True:
                    chunk = s.recv(4096)
                    if not chunk: break
                    f.write(chunk)
            s.close(); self.post_sys(f"SYNCED: {filename}", path)
        except: self.post_sys("SYNC TIMEOUT")

    def post_sys(self, msg, file=None):
        tag = f"[ref={file}][color=00FF00]{msg}[/color][/ref]" if file else f"[color=FFFF00]{msg}[/color]"
        Clock.schedule_once(lambda dt: setattr(self.feed, 'text', f"[b][color=FFFF00]POP![/color][/b]: {tag}\n[color=112233]---[/color]\n" + self.feed.text))

    def open_file_externally(self, path):
        try:
            if platform == 'android':
                PA = autoclass('org.kivy.android.PythonActivity'); Intent = autoclass('android.content.Intent'); Uri = autoclass('android.net.Uri'); File = autoclass('java.io.File')
                uri = Uri.fromFile(File(path)); intent = Intent(Intent.ACTION_VIEW); ext = path.split('.')[-1].lower()
                mime = "application/pdf" if ext == "pdf" else ("application/msword" if ext in ["doc", "docx"] else "*/*")
                intent.setDataAndType(uri, mime); intent.setFlags(268435456); cast('android.app.Activity', PA.mActivity).startActivity(intent)
            else: os.startfile(path) if os.name == 'nt' else os.system(f'open "{path}"')
        except: pass

    def click_file(self, _):
        fc = FileChooserIconView(path="/sdcard/Documents" if platform == "android" else os.path.expanduser("~"), filters=['*.pdf', '*.docx', '*.doc'])
        content = BoxLayout(orientation='vertical'); content.add_widget(fc); sel_btn = Button(text="STAGE FOR PULSE", size_hint_y=None, height=dp(50), background_color=ACCENT_CYAN)
        content.add_widget(sel_btn); self.pop = Popup(title='CAMPUS SYNC', content=content, size_hint=(0.95, 0.95)); sel_btn.bind(on_release=lambda x: self.prepare_manual_pulse(fc.selection)); self.pop.open()

    def prepare_manual_pulse(self, selection):
        if selection:
            self.pending_doc = selection[0]; self.pop.dismiss(); self.pdf_btn.text = "EXECUTE_PULSE"; self.pdf_btn.background_color = [1, 0.5, 0, 1]
            self.pdf_btn.unbind(on_release=self.click_file); self.pdf_btn.bind(on_release=self.execute_manual_pulse); self.post_sys(f"STAGED: {os.path.basename(self.pending_doc)}")

    def execute_manual_pulse(self, _):
        if self.pending_doc:
            fname = os.path.basename(self.pending_doc); self.shared_file_path = self.pending_doc; self.broadcast(fname, "DOC"); self.post_sys(f"PULSED: {fname}")
            self.pdf_btn.text = "SYNC_DOC"; self.pdf_btn.background_color = [0.15, 0.15, 0.2, 0.5]
            self.pdf_btn.unbind(on_release=self.execute_manual_pulse); self.pdf_btn.bind(on_release=self.click_file); self.pending_doc = None

class SunGate(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before: Color(0,0,0,1); Rectangle(size=(5000,5000))
        l = BoxLayout(orientation='vertical', padding=dp(40), spacing=15, size_hint=(1, None)); l.bind(minimum_height=l.setter('height'))
        skin = {'background_color': [0, 0.8, 1, 0.05], 'foreground_color': [0.9, 0.9, 1, 1], 'background_normal': '', 'padding': [dp(15), dp(12)]}
        self.pass_in = TextInput(hint_text="Master Key", password=True, size_hint_y=None, height='48dp', halign='center', multiline=False, **skin)
        self.name_in = TextInput(hint_text="Name", size_hint_y=None, height='48dp', halign='center', multiline=False, **skin)
        self.num_in = TenDigitInput(hint_text="10-Digit Phone", size_hint_y=None, height='48dp', halign='center', multiline=False, input_type='number', **skin)
        self.grp_spin = Spinner(text="SELECT GROUP", values=GROUPS, size_hint_y=None, height='48dp', background_color=[0.05, 0.1, 0.15, 1], color=ACCENT_CYAN, background_normal='')
        btn = Button(text="AUTHORIZE VERTEX", on_release=self.auth, background_color=[0, 0.6, 1, 0.8], background_normal='', bold=True, size_hint_y=None, height='55dp')
        for w in [self.pass_in, self.name_in, self.num_in, self.grp_spin, btn]: l.add_widget(w)
        anchor = AnchorLayout(anchor_x='center', anchor_y='center'); anchor.add_widget(l); self.add_widget(anchor)
    def auth(self, _):
        if len(self.num_in.text) != 10: return
        ui = self.pass_in.text.strip(); exp, code = check_individual_expiry()
        if (exp and ui == str((code * 3) + 8228)) or ui == GENERAL_PASS: self.login()
    def login(self):
        global USER_SIG, ACTIVE_GROUP
        if not self.name_in.text or self.grp_spin.text == "SELECT GROUP": return
        USER_SIG = f"{self.name_in.text.upper()} ({self.num_in.text[-3:]})"; ACTIVE_GROUP = self.grp_spin.text; PowerGuard.acquire(); self.manager.current = 'main'

class StaleScreen(Screen):
    def on_pre_enter(self): exp, code = check_individual_expiry(); self.code_val = code; self.m.text = f"LEASE EXPIRED\nID: [size=40sp]{code}[/size]\n\nContact: [color=00FF00]{COMMAND_NUM}[/color]"
    def __init__(self, **kwargs):
        super().__init__(**kwargs); self.code_val = 0
        with self.canvas.before: Color(0.1, 0, 0, 1); Rectangle(size=(5000,5000))
        l = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(15))
        self.m = Label(text="", halign='center', markup=True); self.name_in = TextInput(hint_text="Enter Name", size_hint_y=None, height=dp(45), halign='center', multiline=False)
        l.add_widget(self.m); l.add_widget(self.name_in); l.add_widget(Button(text="COPY REQ", size_hint_y=None, height=dp(50), background_color=[0, 0.6, 0, 1], on_release=lambda x: Clipboard.copy(f"USER: {self.name_in.text}\nID: {self.code_val}")))
        l.add_widget(Button(text="AUTH GATE", size_hint_y=None, height=dp(50), background_color=ACCENT_CYAN, on_release=lambda x: setattr(self.manager, 'current', 'gate')))
        self.add_widget(l)

class WiFiMessengerApp(App):
    def build(self):
        SecureGuard.enable(); sm = ScreenManager(transition=FadeTransition(duration=0.3))
        for s in [StealthIdle(name='idle'), SunGate(name='gate'), MainInterface(name='main'), DecoyScreen(name='decoy'), StaleScreen(name='stale')]: sm.add_widget(s)
        return sm
    def on_pause(self): return True
    def on_stop(self): PowerGuard.release()

if __name__ == "__main__": WiFiMessengerApp().run()
    
