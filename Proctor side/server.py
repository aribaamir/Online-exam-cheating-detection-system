import socket
import pickle
import struct
import threading
import cv2
import time
import numpy as np
import traceback
import csv
import re
from collections import deque
from datetime import datetime
from PyQt6 import QtCore

HEADER_FMT = "Q"

class ServerSignals(QtCore.QObject):
    new_student_connected = QtCore.pyqtSignal(dict)
    student_disconnected = QtCore.pyqtSignal(str)
    cheating_alert = QtCore.pyqtSignal(dict)

# Node for doubly linked list
class StudentNode:
    def __init__(self, client_key, student):
        self.client_key = client_key
        self.student = student
        self.next = None
        self.prev = None

# Doubly Linked List for connection management
class StudentLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0
        self.lookup = {}
    
    def append(self, client_key, student):
        new_node = StudentNode(client_key, student)
        
        if not self.head:
            self.head = self.tail = new_node
        else:
            new_node.prev = self.tail
            self.tail.next = new_node
            self.tail = new_node
        
        self.lookup[client_key] = new_node
        self.size += 1
        return new_node
    
    def remove(self, client_key):
        if client_key not in self.lookup:
            return False
        
        node = self.lookup[client_key]
        
        if node.prev:
            node.prev.next = node.next
        else:
            self.head = node.next
        
        if node.next:
            node.next.prev = node.prev
        else:
            self.tail = node.prev
        
        del self.lookup[client_key]
        self.size -= 1
        return True
    
    def get(self, client_key):
        node = self.lookup.get(client_key)
        return node.student if node else None
    
    def items(self):
        pairs = []
        current = self.head
        while current:
            pairs.append((current.client_key, current.student))
            current = current.next
        return pairs
    
    def values(self):
        students = []
        current = self.head
        while current:
            students.append(current.student)
            current = current.next
        return students
    
    def keys(self):
        keys = []
        current = self.head
        while current:
            keys.append(current.client_key)
            current = current.next
        return keys
    
    def __len__(self):
        return self.size

class ProctorServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999, 
                 cheat_port: int = 8888, csv_path: str = "students.csv"):
        self.host = host
        self.port = port
        self.cheat_port = cheat_port
        self.csv_path = csv_path
        
        self.student_database = self._load_student_database()
        print(f"[SERVER] Loaded {len(self.student_database)} students")
        
        self._sock = None
        self._cheat_sock = None
        self._running = False
        self._cheat_detection_active = False
        
        self._connected_students = StudentLinkedList()
        self._students_lock = threading.RLock()
        
        self._student_frames = {}
        
        self._alert_queue = deque(maxlen=1000)
        self._alert_queue_lock = threading.Lock()
        
        self._alert_processing = False
        self._alert_thread = None
        
        self._all_alerts = []
        self._all_alerts_lock = threading.Lock()
        
        self._student_history = {}
        self._exam_start_time = None
        
        self.signals = ServerSignals()
    
    def _load_student_database(self):
        student_db = {}
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    student_id = row.get('id', '').strip()
                    student_name = row.get('name', '').strip()
                    if student_id and student_name:
                        student_db[student_id] = student_name
            print(f"[SERVER] Database loaded: {len(student_db)} students")
        except Exception as e:
            print(f"[SERVER] Error loading CSV: {e}")
        return student_db
    
    def _start_alert_processor(self):
        self._alert_processing = True
        self._alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self._alert_thread.start()
        print("[SERVER] Alert processor started")
    
    def _process_alerts(self):
        while self._alert_processing:
            try:
                alert = None
                with self._alert_queue_lock:
                    if self._alert_queue:
                        alert = self._alert_queue.popleft()
                
                if alert:
                    self.signals.cheating_alert.emit(alert)
                    print(f"[SERVER] Signal emitted: {alert.get('student_name')} - {alert.get('violation')}")
                
                time.sleep(0.01)
                
            except Exception as e:
                print(f"[ALERT PROCESSOR] Error: {e}")
    
    def _stop_alert_processor(self):
        self._alert_processing = False
        if self._alert_thread:
            self._alert_thread.join(timeout=1.0)
        print("[SERVER] Alert processor stopped")
    
    def start(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self.host, self.port))
            self._sock.listen(10)
            self._running = True
            
            threading.Thread(target=self._accept_loop, daemon=True).start()
            
            print(f"[SERVER] Identification server on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[SERVER] Error starting: {e}")
            return False
    
    def start_cheating_detection(self):
        try:
            self._cheat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._cheat_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._cheat_sock.bind((self.host, self.cheat_port))
            self._cheat_sock.listen(20)
            self._cheat_detection_active = True
            self._exam_start_time = time.time()
            
            self._start_alert_processor()
            
            threading.Thread(target=self._accept_cheating_alerts, daemon=True).start()
            
            print(f"[SERVER] Cheating detection on {self.host}:{self.cheat_port}")
            return True
        except Exception as e:
            print(f"[SERVER] Error starting cheating detection: {e}")
            return False
    
    def _accept_cheating_alerts(self):
        """Accept cheating alert connections"""
        print("[CHEAT] Alert server listening...")
        while self._cheat_detection_active:
            try:
                client, addr = self._cheat_sock.accept()
                print(f"[CHEAT] New connection from {addr}")
                threading.Thread(target=self._handle_cheating_alert, 
                               args=(client, addr), daemon=True).start()
            except Exception as e:
                if self._cheat_detection_active:
                    print(f"[CHEAT] Accept error: {e}")
                break
    
    def _handle_cheating_alert(self, sock: socket.socket, addr: tuple):
        """Handle cheating alerts - FIXED WITH PROPER PROTOCOL"""
        try:
            sock.settimeout(10.0)
            print(f"[CHEAT] Handling alert from {addr}")
            
            # FIXED: Use proper protocol with length header
            try:
                # Read message length (8 bytes)
                len_bytes = self._recv_exact(sock, 8)
                msg_len = struct.unpack("Q", len_bytes)[0]
                print(f"[CHEAT] Message length: {msg_len} bytes")
                
                # Read exact message
                data = self._recv_exact(sock, msg_len)
                alert_text = data.decode('utf-8', errors='ignore').strip()
                
            except Exception as e:
                print(f"[CHEAT] Protocol error: {e}")
                traceback.print_exc()
                return
            
            print(f"[CHEAT] ✓ Received alert: '{alert_text}'")
            
            if not alert_text:
                print("[CHEAT] Empty alert received")
                return
            
            # Parse student name and message
            student_name = "Unknown"
            alert_message = alert_text
            
            # Extract student name (format: "Name [timestamp]: Alert message")
            match = re.match(r'^(.+?)\s*\[[\d:]+\]:\s*(.+)$', alert_text)
            if match:
                student_name = match.group(1).strip()
                alert_message = match.group(2).strip()
            else:
                # Try simpler format: "Name: Alert message"
                match = re.match(r'^(.+?):\s*(.+)$', alert_text)
                if match:
                    student_name = match.group(1).strip()
                    alert_message = match.group(2).strip()
            
            print(f"[CHEAT] Parsed: Student='{student_name}', Alert='{alert_message}'")
            
            # Determine severity
            severity = "low"
            alert_lower = alert_message.lower()
            
            if any(kw in alert_lower for kw in ["chatgpt", "openai", "chegg", "ai tool", "ai"]):
                severity = "high"
            elif any(kw in alert_lower for kw in ["copy", "paste", "ctrl+c", "ctrl+v"]):
                severity = "medium"
            elif any(kw in alert_lower for kw in ["window", "switch", "tab", "alt+tab"]):
                severity = "medium"
            
            # Create alert data
            timestamp = datetime.now().strftime("%H:%M:%S")
            alert_data = {
                'timestamp': timestamp,
                'student_name': student_name,
                'violation': alert_message,
                'severity': severity
            }
            
            # Store in global list
            with self._all_alerts_lock:
                self._all_alerts.append(alert_data)
            
            # Update student's data
            with self._students_lock:
                student_found = False
                for client_key, student in self._connected_students.items():
                    if student.name.lower() == student_name.lower():
                        student.cheating_alerts.append(alert_data)
                        
                        if not hasattr(student, 'activity_log'):
                            student.activity_log = []
                        student.activity_log.append(f"[{timestamp}] ⚠️ {alert_message}")
                        
                        student.cheating_score = min(100, len(student.cheating_alerts) * 10)
                        
                        student_found = True
                        print(f"[CHEAT] ✓ Updated student: {student_name}")
                        break
                
                if not student_found:
                    print(f"[CHEAT] ⚠ Student '{student_name}' not in connected list")
            
            # Add to queue for signal emission
            with self._alert_queue_lock:
                self._alert_queue.append(alert_data)
            
            print(f"[CHEAT] ✓ Alert queued for processing")
            
            # FIXED: Send acknowledgement with proper protocol
            try:
                ack_msg = pickle.dumps({"status": "received", "alert_id": len(self._all_alerts)})
                sock.sendall(struct.pack("Q", len(ack_msg)) + ack_msg)
                print(f"[CHEAT] ✓ ACK sent")
            except Exception as e:
                print(f"[CHEAT] ACK send error: {e}")
                
        except Exception as e:
            print(f"[CHEAT] Handler error: {e}")
            traceback.print_exc()
        finally:
            try:
                sock.close()
            except:
                pass
            print(f"[CHEAT] Connection closed for {addr}")
    
    def _accept_loop(self):
        while self._running:
            try:
                client, addr = self._sock.accept()
                threading.Thread(target=self._handle_client, 
                               args=(client, addr), daemon=True).start()
            except Exception as e:
                if self._running:
                    print(f"[SERVER] Accept error: {e}")
    
    def _handle_client(self, sock: socket.socket, addr: tuple):
        client_key = f"{addr[0]}:{addr[1]}"
        
        try:
            sock.settimeout(10.0)
            
            len_data = struct.unpack("Q", self._recv_exact(sock, 8))[0]
            data = self._recv_exact(sock, len_data)
            meta = pickle.loads(data)
            
            candidate_name = meta.get("name", "").strip()
            candidate_id = meta.get("id", "").strip()
            
            print(f"[SERVER] New student: {candidate_name} ({candidate_id})")
            
            is_verified = False
            if candidate_id in self.student_database:
                expected_name = self.student_database[candidate_id]
                if candidate_name.lower() == expected_name.lower():
                    is_verified = True
            
            from dataclasses import dataclass, field
            from typing import List
            
            @dataclass
            class ConnectedStudent:
                name: str
                id: str
                sock: socket.socket
                addr: tuple
                is_identified: bool = False
                frame_buffer: bytes = None
                last_frame_time: float = 0
                cheating_alerts: List[dict] = field(default_factory=list)
                activity_log: List[str] = field(default_factory=list)
                cheating_score: int = 0
                client_key: str = ""
            
            student = ConnectedStudent(
                name=candidate_name,
                id=candidate_id,
                sock=sock,
                addr=addr,
                is_identified=is_verified,
                last_frame_time=time.time(),
                client_key=client_key
            )
            
            with self._students_lock:
                self._connected_students.append(client_key, student)
            
            self._student_frames[client_key] = None
            
            if is_verified:
                result = {
                    "status": "identified",
                    "id": candidate_id,
                    "name": candidate_name,
                    "cheat_port": self.cheat_port
                }
            else:
                result = {
                    "status": "not_identified",
                    "id": candidate_id,
                    "name": candidate_name
                }
            
            result_bytes = pickle.dumps(result)
            sock.sendall(struct.pack("Q", len(result_bytes)) + result_bytes)
            
            self.signals.new_student_connected.emit({
                'id': candidate_id,
                'name': candidate_name,
                'is_identified': is_verified,
                'client_key': client_key,
                'cheating_score': 0
            })
            
            if is_verified:
                print(f"[SERVER] Starting video for {candidate_name}")
                while self._running:
                    try:
                        frame_len = struct.unpack("Q", self._recv_exact(sock, 8))[0]
                        frame_data = self._recv_exact(sock, frame_len)
                        jpg_buf = pickle.loads(frame_data)
                        
                        self._student_frames[client_key] = jpg_buf
                        
                        with self._students_lock:
                            node = self._connected_students.lookup.get(client_key)
                            if node:
                                node.student.last_frame_time = time.time()
                        
                        ack = pickle.dumps({"status": "ack"})
                        sock.sendall(struct.pack("Q", len(ack)) + ack)
                        
                    except ConnectionError:
                        break
                    except Exception as e:
                        if self._running:
                            print(f"[SERVER] Frame error: {e}")
                        break
            else:
                time.sleep(2)
                
        except Exception as e:
            print(f"[SERVER] Client error {client_key}: {e}")
            traceback.print_exc()
        finally:
            student_name = "Unknown"
            with self._students_lock:
                node = self._connected_students.lookup.get(client_key)
                if node:
                    student_name = node.student.name
                    
                    if node.student.is_identified:
                        self._save_student_history(node.student)
                    
                    self._connected_students.remove(client_key)
            
            if client_key in self._student_frames:
                del self._student_frames[client_key]
            
            print(f"[SERVER] Student disconnected: {student_name}")
            self.signals.student_disconnected.emit(student_name)
            
            try:
                sock.close()
            except:
                pass
    
    def _recv_exact(self, sock: socket.socket, size: int) -> bytes:
        """Receive exactly size bytes"""
        data = b""
        while len(data) < size and self._running:
            try:
                chunk = sock.recv(min(4096, size - len(data)))
                if not chunk:
                    raise ConnectionError("Client disconnected")
                data += chunk
            except socket.timeout:
                continue
            except Exception as e:
                raise ConnectionError(f"Socket error: {e}")
        return data
    
    def _save_student_history(self, student):
        if not student.id:
            return
        
        self._student_history[student.id] = {
            'name': student.name,
            'id': student.id,
            'alerts': student.cheating_alerts.copy() if hasattr(student, 'cheating_alerts') else [],
            'activity_log': student.activity_log.copy() if hasattr(student, 'activity_log') else [],
            'cheating_score': student.cheating_score if hasattr(student, 'cheating_score') else 0,
            'disconnection_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def stop(self):
        self._running = False
        self._cheat_detection_active = False
        
        self._stop_alert_processor()
        
        with self._students_lock:
            for client_key, student in self._connected_students.items():
                if student.is_identified:
                    self._save_student_history(student)
                try:
                    student.sock.close()
                except:
                    pass
            self._connected_students = StudentLinkedList()
        
        self._student_frames.clear()
        
        for sock in [self._sock, self._cheat_sock]:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        
        self._sock = None
        self._cheat_sock = None
        print("[SERVER] Stopped")
    
    # ========== DASHBOARD METHODS ==========
    
    def get_all_students_info(self):
        students_info = {}
        with self._students_lock:
            for client_key, student in self._connected_students.items():
                students_info[client_key] = {
                    'name': student.name,
                    'id': student.id,
                    'is_identified': student.is_identified,
                    'cheating_score': student.cheating_score if hasattr(student, 'cheating_score') else 0,
                    'alert_count': len(student.cheating_alerts) if hasattr(student, 'cheating_alerts') else 0,
                    'client_key': client_key,
                    'activity_log': student.activity_log.copy() if hasattr(student, 'activity_log') else []
                }
        return students_info
    
    def get_connected_students(self):
        students = []
        with self._students_lock:
            for client_key, student in self._connected_students.items():
                students.append({
                    'name': student.name,
                    'id': student.id,
                    'is_identified': student.is_identified,
                    'cheating_score': student.cheating_score if hasattr(student, 'cheating_score') else 0,
                    'alert_count': len(student.cheating_alerts) if hasattr(student, 'cheating_alerts') else 0,
                    'client_key': client_key,
                    'activity_log': student.activity_log.copy() if hasattr(student, 'activity_log') else []
                })
        return students
    
    def get_identified_students(self):
        identified = {}
        with self._students_lock:
            for student in self._connected_students.values():
                if student.is_identified:
                    identified[student.id] = student.name
        return identified
    
    def get_student_frames(self):
        frames = []
        with self._students_lock:
            for client_key, student in self._connected_students.items():
                if student.is_identified:
                    frame_data = self._student_frames.get(client_key)
                    if frame_data:
                        try:
                            npbuf = np.frombuffer(frame_data, dtype=np.uint8)
                            frame = cv2.imdecode(npbuf, cv2.IMREAD_COLOR)
                            if frame is not None:
                                frames.append((student.name, student.id, frame.copy()))
                        except Exception as e:
                            print(f"[SERVER] Frame decode error: {e}")
        return frames
    
    def get_all_alerts(self):
        with self._all_alerts_lock:
            return self._all_alerts.copy()
    
    def get_cheating_report(self):
        report = {
            "exam_duration": self._get_exam_duration(),
            "total_alerts": len(self._all_alerts),
            "connected_students": {},
            "historical_students": self._student_history.copy(),
            "all_alerts": self.get_all_alerts()
        }
        
        with self._students_lock:
            for client_key, student in self._connected_students.items():
                if student.is_identified:
                    report["connected_students"][student.id] = {
                        "name": student.name,
                        "alerts": student.cheating_alerts.copy() if hasattr(student, 'cheating_alerts') else [],
                        "activity_log": student.activity_log.copy() if hasattr(student, 'activity_log') else [],
                        "cheating_score": student.cheating_score if hasattr(student, 'cheating_score') else 0,
                        "alert_count": len(student.cheating_alerts) if hasattr(student, 'cheating_alerts') else 0,
                        "status": "connected"
                    }
        
        return report
    
    def _get_exam_duration(self):
        if not self._exam_start_time:
            return "N/A"
        
        duration = int(time.time() - self._exam_start_time)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"