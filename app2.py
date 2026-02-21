import tkinter as tk
from tkinter import ttk, font, messagebox
import threading
import socket
import time
import random
import numpy as np
import networkx as nx
import hashlib
import json
import os

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt


# ============================================================
# USER DATABASE CONFIGURATION
# ============================================================
USER_DB_FILE = "users.json"

# ============================================================
# ESP32 CONFIGURATION
# ============================================================
ESP32_IP = "10.181.87.217"
ESP32_PORT = 8080
ESP_CMD = "READ_ALL\n"
BUFFER = 250

# ============================================================
# REALTIME DATA BUFFERS
# ============================================================
temp_buf, hum_buf = [], []
hr_buf, spo2_buf = [], []
lat_buf, thr_buf, jit_buf = [], [], []

_prev_lat = None

# PACKET COUNTERS
packet_hr = 0
packet_spo2 = 0
packet_temp = 0
packet_hum = 0

# Connection tracking
esp32_connected = False
last_successful_data = 0
popup_shown = False
connection_timeout = 10  # seconds before showing disconnected


# ============================================================
# USER MANAGEMENT FUNCTIONS
# ============================================================
def load_users():
    """Load users from JSON file"""
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    """Register a new user"""
    users = load_users()
    
    if username in users:
        return False, "Username already exists!"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters!"
    
    users[username] = {
        'password': hash_password(password),
        'email': email,
        'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        'last_login': None
    }
    
    save_users(users)
    return True, "Registration successful!"

def login_user(username, password):
    """Authenticate user"""
    users = load_users()
    
    if username not in users:
        return False, "Invalid username or password!"
    
    if users[username]['password'] != hash_password(password):
        return False, "Invalid username or password!"
    
    # Update last login time
    users[username]['last_login'] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_users(users)
    
    return True, "Login successful!"


# ============================================================
# MODERN LOGIN/REGISTER SCREEN
# ============================================================
class AuthScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("WSN-SDN Authentication")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f8f9fa')
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        # Custom fonts
        self.title_font = ("Segoe UI", 32, "bold")
        self.subtitle_font = ("Segoe UI", 14)
        self.button_font = ("Segoe UI", 12, "bold")
        self.label_font = ("Segoe UI", 11)
        self.small_font = ("Segoe UI", 10)
        
        # Create main container with modern design
        self.main_container = tk.Frame(root, bg='#f8f9fa')
        self.main_container.pack(fill='both', expand=True)
        
        # Left side - Brand/Info Section
        self.left_panel = tk.Frame(self.main_container, bg='#6f42c1')
        self.left_panel.pack(side='left', fill='both', expand=True)
        
        # Right side - Form Section
        self.right_panel = tk.Frame(self.main_container, bg='white')
        self.right_panel.pack(side='right', fill='both', expand=True)
        
        # Setup both panels
        self.setup_left_panel()
        self.setup_form_panel()
        
        # Store current user
        self.current_user = None

    def setup_left_panel(self):
        """Setup the left brand/info panel"""
        # Logo and brand area
        brand_frame = tk.Frame(self.left_panel, bg='#6f42c1')
        brand_frame.pack(fill='both', expand=True, padx=60, pady=80)
        
        # Logo/Icon
        logo_frame = tk.Frame(brand_frame, bg='#6f42c1')
        logo_frame.pack(pady=(0, 40))
        
        logo_label = tk.Label(logo_frame, text="🌐", font=("Arial", 72), 
                             bg='#6f42c1', fg='white')
        logo_label.pack()
        
        # Brand name
        brand_label = tk.Label(brand_frame, text="WSN-SDN", 
                              font=self.title_font, bg='#6f42c1', fg='white')
        brand_label.pack(pady=(0, 20))
        
        # Tagline
        tagline_label = tk.Label(brand_frame, 
                                text="Intelligent Wireless Sensor Network Dashboard",
                                font=("Segoe UI", 16), bg='#6f42c1', fg='#e2d9f3',
                                justify='center')
        tagline_label.pack(pady=(0, 60))
        
        # Features list with icons
        features_frame = tk.Frame(brand_frame, bg='#6f42c1')
        features_frame.pack()
        
        features = [
            ("📊", "Real-time Sensor Monitoring"),
            ("🕸️", "Network Topology Visualization"),
            ("⚡", "SDN Controller Dashboard"),
            ("📈", "Performance Analytics"),
            ("🔒", "Secure Authentication")
        ]
        
        for icon, text in features:
            feature_frame = tk.Frame(features_frame, bg='#6f42c1')
            feature_frame.pack(fill='x', pady=12)
            
            icon_label = tk.Label(feature_frame, text=icon, font=("Arial", 16), 
                                 bg='#6f42c1', fg='white')
            icon_label.pack(side='left', padx=(0, 15))
            
            text_label = tk.Label(feature_frame, text=text, 
                                 font=self.label_font, bg='#6f42c1', 
                                 fg='white', anchor='w')
            text_label.pack(side='left', fill='x', expand=True)
        
        # Copyright info
        copyright_frame = tk.Frame(brand_frame, bg='#6f42c1')
        copyright_frame.pack(side='bottom', fill='x', pady=20)
        
        copyright_label = tk.Label(copyright_frame, 
                                  text="© 2024 WSN-SDN Dashboard. All rights reserved.",
                                  font=self.small_font, bg='#6f42c1', fg='#d1c4e9')
        copyright_label.pack()

    def setup_form_panel(self):
        """Setup the form panel with login by default"""
        # Form container with padding
        self.form_container = tk.Frame(self.right_panel, bg='white')
        self.form_container.pack(fill='both', expand=True, padx=100, pady=80)
        
        # Header with tabs
        self.header_frame = tk.Frame(self.form_container, bg='white')
        self.header_frame.pack(fill='x', pady=(0, 40))
        
        # Tabs for Login/Register
        self.tab_frame = tk.Frame(self.header_frame, bg='white')
        self.tab_frame.pack()
        
        # Login Tab
        self.login_tab = tk.Label(self.tab_frame, text="SIGN IN", 
                                 font=("Segoe UI", 18, "bold"), 
                                 bg='white', fg='#6f42c1',
                                 padx=20, pady=10, cursor='hand2')
        self.login_tab.pack(side='left')
        self.login_tab.bind("<Button-1>", lambda e: self.show_login())
        
        # Register Tab
        self.register_tab = tk.Label(self.tab_frame, text="SIGN UP", 
                                    font=("Segoe UI", 18), 
                                    bg='white', fg='#6c757d',
                                    padx=20, pady=10, cursor='hand2')
        self.register_tab.pack(side='left')
        self.register_tab.bind("<Button-1>", lambda e: self.show_register())
        
        # Active tab indicator
        self.active_indicator = tk.Frame(self.header_frame, bg='#6f42c1', height=3)
        self.active_indicator.pack(fill='x')
        
        # Form content area
        self.form_content = tk.Frame(self.form_container, bg='white')
        self.form_content.pack(fill='both', expand=True)
        
        # Start with login form
        self.show_login()

    def show_login(self):
        """Show login form"""
        # Update tab styles
        self.login_tab.config(fg='#6f42c1', font=("Segoe UI", 18, "bold"))
        self.register_tab.config(fg='#6c757d', font=("Segoe UI", 18))
        
        # Move indicator
        self.active_indicator.place(x=self.login_tab.winfo_x(), 
                                  rely=1, relwidth=0.5, anchor='nw')
        
        # Clear previous form
        for widget in self.form_content.winfo_children():
            widget.destroy()
        
        # Create login form
        login_frame = tk.Frame(self.form_content, bg='white')
        login_frame.pack(fill='both', expand=True)
        
        # Username/Email field
        tk.Label(login_frame, text="Username or Email", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.login_username = tk.Entry(login_frame, font=self.label_font, 
                                      bg='#f8f9fa', fg='#212529', 
                                      relief='flat', highlightbackground='#dee2e6',
                                      highlightthickness=1, highlightcolor='#6f42c1',
                                      insertbackground='#6f42c1')
        self.login_username.pack(fill='x', pady=(0, 20), ipady=12)
        
        # Password field
        tk.Label(login_frame, text="Password", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.login_password = tk.Entry(login_frame, font=self.label_font, 
                                      bg='#f8f9fa', fg='#212529', show='•',
                                      relief='flat', highlightbackground='#dee2e6',
                                      highlightthickness=1, highlightcolor='#6f42c1',
                                      insertbackground='#6f42c1')
        self.login_password.pack(fill='x', pady=(0, 10), ipady=12)
        
        # Remember me and Forgot password
        options_frame = tk.Frame(login_frame, bg='white')
        options_frame.pack(fill='x', pady=(0, 30))
        
        self.remember_var = tk.BooleanVar()
        remember_check = tk.Checkbutton(options_frame, variable=self.remember_var, 
                                       text="Remember me", font=self.small_font,
                                       bg='white', fg='#6c757d',
                                       activebackground='white',
                                       selectcolor='#f8f9fa')
        remember_check.pack(side='left')
        
        forgot_btn = tk.Label(options_frame, text="Forgot password?", 
                             font=self.small_font, bg='white', fg='#6f42c1',
                             cursor='hand2')
        forgot_btn.pack(side='right')
        forgot_btn.bind("<Button-1>", lambda e: self.show_forgot_password())
        
        # Login button
        login_btn = tk.Button(login_frame, text="Sign In", 
                             font=self.button_font, bg='#6f42c1', 
                             fg='white', relief='flat', cursor='hand2',
                             activebackground='#7952b3', 
                             activeforeground='white',
                             command=self.perform_login)
        login_btn.pack(fill='x', ipady=14, pady=(0, 20))
        
        # Already have account link
        signup_frame = tk.Frame(login_frame, bg='white')
        signup_frame.pack()
        
        tk.Label(signup_frame, text="Don't have an account? ", 
                font=self.small_font, bg='white', fg='#6c757d').pack(side='left')
        
        signup_link = tk.Label(signup_frame, text="Sign up", 
                              font=self.small_font, bg='white', fg='#6f42c1',
                              cursor='hand2')
        signup_link.pack(side='left')
        signup_link.bind("<Button-1>", lambda e: self.show_register())

    def show_register(self):
        """Show registration form"""
        # Update tab styles
        self.login_tab.config(fg='#6c757d', font=("Segoe UI", 18))
        self.register_tab.config(fg='#6f42c1', font=("Segoe UI", 18, "bold"))
        
        # Move indicator
        self.active_indicator.place(x=self.register_tab.winfo_x(), 
                                  rely=1, relwidth=0.5, anchor='nw')
        
        # Clear previous form
        for widget in self.form_content.winfo_children():
            widget.destroy()
        
        # Create register form
        register_frame = tk.Frame(self.form_content, bg='white')
        register_frame.pack(fill='both', expand=True)
        
        # Full Name field
        tk.Label(register_frame, text="Full Name", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.reg_name = tk.Entry(register_frame, font=self.label_font, 
                                bg='#f8f9fa', fg='#212529', 
                                relief='flat', highlightbackground='#dee2e6',
                                highlightthickness=1, highlightcolor='#6f42c1',
                                insertbackground='#6f42c1')
        self.reg_name.pack(fill='x', pady=(0, 15), ipady=12)
        
        # Email field
        tk.Label(register_frame, text="Email Address", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.reg_email = tk.Entry(register_frame, font=self.label_font, 
                                 bg='#f8f9fa', fg='#212529', 
                                 relief='flat', highlightbackground='#dee2e6',
                                 highlightthickness=1, highlightcolor='#6f42c1',
                                 insertbackground='#6f42c1')
        self.reg_email.pack(fill='x', pady=(0, 15), ipady=12)
        
        # Username field
        tk.Label(register_frame, text="Username", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.reg_username = tk.Entry(register_frame, font=self.label_font, 
                                    bg='#f8f9fa', fg='#212529', 
                                    relief='flat', highlightbackground='#dee2e6',
                                    highlightthickness=1, highlightcolor='#6f42c1',
                                    insertbackground='#6f42c1')
        self.reg_username.pack(fill='x', pady=(0, 15), ipady=12)
        
        # Password field
        tk.Label(register_frame, text="Password", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.reg_password = tk.Entry(register_frame, font=self.label_font, 
                                    bg='#f8f9fa', fg='#212529', show='•',
                                    relief='flat', highlightbackground='#dee2e6',
                                    highlightthickness=1, highlightcolor='#6f42c1',
                                    insertbackground='#6f42c1')
        self.reg_password.pack(fill='x', pady=(0, 15), ipady=12)
        
        # Confirm Password field
        tk.Label(register_frame, text="Confirm Password", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', pady=(0, 8))
        
        self.reg_confirm = tk.Entry(register_frame, font=self.label_font, 
                                   bg='#f8f9fa', fg='#212529', show='•',
                                   relief='flat', highlightbackground='#dee2e6',
                                   highlightthickness=1, highlightcolor='#6f42c1',
                                   insertbackground='#6f42c1')
        self.reg_confirm.pack(fill='x', pady=(0, 20), ipady=12)
        
        # Terms and Conditions
        terms_frame = tk.Frame(register_frame, bg='white')
        terms_frame.pack(fill='x', pady=(0, 30))
        
        self.terms_var = tk.BooleanVar()
        terms_check = tk.Checkbutton(terms_frame, variable=self.terms_var, 
                                    bg='white', activebackground='white',
                                    selectcolor='#f8f9fa')
        terms_check.pack(side='left')
        
        tk.Label(terms_frame, text="I agree to the ", 
                font=self.small_font, bg='white', fg='#6c757d').pack(side='left')
        
        terms_link = tk.Label(terms_frame, text="Terms & Conditions", 
                             font=self.small_font, bg='white', fg='#6f42c1',
                             cursor='hand2')
        terms_link.pack(side='left')
        
        # Register button
        register_btn = tk.Button(register_frame, text="Create Account", 
                                font=self.button_font, bg='#6f42c1', 
                                fg='white', relief='flat', cursor='hand2',
                                activebackground='#7952b3', 
                                activeforeground='white',
                                command=self.perform_register)
        register_btn.pack(fill='x', ipady=14, pady=(0, 20))
        
        # Already have account link
        login_frame = tk.Frame(register_frame, bg='white')
        login_frame.pack()
        
        tk.Label(login_frame, text="Already have an account? ", 
                font=self.small_font, bg='white', fg='#6c757d').pack(side='left')
        
        login_link = tk.Label(login_frame, text="Sign in", 
                             font=self.small_font, bg='white', fg='#6f42c1',
                             cursor='hand2')
        login_link.pack(side='left')
        login_link.bind("<Button-1>", lambda e: self.show_login())

    def perform_login(self):
        """Handle login"""
        username = self.login_username.get().strip()
        password = self.login_password.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields!")
            return
        
        success, message = login_user(username, password)
        
        if success:
            self.current_user = username
            messagebox.showinfo("Success", message)
            self.open_dashboard()
        else:
            messagebox.showerror("Error", message)

    def perform_register(self):
        """Handle registration"""
        name = self.reg_name.get().strip()
        email = self.reg_email.get().strip()
        username = self.reg_username.get().strip()
        password = self.reg_password.get()
        confirm = self.reg_confirm.get()
        
        # Validation
        if not all([name, email, username, password, confirm]):
            messagebox.showerror("Error", "Please fill in all fields!")
            return
        
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match!")
            return
        
        if not self.terms_var.get():
            messagebox.showerror("Error", "Please agree to the Terms & Conditions!")
            return
        
        success, message = register_user(username, password, email)
        
        if success:
            messagebox.showinfo("Success", message)
            self.show_login()
        else:
            messagebox.showerror("Error", message)

    def show_forgot_password(self):
        """Show forgot password dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Reset Password")
        dialog.geometry("400x300")
        dialog.configure(bg='white')
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Reset Password", 
                font=("Segoe UI", 20, "bold"), 
                bg='white', fg='#6f42c1').pack(pady=(30, 10))
        
        tk.Label(dialog, text="Enter your email to receive reset instructions", 
                font=self.subtitle_font, bg='white', fg='#6c757d',
                wraplength=350).pack(pady=(0, 20))
        
        tk.Label(dialog, text="Email Address:", 
                font=self.label_font, bg='white', fg='#495057').pack(anchor='w', padx=50, pady=(10, 5))
        
        email_entry = tk.Entry(dialog, font=self.label_font, 
                              bg='#f8f9fa', fg='#212529', 
                              relief='flat', highlightbackground='#dee2e6',
                              highlightthickness=1)
        email_entry.pack(fill='x', padx=50, pady=(0, 20), ipady=10)
        
        def reset_password():
            email = email_entry.get().strip()
            if not email:
                messagebox.showerror("Error", "Please enter your email!", parent=dialog)
                return
            
            users = load_users()
            for user, data in users.items():
                if data['email'] == email:
                    messagebox.showinfo("Success", 
                                      f"Password reset instructions sent to:\n{email}", 
                                      parent=dialog)
                    dialog.destroy()
                    return
            
            messagebox.showerror("Error", "Email not found!", parent=dialog)
        
        tk.Button(dialog, text="Send Reset Instructions", 
                 font=self.button_font, bg='#6f42c1', fg='white',
                 relief='flat', cursor='hand2',
                 command=reset_password).pack(fill='x', padx=50, ipady=12, pady=(0, 20))
        
        tk.Button(dialog, text="Cancel", 
                 font=self.button_font, bg='#6c757d', fg='white',
                 relief='flat', cursor='hand2',
                 command=dialog.destroy).pack(fill='x', padx=50, ipady=10)
        
        dialog.mainloop()

    def open_dashboard(self):
        """Open the main dashboard"""
        self.root.destroy()  # Close auth window
        start_main_app(self.current_user)  # Start main app with logged in user


# ============================================================
# PARSE SENSOR PACKET
# ============================================================
def parse_packet(line):
    vals = {"TEMP": None, "HUM": None, "HR": None, "SPO2": None}

    try:
        for p in line.strip().split("|"):
            if ":" in p:
                key, val = p.split(":")
                if key in vals:
                    vals[key] = float(val)
    except:
        pass

    return vals


# ============================================================
# ESP32 LISTENER THREAD
# ============================================================
def esp32_listener():
    global _prev_lat, packet_hr, packet_spo2, packet_temp, packet_hum
    global esp32_connected, last_successful_data, popup_shown
    
    while True:
        data_received = False
        
        try:
            start = time.time()

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)  # 3 second timeout
            s.connect((ESP32_IP, ESP32_PORT))
            s.send(ESP_CMD.encode())
            raw = s.recv(1024).decode()
            s.close()

            line = next((x for x in raw.split("\n") if "TEMP:" in x), "")
            vals = parse_packet(line)

            # Append data + count packets
            if vals["TEMP"] is not None:
                temp_buf.append(vals["TEMP"])
                packet_temp += 1
                data_received = True

            if vals["HUM"] is not None:
                hum_buf.append(vals["HUM"])
                packet_hum += 1
                data_received = True

            if vals["HR"] is not None:
                hr_buf.append(vals["HR"])
                packet_hr += 1
                data_received = True

            if vals["SPO2"] is not None:
                spo2_buf.append(vals["SPO2"])
                packet_spo2 += 1
                data_received = True

            # NETWORK METRICS
            if data_received:
                latency = (time.time() - start) * 1000
                lat_buf.append(latency)

                if _prev_lat is not None:
                    jitter = abs(latency - _prev_lat)
                    jit_buf.append(jitter)
                _prev_lat = latency

                thr_buf.append(len(raw) * 8 / ((latency / 1000) + 0.001))

                # Trim buffers
                for b in (temp_buf, hum_buf, hr_buf, spo2_buf, lat_buf, thr_buf, jit_buf):
                    if len(b) > BUFFER:
                        b.pop(0)
                
                # Update last successful data time
                last_successful_data = time.time()
                
                # If ESP32 was not connected, now it is
                if not esp32_connected:
                    esp32_connected = True
                    popup_shown = False
                
        except Exception as e:
            # Connection failed
            pass
        
        # Check if we should show disconnected popup
        if esp32_connected:
            time_since_last_data = time.time() - last_successful_data
            if time_since_last_data > connection_timeout:
                esp32_connected = False
                popup_shown = False
        
        time.sleep(1)


# ============================================================
# ENHANCED STYLED CARD WIDGET
# ============================================================
class EnhancedStyledCard(tk.Frame):
    def __init__(self, parent, title, value, unit, color, icon_text="●", trend=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg='white', highlightbackground='#e0d6f0', 
                       highlightthickness=2, relief='flat', 
                       cursor="hand2")
        
        self.config(highlightbackground='#d1c4e9', highlightcolor='#d1c4e9', highlightthickness=2)
        
        # Card header with gradient effect simulation
        header_frame = tk.Frame(self, bg=color, height=35)
        header_frame.pack(fill='x', side='top')
        header_frame.pack_propagate(False)
        
        # Icon with subtle background
        icon_frame = tk.Frame(header_frame, bg=color, width=35)
        icon_frame.pack(side='left', fill='y')
        icon_frame.pack_propagate(False)
        
        icon = tk.Label(icon_frame, text=icon_text, bg='white', fg=color,
                       font=("Arial", 14, "bold"), width=3, height=1,
                       relief='flat')
        icon.place(relx=0.5, rely=0.5, anchor='center')
        
        title_label = tk.Label(header_frame, text=title, bg=color, fg='white',
                              font=("Arial", 11, "bold"))
        title_label.pack(side='left', padx=(10, 0))
        
        # Card body with subtle pattern background
        body_frame = tk.Frame(self, bg='white')
        body_frame.pack(fill='both', expand=True, padx=15, pady=20)
        
        # Value display with modern typography
        self.value_label = tk.Label(body_frame, text=value, bg='white',
                                   font=("Arial", 28, "bold"), fg='#2d1b69')
        self.value_label.pack(pady=(5, 0))
        
        # Unit with smaller font
        unit_frame = tk.Frame(body_frame, bg='white')
        unit_frame.pack()
        
        unit_label = tk.Label(unit_frame, text=unit, bg='white',
                             font=("Arial", 10), fg='#7e57c2')
        unit_label.pack(side='left')
        
        # Optional trend indicator
        if trend:
            trend_icon = "↗" if trend > 0 else "↘" if trend < 0 else "→"
            trend_color = "#4caf50" if trend > 0 else "#f44336" if trend < 0 else "#757575"
            trend_label = tk.Label(unit_frame, text=f" {trend_icon}", 
                                  bg='white', fg=trend_color,
                                  font=("Arial", 10, "bold"))
            trend_label.pack(side='left', padx=(5, 0))
    
    def safe_update_value(self, value):
        """Thread-safe method to update card value"""
        try:
            self.value_label.config(text=value)
        except:
            pass


# ============================================================
# MAIN APPLICATION CLASS
# ============================================================
class App:
    def __init__(self, root, username):
        self.root = root
        self.root.title(f"WSN Intelligent SDN Dashboard - Welcome, {username}")
        self.root.geometry("1600x900")
        
        # Store username
        self.username = username
        
        # Professional purple gradient background
        self.root.configure(bg='#f5f1fe')
        
        # Custom fonts
        self.title_font = ("Segoe UI", 18, "bold")
        self.subtitle_font = ("Segoe UI", 12, "bold")
        self.normal_font = ("Segoe UI", 10)
        self.card_title_font = ("Segoe UI", 11, "bold")
        self.card_value_font = ("Segoe UI", 28, "bold")
        
        # Card references
        self.cards = {}
        
        self.layout()
        self.sidebar()
        self.tabs()
        
        # Initialize cards
        self.initialize_monitor_cards()
        
        # Start ESP32 listener thread
        threading.Thread(target=esp32_listener, daemon=True).start()
        
        # Schedule updates in main thread
        self.running = True
        self.schedule_updates()

    # --------------------------------------------------------
    def layout(self):
        # Main container with purple gradient sidebar
        self.left = tk.Frame(self.root, bg='#3f2b96', width=300)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)
        
        self.right = tk.Frame(self.root, bg='#f5f1fe')
        self.right.pack(side="right", fill="both", expand=True)

    # --------------------------------------------------------
    def sidebar(self):
        # Sidebar header with user info
        header = tk.Frame(self.left, bg='#2d1b69', height=120)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        # User avatar/icon
        avatar_frame = tk.Frame(header, bg='#2d1b69')
        avatar_frame.pack(pady=(15, 10))
        
        avatar_label = tk.Label(avatar_frame, text="👤", font=("Arial", 24), 
                               bg='#2d1b69', fg='white')
        avatar_label.pack()
        
        # Username
        tk.Label(header, text=self.username, 
                 font=("Segoe UI", 14, "bold"),
                 bg='#2d1b69', fg='white').pack()
        
        # User role
        tk.Label(header, text="System Administrator", 
                 font=("Segoe UI", 10),
                 bg='#2d1b69', fg='#d1c4e9').pack(pady=(5, 0))
        
        # Configuration section
        config_frame = tk.Frame(self.left, bg='#3f2b96')
        config_frame.pack(fill='x', padx=25, pady=25)
        
        tk.Label(config_frame, text="Sensor Module:", 
                 bg='#3f2b96', fg='#e1d8f0',
                 font=self.subtitle_font).pack(anchor='w', pady=(0, 8))
        
        self.sensor_type = ttk.Combobox(
            config_frame,
            values=["MAX30102 (HR + SpO₂)", "DHT11 (Temp + Humidity)"],
            state="readonly",
            font=self.normal_font,
            height=5
        )
        self.sensor_type.current(0)
        self.sensor_type.pack(fill='x', pady=(0, 20))
        
        # Professional purple buttons
        button_style = {
            'font': self.subtitle_font, 
            'bd': 0, 
            'height': 2, 
            'cursor': 'hand2', 
            'fg': 'white',
            'activebackground': '#7e57c2',
            'activeforeground': 'white'
        }
        
        # Button with gradient effect simulation
        btn_frame1 = tk.Frame(self.left, bg='#3f2b96')
        btn_frame1.pack(fill='x', padx=25, pady=10)
        tk.Button(btn_frame1, text="Start SDN Controller",
                  bg='#7e57c2', **button_style,
                  command=self.start_sdn).pack(fill='x')
        
        btn_frame2 = tk.Frame(self.left, bg='#3f2b96')
        btn_frame2.pack(fill='x', padx=25, pady=10)
        tk.Button(btn_frame2, text="Compare Networks",
                  bg='#5e35b1', **button_style,
                  command=self.compare).pack(fill='x')
        
        btn_frame3 = tk.Frame(self.left, bg='#3f2b96')
        btn_frame3.pack(fill='x', padx=25, pady=10)
        tk.Button(btn_frame3, text="Show Topology",
                  bg='#4527a0', **button_style,
                  command=self.show_topology).pack(fill='x')
        
        # Status indicators with purple theme
        status_frame = tk.Frame(self.left, bg='#3f2b96')
        status_frame.pack(fill='x', padx=25, pady=(30, 20))
        
        status_header = tk.Label(status_frame, text="System Status", 
                                 bg='#3f2b96', fg='#d1c4e9',
                                 font=self.subtitle_font)
        status_header.pack(anchor='w', pady=(0, 15))
        
        self.conn_status = tk.Label(status_frame, text="● ESP32: DISCONNECTED", 
                                    bg='#3f2b96', fg='#ef9a9a',
                                    font=self.normal_font)
        self.conn_status.pack(anchor='w', pady=3)
        
        self.data_status = tk.Label(status_frame, text="● Data: WAITING", 
                                    bg='#3f2b96', fg='#ffcc80',
                                    font=self.normal_font)
        self.data_status.pack(anchor='w', pady=3)
        
        self.sdn_status = tk.Label(status_frame, text="● SDN: INACTIVE", 
                                   bg='#3f2b96', fg='#ef9a9a',
                                   font=self.normal_font)
        self.sdn_status.pack(anchor='w', pady=3)
        
        # Logout button at bottom
        logout_frame = tk.Frame(self.left, bg='#3f2b96')
        logout_frame.pack(side='bottom', fill='x', padx=25, pady=20)
        
        tk.Button(logout_frame, text="🚪 Logout", 
                  bg='#e53935', fg='white', font=self.subtitle_font,
                  relief='flat', cursor='hand2',
                  activebackground='#ef5350', activeforeground='white',
                  command=self.logout).pack(fill='x', ipady=8)

    # --------------------------------------------------------
    def logout(self):
        """Logout and return to auth screen"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.running = False
            self.root.destroy()
            start_auth_screen()

    # --------------------------------------------------------
    def tabs(self):
        # Styled notebook with purple theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Purple.TNotebook', background='#f5f1fe', borderwidth=0)
        style.configure('Purple.TNotebook.Tab', 
                       background='#e8eaf6',
                       foreground='#5e35b1',
                       padding=[25, 10],
                       font=self.subtitle_font,
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Purple.TNotebook.Tab', 
                 background=[('selected', '#7e57c2')],
                 foreground=[('selected', 'white')],
                 expand=[('selected', [1, 1, 1, 0])])
        
        self.tabs = ttk.Notebook(self.right, style='Purple.TNotebook')
        self.tabs.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Create tabs
        self.tab_monitor = tk.Frame(self.tabs, bg='#f5f1fe')
        self.tab_compare = tk.Frame(self.tabs, bg='#f5f1fe')
        self.tab_topology = tk.Frame(self.tabs, bg='#f5f1fe')
        self.tab_sdn = tk.Frame(self.tabs, bg='#f5f1fe')
        
        self.tabs.add(self.tab_monitor, text="Realtime Monitor")
        self.tabs.add(self.tab_compare, text="Network Comparison")
        self.tabs.add(self.tab_topology, text="Network Topology")
        self.tabs.add(self.tab_sdn, text="SDN Controller")
        
        self.monitor_tab()
        self.compare_tab()
        self.topology_tab()
        self.sdn_tab()

    # --------------------------------------------------------
    def initialize_monitor_cards(self):
        # Card container with grid layout
        self.card_frame = tk.Frame(self.tab_monitor, bg='#f5f1fe')
        self.card_frame.pack(fill='x', padx=20, pady=20)
        
        # Purple color scheme for cards
        card_colors = {
            'hr': '#9575cd',      # Light purple
            'spo2': '#7e57c2',    # Medium purple
            'temp': '#5e35b1',    # Deep purple
            'hum': '#4527a0',     # Dark purple
            'lat': '#b39ddb',     # Pale purple
            'thr': '#d1c4e9'      # Very light purple
        }
        
        # First row of cards
        row1_frame = tk.Frame(self.card_frame, bg='#f5f1fe')
        row1_frame.pack(fill='x', pady=(0, 15))
        
        self.hr_card = EnhancedStyledCard(row1_frame, "Heart Rate", "--", "BPM", 
                                         card_colors['hr'], "❤", width=240, height=140)
        self.hr_card.pack(side='left', padx=10, pady=10)
        
        self.spo2_card = EnhancedStyledCard(row1_frame, "SpO₂", "--", "%", 
                                           card_colors['spo2'], "O2", width=240, height=140)
        self.spo2_card.pack(side='left', padx=10, pady=10)
        
        self.temp_card = EnhancedStyledCard(row1_frame, "Temperature", "--", "°C", 
                                           card_colors['temp'], "🌡", width=240, height=140)
        self.temp_card.pack(side='left', padx=10, pady=10)
        
        # Second row of cards
        row2_frame = tk.Frame(self.card_frame, bg='#f5f1fe')
        row2_frame.pack(fill='x', pady=(0, 20))
        
        self.hum_card = EnhancedStyledCard(row2_frame, "Humidity", "--", "%", 
                                          card_colors['hum'], "💧", width=240, height=140)
        self.hum_card.pack(side='left', padx=10, pady=10)
        
        self.lat_card = EnhancedStyledCard(row2_frame, "Latency", "--", "ms", 
                                          card_colors['lat'], "⚡", width=240, height=140)
        self.lat_card.pack(side='left', padx=10, pady=10)
        
        self.thr_card = EnhancedStyledCard(row2_frame, "Throughput", "--", "bps", 
                                          card_colors['thr'], "📊", width=240, height=140)
        self.thr_card.pack(side='left', padx=10, pady=10)
        
        # Store card references
        self.cards = {
            'hr': self.hr_card,
            'spo2': self.spo2_card,
            'temp': self.temp_card,
            'hum': self.hum_card,
            'lat': self.lat_card,
            'thr': self.thr_card
        }

    # --------------------------------------------------------
    # REALTIME MONITOR TAB
    # --------------------------------------------------------
    def monitor_tab(self):
        # Create figure with purple theme
        plt.style.use('default')
        
        # Set purple color cycle
        purple_colors = ['#7e57c2', '#5e35b1', '#4527a0', '#9575cd', '#b39ddb', '#d1c4e9']
        plt.rcParams['axes.prop_cycle'] = plt.cycler(color=purple_colors)
        
        self.fig, self.ax = plt.subplots(3, 2, figsize=(14, 9), facecolor='#f5f1fe')
        self.fig.subplots_adjust(hspace=0.4, wspace=0.3)
        
        # Set background color for all axes
        for row in self.ax:
            for ax in row:
                ax.set_facecolor('#ede7f6')
                ax.spines['bottom'].set_color('#b39ddb')
                ax.spines['top'].set_color('#b39ddb')
                ax.spines['right'].set_color('#b39ddb')
                ax.spines['left'].set_color('#b39ddb')
                ax.tick_params(colors='#5e35b1')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_monitor)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=20, pady=20)

    # --------------------------------------------------------
    # SCHEDULE UPDATES SAFELY
    # --------------------------------------------------------
    def schedule_updates(self):
        """Schedule updates using after() method for thread safety"""
        if not self.running:
            return
            
        try:
            self.update_gui()
            # Schedule next update if window still exists
            self.root.after(1000, self.schedule_updates)
        except:
            # Window destroyed, stop updates
            pass
    
    def update_gui(self):
        """Update GUI elements - called from main thread"""
        try:
            # Update card values
            if hr_buf:
                self.hr_card.safe_update_value(f"{hr_buf[-1]:.1f}")
            else:
                self.hr_card.safe_update_value("--")
                
            if spo2_buf:
                self.spo2_card.safe_update_value(f"{spo2_buf[-1]:.1f}")
            else:
                self.spo2_card.safe_update_value("--")
                
            if temp_buf:
                self.temp_card.safe_update_value(f"{temp_buf[-1]:.1f}")
            else:
                self.temp_card.safe_update_value("--")
                
            if hum_buf:
                self.hum_card.safe_update_value(f"{hum_buf[-1]:.1f}")
            else:
                self.hum_card.safe_update_value("--")
                
            if lat_buf:
                self.lat_card.safe_update_value(f"{lat_buf[-1]:.1f}")
            else:
                self.lat_card.safe_update_value("--")
                
            if thr_buf:
                self.thr_card.safe_update_value(f"{thr_buf[-1]:.0f}")
            else:
                self.thr_card.safe_update_value("--")
            
            # Update status indicators
            time_since_last_data = time.time() - last_successful_data
            
            if esp32_connected:
                if time_since_last_data < 5:
                    self.conn_status.config(text="● ESP32: CONNECTED", fg='#a5d6a7')
                    self.data_status.config(text="● Data: STREAMING", fg='#a5d6a7')
                elif time_since_last_data < connection_timeout:
                    self.conn_status.config(text="● ESP32: CONNECTED", fg='#ffcc80')
                    self.data_status.config(text="● Data: INTERMITTENT", fg='#ffcc80')
                else:
                    self.conn_status.config(text="● ESP32: DISCONNECTED", fg='#ef9a9a')
                    self.data_status.config(text="● Data: NO SIGNAL", fg='#ef9a9a')
            else:
                if time_since_last_data < 2:
                    self.conn_status.config(text="● ESP32: CONNECTING...", fg='#ffcc80')
                    self.data_status.config(text="● Data: CHECKING", fg='#ffcc80')
                else:
                    self.conn_status.config(text="● ESP32: DISCONNECTED", fg='#ef9a9a')
                    self.data_status.config(text="● Data: WAITING", fg='#ef9a9a')
            
            # Update charts
            self.update_charts()
            
        except Exception as e:
            # Silently handle GUI update errors
            pass
    
    def update_charts(self):
        """Update the charts"""
        try:
            self.ax[0][0].clear()
            if hr_buf:
                self.ax[0][0].plot(hr_buf[-150:], color='#7e57c2', linewidth=2.5)
            self.ax[0][0].set_title("Heart Rate (BPM)", fontweight='bold', color='#5e35b1', fontsize=11)
            self.ax[0][0].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
            self.ax[0][0].set_facecolor('#ede7f6')
            
            self.ax[0][1].clear()
            if spo2_buf:
                self.ax[0][1].plot(spo2_buf[-150:], color='#5e35b1', linewidth=2.5)
            self.ax[0][1].set_title("SpO₂ (%)", fontweight='bold', color='#5e35b1', fontsize=11)
            self.ax[0][1].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
            self.ax[0][1].set_facecolor('#ede7f6')
            
            self.ax[1][0].clear()
            if temp_buf:
                self.ax[1][0].plot(temp_buf[-150:], color='#4527a0', linewidth=2.5)
            self.ax[1][0].set_title("Temperature (°C)", fontweight='bold', color='#5e35b1', fontsize=11)
            self.ax[1][0].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
            self.ax[1][0].set_facecolor('#ede7f6')
            
            self.ax[1][1].clear()
            if hum_buf:
                self.ax[1][1].plot(hum_buf[-150:], color='#9575cd', linewidth=2.5)
            self.ax[1][1].set_title("Humidity (%)", fontweight='bold', color='#5e35b1', fontsize=11)
            self.ax[1][1].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
            self.ax[1][1].set_facecolor('#ede7f6')
            
            self.ax[2][0].clear()
            if lat_buf:
                self.ax[2][0].plot(lat_buf[-150:], color='#b39ddb', linewidth=2.5)
            self.ax[2][0].set_title("Latency (ms)", fontweight='bold', color='#5e35b1', fontsize=11)
            self.ax[2][0].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
            self.ax[2][0].set_facecolor('#ede7f6')
            
            self.ax[2][1].clear()
            if thr_buf:
                self.ax[2][1].plot(thr_buf[-150:], color='#d1c4e9', linewidth=2.5)
            self.ax[2][1].set_title("Throughput (bps)", fontweight='bold', color='#5e35b1', fontsize=11)
            self.ax[2][1].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
            self.ax[2][1].set_facecolor('#ede7f6')
            
            self.canvas.draw()
        except:
            pass

    # --------------------------------------------------------
    # SDN vs TRADITIONAL COMPARISON TAB
    # --------------------------------------------------------
    def compare_tab(self):
        fig, self.cax = plt.subplots(1, 3, figsize=(14, 6), facecolor='#f5f1fe')
        fig.subplots_adjust(wspace=0.3)
        
        canvas = FigureCanvasTkAgg(fig, master=self.tab_compare)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)
        
        # Initial comparison
        self.compare()

    def compare(self):
        t, thr_sdn, lat_sdn, e_sdn = simulate("SDN")
        t, thr_tr, lat_tr, e_tr = simulate("Traditional")

        colors = {'SDN': '#7e57c2', 'Traditional': '#ff9800'}  # Purple vs Orange
        
        for ax in self.cax:
            ax.set_facecolor('#ede7f6')
            ax.spines['bottom'].set_color('#b39ddb')
            ax.spines['top'].set_color('#b39ddb')
            ax.spines['right'].set_color('#b39ddb')
            ax.spines['left'].set_color('#b39ddb')
            ax.tick_params(colors='#5e35b1')
        
        self.cax[0].clear()
        self.cax[0].plot(t, thr_sdn, label="SDN", color=colors['SDN'], linewidth=3, marker='o', markersize=4)
        self.cax[0].plot(t, thr_tr, label="Traditional", color=colors['Traditional'], 
                        linewidth=3, linestyle='--', marker='s', markersize=4)
        self.cax[0].set_title("Throughput Comparison", fontweight='bold', color='#5e35b1', fontsize=12)
        self.cax[0].set_xlabel("Time (s)", color='#5e35b1')
        self.cax[0].set_ylabel("Throughput", color='#5e35b1')
        self.cax[0].legend(framealpha=0.9, facecolor='white')
        self.cax[0].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
        self.cax[0].set_facecolor('#ede7f6')
        
        self.cax[1].clear()
        self.cax[1].plot(t, lat_sdn, label="SDN", color=colors['SDN'], linewidth=3, marker='o', markersize=4)
        self.cax[1].plot(t, lat_tr, label="Traditional", color=colors['Traditional'], 
                        linewidth=3, linestyle='--', marker='s', markersize=4)
        self.cax[1].set_title("Latency Comparison", fontweight='bold', color='#5e35b1', fontsize=12)
        self.cax[1].set_xlabel("Time (s)", color='#5e35b1')
        self.cax[1].set_ylabel("Latency (ms)", color='#5e35b1')
        self.cax[1].legend(framealpha=0.9, facecolor='white')
        self.cax[1].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
        self.cax[1].set_facecolor('#ede7f6')
        
        self.cax[2].clear()
        self.cax[2].plot(t, e_sdn, label="SDN", color=colors['SDN'], linewidth=3, marker='o', markersize=4)
        self.cax[2].plot(t, e_tr, label="Traditional", color=colors['Traditional'], 
                        linewidth=3, linestyle='--', marker='s', markersize=4)
        self.cax[2].set_title("Energy Consumption", fontweight='bold', color='#5e35b1', fontsize=12)
        self.cax[2].set_xlabel("Time (s)", color='#5e35b1')
        self.cax[2].set_ylabel("Energy Level", color='#5e35b1')
        self.cax[2].legend(framealpha=0.9, facecolor='white')
        self.cax[2].grid(True, alpha=0.2, linestyle='--', color='#b39ddb')
        self.cax[2].set_facecolor('#ede7f6')
        
        self.cax[0].figure.canvas.draw()

    # --------------------------------------------------------
    # ENHANCED NETWORK TOPOLOGY TAB
    # --------------------------------------------------------
    def topology_tab(self):
        self.topology_frame = tk.Frame(self.tab_topology, bg='#f5f1fe')
        self.topology_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Control panel with purple theme
        control_frame = tk.Frame(self.topology_frame, bg='#f5f1fe')
        control_frame.pack(fill='x', pady=(0, 20))
        
        tk.Button(control_frame, text="Generate New Topology", 
                  bg='#7e57c2', fg='white', font=self.subtitle_font,
                  activebackground='#9575cd', activeforeground='white',
                  relief='flat', cursor='hand2',
                  command=self.show_topology).pack(side='left')
        
        self.node_count = tk.IntVar(value=25)
        tk.Scale(control_frame, from_=10, to=50, variable=self.node_count,
                orient='horizontal', label="Node Count:",
                bg='#f5f1fe', fg='#5e35b1',
                troughcolor='#d1c4e9',
                activebackground='#7e57c2',
                length=250, font=self.normal_font).pack(side='left', padx=40)
        
        # Create figure with purple theme
        self.topology_fig = plt.figure(figsize=(10, 8), facecolor='#f5f1fe')
        self.taxa = self.topology_fig.add_subplot(111)
        
        canvas = FigureCanvasTkAgg(self.topology_fig, master=self.topology_frame)
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Initial topology
        self.show_topology()

    def show_topology(self):
        nodes = self.node_count.get()
        G, pos, battery, node_types, traffic_load, node_colors = generate_enhanced_topology(nodes)
        
        self.taxa.clear()
        self.taxa.set_facecolor('#ede7f6')
        
        # Draw edges with purple gradient
        for (u, v) in G.edges():
            edge_load = (traffic_load[u] + traffic_load[v]) / 2
            width = 1 + edge_load * 4
            alpha = 0.3 + edge_load * 0.4
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], 
                                  width=width, alpha=alpha, edge_color='#9575cd',
                                  style='dashed' if edge_load < 0.5 else 'solid',
                                  ax=self.taxa)
        
        # Draw nodes with purple color scheme
        node_sizes = []
        node_edge_colors = []
        for node in G.nodes():
            if node_types[node] == 'sensor':
                node_sizes.append(400)
                node_edge_colors.append('#5e35b1')
            elif node_types[node] == 'router':
                node_sizes.append(600)
                node_edge_colors.append('#4527a0')
            elif node_types[node] == 'gateway':
                node_sizes.append(900)
                node_edge_colors.append('#311b92')
            else:  # controller
                node_sizes.append(1200)
                node_edge_colors.append('#1a237e')
        
        # Use purple colormap
        scatter = nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                                        node_size=node_sizes,
                                        cmap=plt.cm.Purples,
                                        alpha=0.9,
                                        edgecolors=node_edge_colors,
                                        linewidths=2,
                                        ax=self.taxa)
        
        # Add node labels
        labels = {node: f"{battery[node]}%" for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=9, 
                               font_weight='bold', font_color='#311b92', ax=self.taxa)
        
        # Add legend with purple theme
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', label='Sensor',
                      markerfacecolor='#b39ddb', markersize=12, markeredgecolor='#5e35b1', markeredgewidth=2),
            plt.Line2D([0], [0], marker='o', color='w', label='Router',
                      markerfacecolor='#9575cd', markersize=12, markeredgecolor='#4527a0', markeredgewidth=2),
            plt.Line2D([0], [0], marker='o', color='w', label='Gateway',
                      markerfacecolor='#7e57c2', markersize=12, markeredgecolor='#311b92', markeredgewidth=2),
            plt.Line2D([0], [0], marker='*', color='w', label='Controller',
                      markerfacecolor='#5e35b1', markersize=15, markeredgecolor='#1a237e', markeredgewidth=2)
        ]
        self.taxa.legend(handles=legend_elements, loc='upper right', 
                        facecolor='#f5f1fe', edgecolor='#d1c4e9', framealpha=0.9)
        
        self.taxa.set_title("Wireless Sensor Network Topology", 
                           fontweight='bold', fontsize=14, color='#5e35b1', pad=20)
        self.taxa.grid(True, alpha=0.1, color='#b39ddb')
        
        # Add colorbar for traffic load with purple theme
        sm = plt.cm.ScalarMappable(cmap=plt.cm.Purples, 
                                  norm=plt.Normalize(vmin=0, vmax=1))
        sm.set_array([])
        cbar = self.topology_fig.colorbar(sm, ax=self.taxa, shrink=0.8)
        cbar.set_label('Traffic Load', rotation=270, labelpad=20, color='#5e35b1', fontweight='bold')
        cbar.ax.yaxis.set_tick_params(color='#5e35b1')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#5e35b1')
        
        self.topology_fig.tight_layout()
        self.taxa.figure.canvas.draw()

    # --------------------------------------------------------
    # ENHANCED SDN CONTROLLER TAB WITH PURPLE THEME
    # --------------------------------------------------------
    def sdn_tab(self):
        # Header with gradient purple
        header = tk.Frame(self.tab_sdn, bg='#7e57c2', height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="SDN Controller – Real-Time Engine",
                 font=("Segoe UI", 16, "bold"),
                 bg='#7e57c2', fg='white').pack(pady=20)
        
        # Main content frame
        content_frame = tk.Frame(self.tab_sdn, bg='#f5f1fe')
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Left panel for status and stats
        left_panel = tk.Frame(content_frame, bg='#f5f1fe')
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Right panel for SDN log
        right_panel = tk.Frame(content_frame, bg='#f5f1fe')
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Device Status Card
        status_card = tk.Frame(left_panel, bg='white', relief='flat', highlightbackground='#d1c4e9',
                              highlightthickness=2)
        status_card.pack(fill='x', pady=(0, 15))
        
        card_header1 = tk.Frame(status_card, bg='#7e57c2', height=40)
        card_header1.pack(fill='x')
        card_header1.pack_propagate(False)
        
        tk.Label(card_header1, text="Device Status", 
                 font=self.subtitle_font, bg='#7e57c2', fg='white').pack(pady=10)
        
        self.device_status = tk.Text(status_card, width=40, height=8,
                                     bg='#0a0a1a', fg='#d1c4e9', 
                                     font=('Consolas', 10), relief='flat',
                                     insertbackground='#7e57c2')
        self.device_status.pack(padx=10, pady=10)
        
        # Packet Statistics Card
        stats_card = tk.Frame(left_panel, bg='white', relief='flat', highlightbackground='#d1c4e9',
                             highlightthickness=2)
        stats_card.pack(fill='x', pady=(0, 15))
        
        card_header2 = tk.Frame(stats_card, bg='#5e35b1', height=40)
        card_header2.pack(fill='x')
        card_header2.pack_propagate(False)
        
        tk.Label(card_header2, text="Packet Statistics", 
                 font=self.subtitle_font, bg='#5e35b1', fg='white').pack(pady=10)
        
        self.packet_stats = tk.Text(stats_card, width=40, height=8,
                                    bg='#0a1a0a', fg='#c8e6c9',
                                    font=('Consolas', 10), relief='flat',
                                    insertbackground='#5e35b1')
        self.packet_stats.pack(padx=10, pady=10)
        
        # Live Sensor Data Card
        live_card = tk.Frame(left_panel, bg='white', relief='flat', highlightbackground='#d1c4e9',
                            highlightthickness=2)
        live_card.pack(fill='x')
        
        card_header3 = tk.Frame(live_card, bg='#4527a0', height=40)
        card_header3.pack(fill='x')
        card_header3.pack_propagate(False)
        
        tk.Label(card_header3, text="Live Sensor Data", 
                 font=self.subtitle_font, bg='#4527a0', fg='white').pack(pady=10)
        
        self.live_values = tk.Text(live_card, width=40, height=10,
                                   bg='#0a0a2a', fg='#d1c4e9',
                                   font=('Consolas', 10), relief='flat',
                                   insertbackground='#4527a0')
        self.live_values.pack(padx=10, pady=10)
        
        # SDN Decision Log Card
        log_card = tk.Frame(right_panel, bg='white', relief='flat', highlightbackground='#d1c4e9',
                           highlightthickness=2)
        log_card.pack(fill='both', expand=True)
        
        card_header4 = tk.Frame(log_card, bg='#311b92', height=40)
        card_header4.pack(fill='x')
        card_header4.pack_propagate(False)
        
        tk.Label(card_header4, text="SDN Routing Decisions", 
                 font=self.subtitle_font, bg='#311b92', fg='white').pack(pady=10)
        
        # Add scrollbar to log
        log_frame = tk.Frame(log_card, bg='white')
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.sdn_log = tk.Text(log_frame, width=60, height=30,
                               bg='#0a0a0a', fg='#e1d8f0',
                               yscrollcommand=scrollbar.set,
                               font=('Consolas', 9), relief='flat',
                               insertbackground='#7e57c2')
        self.sdn_log.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.sdn_log.yview)

    # --------------------------------------------------------
    # START SDN CONTROLLER
    # --------------------------------------------------------
    def start_sdn(self):
        threading.Thread(target=self.update_device_status, daemon=True).start()
        threading.Thread(target=self.update_packet_stats, daemon=True).start()
        threading.Thread(target=self.sdn_loop_snapshot, daemon=True).start()
        
        # Update status indicators
        self.sdn_status.config(text="● SDN: ACTIVE", fg='#a5d6a7')

    # --------------------------------------------------------
    # DEVICE STATUS PANEL UPDATER
    # --------------------------------------------------------
    def update_device_status(self):
        while True:
            try:
                time_since_last_data = time.time() - last_successful_data
                
                if esp32_connected:
                    if time_since_last_data < 5:
                        status_color = '#a5d6a7'
                        status_text = "CONNECTED ✓"
                    elif time_since_last_data < connection_timeout:
                        status_color = '#ffcc80'
                        status_text = "CONNECTED (SLOW) ⚠"
                    else:
                        status_color = '#ef9a9a'
                        status_text = "DISCONNECTED ✗"
                else:
                    if time_since_last_data < 2:
                        status_color = '#ffcc80'
                        status_text = "CONNECTING... ⚡"
                    else:
                        status_color = '#ef9a9a'
                        status_text = "DISCONNECTED ✗"

                # Update in main thread
                self.root.after(0, self.update_device_status_text, status_text, status_color, time_since_last_data)
            except:
                pass
            time.sleep(1)
    
    def update_device_status_text(self, status_text, status_color, time_since_last_data):
        """Update device status text in main thread"""
        try:
            self.device_status.delete("1.0", "end")
            self.device_status.insert("end", f"╔{'═'*38}╗\n")
            self.device_status.insert("end", "║           DEVICE STATUS           ║\n")
            self.device_status.insert("end", f"╠{'═'*38}╣\n")
            self.device_status.insert("end", f"║ ESP32 Status: {status_text:20} ║\n")
            self.device_status.insert("end", f"║ Last Data:    {time_since_last_data:5.1f} sec ago        ║\n")
            self.device_status.insert("end", f"╠{'═'*38}╣\n")
            self.device_status.insert("end", "║          Active Sensors:         ║\n")
            self.device_status.insert("end", "║ • Temperature Sensor             ║\n")
            self.device_status.insert("end", "║ • Humidity Sensor                ║\n")
            self.device_status.insert("end", "║ • Heart Rate Sensor              ║\n")
            self.device_status.insert("end", "║ • SpO₂ Sensor                    ║\n")
            self.device_status.insert("end", f"╚{'═'*38}╝\n")

            # Update status color in text widget
            self.device_status.tag_add("status", "4.15", "4.35")
            self.device_status.tag_config("status", foreground=status_color)
        except:
            pass

    # --------------------------------------------------------
    # PACKET STATISTICS PANEL UPDATER
    # --------------------------------------------------------
    def update_packet_stats(self):
        while True:
            try:
                total = packet_hr + packet_spo2 + packet_temp + packet_hum
                
                # Update in main thread
                self.root.after(0, self.update_packet_stats_text, total)
            except:
                pass
            time.sleep(1)
    
    def update_packet_stats_text(self, total):
        """Update packet stats text in main thread"""
        try:
            self.packet_stats.delete("1.0", "end")
            self.packet_stats.insert("end", f"╔{'═'*38}╗\n")
            self.packet_stats.insert("end", "║        PACKET STATISTICS         ║\n")
            self.packet_stats.insert("end", f"╠{'═'*38}╣\n")
            self.packet_stats.insert("end", f"║ Temperature : {packet_temp:6d} packets      ║\n")
            self.packet_stats.insert("end", f"║ Humidity    : {packet_hum:6d} packets      ║\n")
            self.packet_stats.insert("end", f"║ Heart Rate  : {packet_hr:6d} packets      ║\n")
            self.packet_stats.insert("end", f"║ SpO₂        : {packet_spo2:6d} packets      ║\n")
            self.packet_stats.insert("end", f"╠{'═'*38}╣\n")
            self.packet_stats.insert("end", f"║ Total       : {total:6d} packets      ║\n")
            self.packet_stats.insert("end", f"╚{'═'*38}╝\n")
        except:
            pass

    # --------------------------------------------------------
    # SDN SNAPSHOT ENGINE
    # --------------------------------------------------------
    def sdn_loop_snapshot(self):
        while True:
            try:
                if not (hr_buf and spo2_buf and temp_buf and hum_buf):
                    self.root.after(0, self.append_to_sdn_log, "\n⚠️  Waiting for sensor data...\n")
                    time.sleep(2)
                    continue

                hr = hr_buf[-1]
                spo2 = spo2_buf[-1]
                temp = temp_buf[-1]
                hum = hum_buf[-1]

                # Classify states
                hr_state = "HIGH" if hr > 120 else "Normal"
                spo2_state = "LOW" if spo2 < 95 else "Normal"
                temp_state = "HIGH" if temp > 38 else "Normal"
                hum_state = "HIGH" if hum > 85 else "Normal"

                # SDN decision with purple theme colors
                if spo2_state == "LOW":
                    decision = "Medical Priority Path"
                    decision_color = "#ef5350"
                elif hr_state == "HIGH":
                    decision = "Emergency Routing"
                    decision_color = "#ff9800"
                elif temp_state == "HIGH":
                    decision = "Alert Routing"
                    decision_color = "#ffb74d"
                elif hum_state == "HIGH":
                    decision = "Environmental Routing"
                    decision_color = "#4fc3f7"
                else:
                    decision = "Normal Routing"
                    decision_color = "#81c784"

                # Update live values in main thread
                self.root.after(0, self.update_live_values, temp, hum, hr, spo2, temp_state, hum_state, hr_state, spo2_state)
                
                # Create snapshot
                timestamp = time.strftime("%H:%M:%S")
                snapshot = f"""
╔{'═'*52}╗
║{' ':20}SDN SNAPSHOT [{timestamp}]{' ':20}║
╠{'═'*52}╣
║ Temp : {temp:6.1f}°C ({temp_state:10}){' ':18}║
║ Hum  : {hum:6.1f}%  ({hum_state:10}){' ':18}║
║ HR   : {hr:6.1f} BPM ({hr_state:10}){' ':18}║
║ SpO₂ : {spo2:6.1f}%  ({spo2_state:10}){' ':18}║
╠{'─'*52}╣
║ {decision:50} ║
╚{'═'*52}╝

"""
                
                # Update SDN log in main thread
                self.root.after(0, self.append_to_sdn_log, snapshot, decision, decision_color)
            except:
                pass
            time.sleep(2)
    
    def update_live_values(self, temp, hum, hr, spo2, temp_state, hum_state, hr_state, spo2_state):
        """Update live values in main thread"""
        try:
            self.live_values.delete("1.0", "end")
            self.live_values.insert("end", f"╔{'═'*38}╗\n")
            self.live_values.insert("end", "║        LIVE SENSOR DATA         ║\n")
            self.live_values.insert("end", f"╠{'═'*38}╣\n")
            self.live_values.insert("end", f"║ Temperature : {temp:6.1f} °C ({temp_state:6}) ║\n")
            self.live_values.insert("end", f"║ Humidity    : {hum:6.1f} %  ({hum_state:6}) ║\n")
            self.live_values.insert("end", f"║ Heart Rate  : {hr:6.1f} BPM ({hr_state:6}) ║\n")
            self.live_values.insert("end", f"║ SpO₂        : {spo2:6.1f} %  ({spo2_state:6}) ║\n")
            self.live_values.insert("end", f"╚{'═'*38}╝\n")
        except:
            pass
    
    def append_to_sdn_log(self, text, decision=None, decision_color=None):
        """Append text to SDN log in main thread"""
        try:
            self.sdn_log.insert("end", text)
            self.sdn_log.see("end")
            
            if decision:
                # Apply color to decision line
                lines = self.sdn_log.get("1.0", "end").split('\n')
                for i, line in enumerate(lines):
                    if decision.strip("║ ") in line:
                        line_num = i + 1
                        self.sdn_log.tag_add("decision", f"{line_num}.3", f"{line_num}.51")
                        self.sdn_log.tag_config("decision", foreground=decision_color, font=('Consolas', 9, 'bold'))
                        break
        except:
            pass


# ============================================================
# SIMULATION (SDN vs TRADITIONAL)
# ============================================================
def simulate(mode):
    t = list(range(30))
    if mode == "SDN":
        thr_base, lat_base, e_base = 0.55, 4.6, 9
    else:
        thr_base, lat_base, e_base = 0.48, 5.2, 10

    thr = [thr_base + random.uniform(-0.02, 0.02) for _ in t]
    lat = [lat_base + random.uniform(-0.25, 0.25) for _ in t]

    e = e_base
    energy = []

    for _ in t:
        e -= random.uniform(0.05, 0.15)
        energy.append(max(e, 2))

    return t, thr, lat, energy


# ============================================================
# ENHANCED TOPOLOGY GENERATOR
# ============================================================
def generate_enhanced_topology(n):
    G = nx.random_geometric_graph(n, 0.35)
    pos = nx.get_node_attributes(G, "pos")
    
    # Enhanced node attributes
    battery = {node: random.randint(10, 100) for node in G.nodes()}
    node_types = {node: random.choice(['sensor', 'router', 'gateway', 'controller']) 
                  for node in G.nodes()}
    traffic_load = {node: random.uniform(0.1, 0.9) for node in G.nodes()}
    
    # Color mapping
    node_colors = []
    for node in G.nodes():
        if node_types[node] == 'sensor':
            node_colors.append(traffic_load[node])
        elif node_types[node] == 'router':
            node_colors.append(0.5 + traffic_load[node] * 0.5)
        elif node_types[node] == 'gateway':
            node_colors.append(0.8)
        else:  # controller
            node_colors.append(1.0)
    
    return G, pos, battery, node_types, traffic_load, node_colors


# ============================================================
# APPLICATION STARTER FUNCTIONS
# ============================================================
def start_auth_screen():
    """Start the authentication screen"""
    auth_root = tk.Tk()
    auth_app = AuthScreen(auth_root)
    auth_root.mainloop()

def start_main_app(username):
    """Start the main dashboard application"""
    global root
    root = tk.Tk()
    app = App(root, username)
    root.mainloop()


# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    # Start with authentication screen
    start_auth_screen()