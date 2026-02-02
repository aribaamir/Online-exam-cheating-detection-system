# student.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import cv2
import time
import socket
import pickle
import struct
import numpy as np
import traceback
import pygetwindow as gw
import keyboard
from datetime import datetime

class StudentApp(tk.Tk):
    def __init__(self):  # FIXED: Was _init before
        super().__init__()
        self.title("Student Identification & Exam Client")
        self.geometry("500x400")
        
        # State variables
        self.running = False
        self.identified = False
        self.cap = None
        self.sock = None
        self.cheat_sock = None
        self.monitoring_active = False
        
        # Server configuration
        self.server_host = "Change to your server IP"  
        self.server_port = 9999
        self.cheat_port = 8888
        
        # Student info
        self.student_name = ""
        self.student_id = ""
        
        # Monitoring variables
        self.exam_window = "Student Identification & Exam Client"
        self.last_window = ""
        
        # Alert tracking
        self.alerts_sent = 0
        self.last_alert_time = None
        self.alert_lock = threading.Lock()
        
        # Connection state
        self.cheat_connected = False
        self.reconnect_attempts = 0
        
        self.setup_ui()
        self.setup_periodic_tasks()
    
    def setup_periodic_tasks(self):
        """Setup periodic checks"""
        self.after(1000, self.check_connections)
    
    def check_connections(self):
        """Periodically check connections"""
        if self.monitoring_active:
            status = "Monitoring: ACTIVE"
            if self.cheat_sock and self.cheat_connected:
                status += " | Socket: ✓ Connected"
            else:
                status += " | Socket: ✗ Disconnected"
            status += f" | Alerts: {self.alerts_sent}"
            self.monitor_status_var.set(status)
        
        # Reschedule
        self.after(2000, self.check_connections)
    
    def setup_ui(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Identification
        self.ident_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ident_frame, text='Identification')
        
        ttk.Label(self.ident_frame, text="Student Identification", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Name and ID inputs
        input_frame = ttk.Frame(self.ident_frame)
        input_frame.pack(pady=10, padx=20, fill='x')
        
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(input_frame, textvariable=self.name_var, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(input_frame, text="ID:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.id_var = tk.StringVar()
        self.id_entry = ttk.Entry(input_frame, textvariable=self.id_var, width=30)
        self.id_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Status display
        self.status_var = tk.StringVar(value="Enter your name and ID, then click Connect.")
        status_label = ttk.Label(self.ident_frame, textvariable=self.status_var, 
                                wraplength=400, justify='center')
        status_label.pack(pady=10, padx=20)
        
        # Camera preview
        self.camera_label = ttk.Label(self.ident_frame, text="Camera: Off", 
                                     relief='solid', borderwidth=1)
        self.camera_label.pack(pady=10, padx=20, fill='both', expand=True)
        
        # Buttons
        button_frame = ttk.Frame(self.ident_frame)
        button_frame.pack(pady=10)
        
        self.connect_btn = ttk.Button(button_frame, text="Connect", 
                                     command=self.connect_and_identify)
        self.connect_btn.pack(side='left', padx=5)
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", 
                                        state="disabled", command=self.disconnect)
        self.disconnect_btn.pack(side='left', padx=5)
        
        # Tab 2: Exam
        self.exam_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.exam_frame, text='Exam')
        
        ttk.Label(self.exam_frame, text="Exam Interface", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Exam instructions
        instructions_frame = ttk.LabelFrame(self.exam_frame, text="Exam Instructions")
        instructions_frame.pack(pady=10, padx=20, fill='x')
        
        instructions = """
        1. Do NOT switch to other windows
        2. Do NOT use copy (Ctrl+C) or paste (Ctrl+V)
        3. Keep this window active
        4. Your activity is being monitored
        5. Do NOT use Alt+Tab
        
        Violations will be reported to the proctor.
        """
        
        ttk.Label(instructions_frame, text=instructions, justify='left', 
                 wraplength=400).pack(pady=10, padx=10)
        
        # Start and Stop Exam buttons
        button_frame_exam = ttk.Frame(self.exam_frame)
        button_frame_exam.pack(pady=10)
        
        self.start_exam_btn = ttk.Button(button_frame_exam, text="Start Exam", 
                                        command=self.start_exam_monitoring)
        self.start_exam_btn.pack(side='left', padx=5)
        
        self.stop_exam_btn = ttk.Button(button_frame_exam, text="Stop Exam", 
                                       state="disabled", command=self.stop_exam_monitoring)
        self.stop_exam_btn.pack(side='left', padx=5)
        
        # Monitoring status
        self.monitor_status_var = tk.StringVar(value="Monitoring: OFF | Alerts: 0")
        ttk.Label(self.exam_frame, textvariable=self.monitor_status_var,
                 font=("Arial", 10)).pack(pady=5)
        
        # Alert test button
        test_frame = ttk.Frame(self.exam_frame)
        test_frame.pack(pady=5)
        
        self.test_alert_btn = ttk.Button(test_frame, text="Test Alert", 
                                       command=self.test_alert_send,
                                       state="disabled")
        self.test_alert_btn.pack()
        
        # Exam content
        exam_content_frame = ttk.LabelFrame(self.exam_frame, text="Exam Questions")
        exam_content_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        exam_content = """
        Mathematics Test
        ================
        
        1. Solve: 2x + 5 = 15
        Answer: 
        
        2. What is the value of π (pi) to two decimal places?
        Answer: 
        
        3. Calculate the area of a circle with radius 7cm.
        Answer: 
        
        4. Simplify: (3 + 4) × 2 - 5
        Answer: 
        
        5. What is 15% of 200?
        Answer: 
        """
        
        self.exam_text = tk.Text(exam_content_frame, height=15, wrap='word')
        self.exam_text.pack(pady=10, padx=10, fill='both', expand=True)
        self.exam_text.insert('1.0', exam_content)
        
        # Disable exam tab initially
        self.notebook.tab(1, state='disabled')
    
    def test_alert_send(self):
        """Test function to check if alerts work"""
        print("[TEST] Sending test alert...")
        success = self.send_cheating_alert("TEST: This is a test alert from student")
        if success:
            messagebox.showinfo("Test Alert", f"✓ Test alert sent successfully!\nTotal alerts: {self.alerts_sent}")
        else:
            messagebox.showerror("Test Alert", "✗ Failed to send test alert. Check console.")
    
    def connect_and_identify(self):
        if self.running:
            return
        
        self.student_name = self.name_var.get().strip()
        self.student_id = self.id_var.get().strip()
        
        if not self.student_name or not self.student_id:
            self.status_var.set("Please enter both name and ID.")
            return
        
        self.running = True
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_var.set("Connecting to server...")
        
        threading.Thread(target=self.connect_to_server, daemon=True).start()
    
    def connect_to_server(self):
        try:
            # Connect to identification server
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.server_host, self.server_port))
            
            print(f"[CLIENT] ✓ Connected to server at {self.server_host}:{self.server_port}")
            
            # Send student info
            student_info = {
                "name": self.student_name,
                "id": self.student_id
            }
            
            meta_bytes = pickle.dumps(student_info)
            self.sock.sendall(struct.pack("Q", len(meta_bytes)) + meta_bytes)
            
            print(f"[CLIENT] Sent student info: {self.student_name} (ID: {self.student_id})")
            
            # Wait for verification response
            response_size_data = self._recv_exact(self.sock, 8)
            response_size = struct.unpack("Q", response_size_data)[0]
            response_bytes = self._recv_exact(self.sock, response_size)
            response = pickle.loads(response_bytes)
            
            print(f"[CLIENT] Server response: {response}")
            
            if response.get("status") == "identified":
                self.identified = True
                self.status_var.set(f"✓ IDENTIFIED — Starting camera...")
                
                # Get cheating detection port
                if "cheat_port" in response:
                    self.cheat_port = response["cheat_port"]
                    print(f"[CLIENT] Using cheat port: {self.cheat_port}")
                
                # Start camera
                self.after(0, self.start_camera_stream)
                
                # Enable exam tab
                self.after(0, lambda: self.notebook.tab(1, state='normal'))
                
                # Connect to cheating detection server
                print(f"[CLIENT] Connecting to cheating monitor on port {self.cheat_port}")
                threading.Thread(target=self.connect_to_cheating_monitor, daemon=True).start()
                
            else:
                self.status_var.set(f"✗ Verification failed: {response.get('message', 'Unknown error')}")
                self.running = False
                self.after(0, self.reset_connection)
                
        except ConnectionRefusedError:
            self.status_var.set("✗ Cannot connect to server. Make sure server is running.")
            self.running = False
            self.after(0, self.reset_connection)
        except Exception as e:
            print(f"[CLIENT] Error: {e}")
            traceback.print_exc()
            self.status_var.set(f"✗ Connection error: {str(e)}")
            self.running = False
            self.after(0, self.reset_connection)
    
    def _recv_exact(self, sock, size):
        """Receive exactly size bytes"""
        data = b""
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data
    
    def start_camera_stream(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.status_var.set("Camera access failed.")
                self.running = False
                return
            
            self.status_var.set("✓ Camera active. Stream starting...")
            
            threading.Thread(target=self.video_stream_loop, daemon=True).start()
            
        except Exception as e:
            print(f"[CLIENT] Camera error: {e}")
            self.status_var.set(f"Camera error: {str(e)}")
    
    def video_stream_loop(self):
        print("[CLIENT] Starting video stream...")
        frame_count = 0
        
        while self.running and self.identified and self.cap and self.sock:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                
                # Update camera preview
                preview_frame = cv2.resize(frame, (320, 240))
                preview_rgb = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
                preview_img = tk.PhotoImage(data=cv2.imencode('.ppm', preview_rgb)[1].tobytes())
                self.camera_label.config(image=preview_img, text="")
                self.camera_label.image = preview_img
                
                # Resize for transmission
                frame = cv2.resize(frame, (640, 480))
                
                # Encode as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                _, jpg_buffer = cv2.imencode('.jpg', frame, encode_param)
                jpg_bytes = jpg_buffer.tobytes()
                
                # Send frame
                frame_data = pickle.dumps(jpg_bytes)
                self.sock.sendall(struct.pack("Q", len(frame_data)) + frame_data)
                
                # Wait for ACK
                try:
                    ack_size_data = self._recv_exact(self.sock, 8)
                    ack_size = struct.unpack("Q", ack_size_data)[0]
                    ack_bytes = self._recv_exact(self.sock, ack_size)
                    ack = pickle.loads(ack_bytes)
                except:
                    pass
                
                # Update status
                if frame_count % 30 == 0:
                    self.status_var.set(f"✓ Streaming... Frames: {frame_count}")
                
                time.sleep(0.05)
                
            except ConnectionError:
                print("[CLIENT] Connection lost")
                break
            except Exception as e:
                print(f"[CLIENT] Stream error: {e}")
                if frame_count < 10:
                    break
                continue
        
        print("[CLIENT] Video stream ended")
        self.cleanup()
    
    def connect_to_cheating_monitor(self):
        """Connect to cheating detection server - FIXED"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"[CLIENT] Connection attempt {attempt + 1}/{max_retries} to {self.server_host}:{self.cheat_port}")
                
                # Create fresh socket
                if self.cheat_sock:
                    try:
                        self.cheat_sock.close()
                    except:
                        pass
                
                self.cheat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cheat_sock.settimeout(10)
                self.cheat_sock.connect((self.server_host, self.cheat_port))
                
                self.cheat_connected = True
                self.reconnect_attempts = 0
                
                print(f"[CLIENT] ✓✓✓ SUCCESS: Connected to cheating monitor on port {self.cheat_port}")
                self.after(0, lambda: self.test_alert_btn.config(state="normal"))
                return True
                
            except ConnectionRefusedError:
                print(f"[CLIENT] ✗ Server refused connection on port {self.cheat_port} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    print(f"[CLIENT] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
            except Exception as e:
                print(f"[CLIENT] Cheating monitor connection error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        print(f"[CLIENT] ✗✗✗ FAILED: Could not connect to cheating monitor after {max_retries} attempts")
        self.cheat_connected = False
        return False
    
    def start_exam_monitoring(self):
        """Start cheating monitoring"""
        if self.monitoring_active:
            return
        
        # Ensure cheat socket is connected
        if not self.cheat_sock or not self.cheat_connected:
            print("[MONITOR] Cheating socket not connected. Connecting now...")
            success = self.connect_to_cheating_monitor()
            if not success:
                messagebox.showerror("Connection Error", 
                                   "Failed to connect to cheating monitor.\n"
                                   "Make sure the teacher has started exam monitoring.")
                return
        
        self.monitoring_active = True
        self.start_exam_btn.config(state='disabled')
        self.stop_exam_btn.config(state='normal')
        self.monitor_status_var.set("Monitoring: ACTIVE | Alerts: 0")
        
        # Start monitoring threads
        threading.Thread(target=self.detect_window_change, daemon=True).start()
        threading.Thread(target=self.detect_copy_paste, daemon=True).start()
        threading.Thread(target=self.detect_tab_switch, daemon=True).start()
        
        # Switch to exam tab
        self.notebook.select(1)
        
        messagebox.showinfo("Exam Started", 
                          "Exam monitoring is now active!\n\n"
                          "Rules:\n"
                          "1. Do NOT switch windows\n"
                          "2. Do NOT use Ctrl+C or Ctrl+V\n"
                          "3. Keep this window active\n\n"
                          f"Connected to: {self.server_host}:{self.cheat_port}")
    
    def stop_exam_monitoring(self):
        """Stop cheating monitoring"""
        if not self.monitoring_active:
            return
        
        if messagebox.askyesno("Stop Exam", 
                              "Are you sure you want to stop the exam?\n\n"
                              "This will end monitoring and notify the proctor."):
            
            self.send_cheating_alert("Student manually stopped the exam")
            
            self.monitoring_active = False
            self.start_exam_btn.config(state='normal')
            self.stop_exam_btn.config(state='disabled')
            self.monitor_status_var.set(f"Monitoring: STOPPED | Alerts: {self.alerts_sent}")
            
            self.notebook.select(0)
            
            messagebox.showinfo("Exam Stopped", 
                              f"Exam monitoring has been stopped.\n"
                              f"Total alerts sent: {self.alerts_sent}")
    
    def detect_window_change(self):
        """Detect window changes"""
        print("[MONITOR] Window change detection started")
        while self.monitoring_active and self.running:
            try:
                time.sleep(0.5)
                
                current = gw.getActiveWindow()
                if current:
                    current_title = current.title
                    if current_title != self.last_window:
                        self.last_window = current_title
                        
                        if (self.exam_window not in current_title and 
                            current_title.strip() and
                            "Student Identification" not in current_title):
                            violation = f"Window switch: {current_title}"
                            print(f"[MONITOR] Detected: {violation}")
                            self.send_cheating_alert(violation)
                
            except Exception as e:
                print(f"[MONITOR] Window detection error: {e}")
                continue
    
    def detect_copy_paste(self):
        """Detect copy/paste attempts"""
        print("[MONITOR] Copy/paste detection started")
        
        ctrl_c_pressed = False
        ctrl_v_pressed = False
        
        while self.monitoring_active and self.running:
            try:
                if keyboard.is_pressed('ctrl') and keyboard.is_pressed('c'):
                    if not ctrl_c_pressed:
                        ctrl_c_pressed = True
                        violation = "Copy attempt (Ctrl+C) detected"
                        print(f"[MONITOR] Detected: {violation}")
                        self.send_cheating_alert(violation)
                else:
                    ctrl_c_pressed = False
                
                if keyboard.is_pressed('ctrl') and keyboard.is_pressed('v'):
                    if not ctrl_v_pressed:
                        ctrl_v_pressed = True
                        violation = "Paste attempt (Ctrl+V) detected"
                        print(f"[MONITOR] Detected: {violation}")
                        self.send_cheating_alert(violation)
                else:
                    ctrl_v_pressed = False
                
                time.sleep(0.05)
                    
            except Exception as e:
                print(f"[MONITOR] Copy/paste detection error: {e}")
                continue
    
    def detect_tab_switch(self):
        """Detect Alt+Tab usage"""
        print("[MONITOR] Tab switch detection started")
        
        alt_tab_pressed = False
        
        while self.monitoring_active and self.running:
            try:
                if keyboard.is_pressed('alt') and keyboard.is_pressed('tab'):
                    if not alt_tab_pressed:
                        alt_tab_pressed = True
                        violation = "Alt+Tab window switching detected"
                        print(f"[MONITOR] Detected: {violation}")
                        self.send_cheating_alert(violation)
                else:
                    alt_tab_pressed = False
                
                time.sleep(0.05)
                    
            except Exception as e:
                print(f"[MONITOR] Tab detection error: {e}")
                continue
    
    def send_cheating_alert(self, violation):
        """Send cheating alert to server - FIXED WITH PROPER PROTOCOL"""
        with self.alert_lock:
            try:
                # Check connection
                if not self.cheat_sock or not self.cheat_connected:
                    print(f"[ALERT] Socket not connected. Attempting reconnect...")
                    success = self.connect_to_cheating_monitor()
                    if not success:
                        print(f"[ALERT] ✗ Reconnection failed. Alert lost: {violation}")
                        return False
                
                # Format message
                timestamp = datetime.now().strftime("%H:%M:%S")
                alert_msg = f"{self.student_name} [{timestamp}]: {violation}"
                alert_bytes = alert_msg.encode('utf-8')
                
                print(f"[ALERT] Sending (len={len(alert_bytes)}): {alert_msg}")
                
                # FIXED: Use proper protocol with length header
                try:
                    # Create new socket for each alert (more reliable)
                    temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    temp_sock.settimeout(5.0)
                    temp_sock.connect((self.server_host, self.cheat_port))
                    
                    # Send length header + data
                    temp_sock.sendall(struct.pack("Q", len(alert_bytes)))
                    temp_sock.sendall(alert_bytes)
                    
                    print(f"[ALERT] Data sent, waiting for ACK...")
                    
                    # Wait for ACK
                    try:
                        ack_len_bytes = self._recv_exact(temp_sock, 8)
                        ack_len = struct.unpack("Q", ack_len_bytes)[0]
                        ack_bytes = self._recv_exact(temp_sock, ack_len)
                        ack = pickle.loads(ack_bytes)
                        
                        print(f"[ALERT] ✓✓✓ ACK received: {ack}")
                        
                        # Update counters
                        self.alerts_sent += 1
                        self.last_alert_time = datetime.now()
                        
                        # Update UI
                        self.after(0, lambda: self.monitor_status_var.set(
                            f"Monitoring: ACTIVE | Alerts: {self.alerts_sent}"))
                        
                        print(f"[ALERT] ✓ Successfully sent alert #{self.alerts_sent}")
                        
                        temp_sock.close()
                        return True
                        
                    except Exception as e:
                        print(f"[ALERT] ACK error: {e}")
                        temp_sock.close()
                        return False
                    
                except ConnectionRefusedError:
                    print(f"[ALERT] ✗ Connection refused")
                    self.cheat_connected = False
                    return False
                    
                except Exception as e:
                    print(f"[ALERT] Send error: {e}")
                    traceback.print_exc()
                    return False
                
            except Exception as e:
                print(f"[ALERT] ✗ Failed: {e}")
                traceback.print_exc()
                return False
    
    def disconnect(self):
        self.running = False
        self.monitoring_active = False
        self.status_var.set("Disconnecting...")
        self.disconnect_btn.config(state="disabled")
        threading.Thread(target=self.cleanup, daemon=True).start()
    
    def cleanup(self):
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
            if self.sock:
                self.sock.close()
                self.sock = None
            if self.cheat_sock:
                self.cheat_sock.close()
                self.cheat_sock = None
        except:
            pass
        
        self.running = False
        self.identified = False
        self.monitoring_active = False
        self.cheat_connected = False
        self.after(0, self.on_disconnected)
    
    def reset_connection(self):
        self.cleanup()
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
    
    def on_disconnected(self):
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.status_var.set("Disconnected. Ready to connect.")
        self.camera_label.config(image='', text="Camera: Off")
        self.notebook.tab(1, state='disabled')
        self.monitor_status_var.set("Monitoring: OFF")
        self.start_exam_btn.config(state='normal')
        self.stop_exam_btn.config(state='disabled')
        self.test_alert_btn.config(state="disabled")
        
        print(f"\n[SESSION SUMMARY]")
        print(f"  Total alerts sent: {self.alerts_sent}")
        if self.alerts_sent > 0 and self.last_alert_time:
            print(f"  Last alert time: {self.last_alert_time}")
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        self.monitoring_active = False
        self.cleanup()
        self.destroy()

if __name__ == "__main__":
    app = StudentApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()