# dashboard.py 
import sys
import cv2
import traceback
import json
import os
from datetime import datetime
from PyQt6 import QtWidgets, uic, QtGui, QtCore, QtPrintSupport
from server import ProctorServer
from report import ReportWindow

class ProctorDashboard(QtWidgets.QMainWindow):
    def __init__(self, server: ProctorServer):
        super().__init__()
        uic.loadUi("proctor.ui", self)
        
        self.server = server
        
        # Connect server signals
        self.server.signals.new_student_connected.connect(self.on_new_student_connected)
        self.server.signals.student_disconnected.connect(self.on_student_disconnected)
        self.server.signals.cheating_alert.connect(self.on_cheating_alert)
        
        # Connect UI elements
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.setInterval(1000)
        
        self.preview_timer = QtCore.QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.setInterval(33)
        
        # Connect buttons
        self.startbutton.clicked.connect(self.start_server)
        self.endbutton.clicked.connect(self.stop_server)
        self.exambutton.clicked.connect(self.start_exam)
        self.reportbutton.clicked.connect(self.generate_report)
        
        # Disable buttons initially
        self.endbutton.setEnabled(False)
        self.exambutton.setEnabled(False)
        self.reportbutton.setEnabled(False)
        
        # Store student video mappings
        self.student_mappings = {}  # {client_key: video_label_name}
        self.video_label_students = {}  # {video_label_name: client_key} for reverse lookup
        
        # Activity log for cheating alerts
        if hasattr(self, 'list'):
            self.activity_list = self.list
            self.activity_list.setAlternatingRowColors(True)
            self.activity_list.setStyleSheet("""
                QListWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                }
                QListWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #333;
                }
                QListWidget::item:alternate {
                    background-color: #252525;
                }
                QListWidget::item:hover {
                    background-color: #2a2a2a;
                }
            """)
            
            # Add header item
            header_item = QtWidgets.QListWidgetItem("📋 ACTIVITY LOG - Cheating Alerts")
            header_item.setBackground(QtGui.QColor(30, 60, 90))
            header_item.setForeground(QtGui.QColor(255, 255, 255))
            header_item.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Weight.Bold))
            self.activity_list.addItem(header_item)
        
        # FIX: Find existing name labels or create them
        self.name_labels = {}
        
        # Look for existing name labels in the UI
        if hasattr(self, 'name1'):
            self.name_labels['videolabel'] = self.name1
        else:
            # Create name1 label if it doesn't exist
            self.name1 = QtWidgets.QLabel("Student 1: Not Connected")
            self.name1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.name1.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    color: #888;
                    padding: 5px;
                    background-color: #2a2a2a;
                    border-radius: 5px;
                    border: 1px solid #444;
                }
            """)
            self.name_labels['videolabel'] = self.name1
            
            # Try to add to layout if possible
            if hasattr(self, 'student1_video_layout'):
                self.student1_video_layout.addWidget(self.name1)
            elif hasattr(self, 'student1_layout'):
                self.student1_layout.addWidget(self.name1)
            elif hasattr(self, 'layout'):
                self.layout().addWidget(self.name1)
        
        if hasattr(self, 'name2'):
            self.name_labels['videolabel2'] = self.name2
        elif hasattr(self, 'videolabel2'):
            # Create name2 label if there's a second video label
            self.name2 = QtWidgets.QLabel("Student 2: Not Connected")
            self.name2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.name2.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    color: #888;
                    padding: 5px;
                    background-color: #2a2a2a;
                    border-radius: 5px;
                    border: 1px solid #444;
                }
            """)
            self.name_labels['videolabel2'] = self.name2
            
            # Try to add to layout if possible
            if hasattr(self, 'student2_video_layout'):
                self.student2_video_layout.addWidget(self.name2)
            elif hasattr(self, 'student2_layout'):
                self.student2_layout.addWidget(self.name2)
            elif hasattr(self, 'layout'):
                self.layout().addWidget(self.name2)
        
        # Status labels
        self.status_label = QtWidgets.QLabel("Server: Stopped")
        self.connection_label = QtWidgets.QLabel("Connected: 0")
        self.identified_label = QtWidgets.QLabel("Verified: 0")
        self.alerts_label = QtWidgets.QLabel("Alerts: 0")
        
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.connection_label)
        self.statusBar().addPermanentWidget(self.identified_label)
        self.statusBar().addPermanentWidget(self.alerts_label)
        
        # Cheating alerts counter
        self.alert_count = 0
        self.exam_active = False
        
        # Set window title
        self.setWindowTitle("Proctor Dashboard")
    
    def start_server(self):
        """Start the server when proctor clicks Start Session"""
        try:
            self.server.start()
            self.refresh_timer.start()
            self.preview_timer.start()
            
            # Update button states
            self.startbutton.setEnabled(False)
            self.endbutton.setEnabled(True)
            self.exambutton.setEnabled(True)
            
            # Clear mappings
            self.student_mappings.clear()
            self.video_label_students.clear()
            
            # Update status
            self.status_label.setText("Server: Running")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Initial refresh
            self.refresh_dashboard()
            
            # Clear activity log but keep header
            if hasattr(self, 'activity_list'):
                for i in range(self.activity_list.count() - 1, 0, -1):
                    self.activity_list.takeItem(i)
                self.alert_count = 0
                self.alerts_label.setText("Alerts: 0")
            
            QtWidgets.QMessageBox.information(self, "Server Started", 
                "Server is running. Students can now connect for identification.")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Server Error", f"Failed to start server: {str(e)}")
    
    def start_exam(self):
        """Start exam monitoring"""
        try:
            # Start cheating detection server
            self.server.start_cheating_detection()
            self.exam_active = True
            
            # Update UI
            self.exambutton.setEnabled(False)
            self.reportbutton.setEnabled(True)
            
            # Add log entry
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.add_to_activity_log(f"[{timestamp}] ⚡ Exam started. Monitoring active.", "info")
            
            QtWidgets.QMessageBox.information(self, "Exam Started", 
                "Exam monitoring is now active. Cheating detection is enabled.")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Exam Error", f"Failed to start exam: {str(e)}")
    
    def stop_server(self):
        """Stop the server"""
        try:
            self.refresh_timer.stop()
            self.preview_timer.stop()
            self.server.stop()
            
            # Clear videos
            if hasattr(self, 'videolabel'):
                self.videolabel.clear()
                self.videolabel.setText("Server Stopped")
                self.videolabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            # Clear second video if exists
            if hasattr(self, 'videolabel2'):
                self.videolabel2.clear()
                self.videolabel2.setText("Server Stopped")
                self.videolabel2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            # Reset name labels
            for label_name, label in self.name_labels.items():
                if 'videolabel' in label_name:
                    label.setText(f"Student {label_name[-1] if label_name[-1].isdigit() else '1'}: Not Connected")
                    label.setStyleSheet("""
                        QLabel {
                            font-weight: bold;
                            font-size: 14px;
                            color: #888;
                            padding: 5px;
                            background-color: #2a2a2a;
                            border-radius: 5px;
                            border: 1px solid #444;
                        }
                    """)
            
            # Clear mappings
            self.student_mappings.clear()
            self.video_label_students.clear()
            
            # Update button states
            self.startbutton.setEnabled(True)
            self.endbutton.setEnabled(False)
            self.exambutton.setEnabled(False)
            self.reportbutton.setEnabled(False)
            
            # Update status
            self.status_label.setText("Server: Stopped")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connection_label.setText("Connected: 0")
            self.identified_label.setText("Verified: 0")
            
            # Reset exam state
            self.exam_active = False
            
            # Add log entry
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.add_to_activity_log(f"[{timestamp}] ⛔ Server stopped. All connections terminated.", "warning")
            
            QtWidgets.QMessageBox.information(self, "Server Stopped", 
                "Server has been stopped. All connections terminated.")
            
        except Exception as e:
            print(f"[DASHBOARD] Error stopping server: {e}")
    
    def on_new_student_connected(self, student_info):
        """Handle new student connection"""
        print(f"[DASHBOARD] New student connected: {student_info}")
        
        # Assign student to first available slot
        client_key = student_info['client_key']
        if client_key not in self.student_mappings:
            # Find first available video label
            video_labels = []
            if hasattr(self, 'videolabel'):
                video_labels.append('videolabel')
            if hasattr(self, 'videolabel2'):
                video_labels.append('videolabel2')
            
            for video_label in video_labels:
                if video_label not in self.video_label_students:
                    # Assign this student to this video label
                    self.student_mappings[client_key] = video_label
                    self.video_label_students[video_label] = client_key
                    print(f"[DASHBOARD] Assigned {student_info['name']} to {video_label}")
                    break
        
        self.refresh_dashboard()
        
        # Add to activity log
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "✅ VERIFIED" if student_info['is_identified'] else "❌ NOT VERIFIED"
        self.add_to_activity_log(f"[{timestamp}] 👤 {student_info['name']} ({student_info['id']}) connected - {status}", 
                               "success" if student_info['is_identified'] else "error")
    
    def on_student_disconnected(self, student_name):
        """Handle student disconnection - FIXED VERSION"""
        print(f"[DASHBOARD] Student disconnected: {student_name}")
        
        # Find the client_key for this student
        client_key_to_remove = None
        all_students_info = self.server.get_all_students_info()
        
        for client_key, student_info in all_students_info.items():
            if student_info.get('name') == student_name:
                client_key_to_remove = client_key
                break
        
        if client_key_to_remove and client_key_to_remove in self.student_mappings:
            # Free up the video label
            video_label = self.student_mappings[client_key_to_remove]
            
            # Remove from mappings
            del self.student_mappings[client_key_to_remove]
            if video_label in self.video_label_students:
                del self.video_label_students[video_label]
            
            # Clear the video label
            if video_label == 'videolabel' and hasattr(self, 'videolabel'):
                self.show_placeholder(self.videolabel, "👤 Waiting for student...")
                # Update name label
                if 'videolabel' in self.name_labels:
                    self.name_labels['videolabel'].setText("Student 1: Not Connected")
                    self.name_labels['videolabel'].setStyleSheet("""
                        QLabel {
                            font-weight: bold;
                            font-size: 14px;
                            color: #888;
                            padding: 5px;
                            background-color: #2a2a2a;
                            border-radius: 5px;
                            border: 1px solid #444;
                        }
                    """)
            elif video_label == 'videolabel2' and hasattr(self, 'videolabel2'):
                self.show_placeholder(self.videolabel2, "👤 Waiting for student...")
                # Update name label
                if 'videolabel2' in self.name_labels:
                    self.name_labels['videolabel2'].setText("Student 2: Not Connected")
                    self.name_labels['videolabel2'].setStyleSheet("""
                        QLabel {
                            font-weight: bold;
                            font-size: 14px;
                            color: #888;
                            padding: 5px;
                            background-color: #2a2a2a;
                            border-radius: 5px;
                            border: 1px solid #444;
                        }
                    """)
        
        self.refresh_dashboard()
        
        # Add to activity log
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.add_to_activity_log(f"[{timestamp}] 🚪 {student_name} disconnected", "warning")
    
    def on_cheating_alert(self, alert_data):
        """Handle cheating alert from server - FIXED VERSION"""
        try:
            self.alert_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Format the alert message
            student_name = alert_data.get('student_name', 'Unknown')
            violation = alert_data.get('violation', 'Unknown violation')
            severity = alert_data.get('severity', 'low')
            
            print(f"[DASHBOARD] Cheating alert #{self.alert_count} received: {student_name} - {violation} ({severity})")
            
            # Create alert message with emoji based on violation type
            if "chatgpt" in violation.lower() or "openai" in violation.lower() or "ai" in violation.lower():
                icon = "🤖"
            elif "copy" in violation.lower() or "paste" in violation.lower() or "ctrl" in violation.lower():
                icon = "📋"
            elif "window" in violation.lower() or "switch" in violation.lower() or "tab" in violation.lower():
                icon = "🪟"
            elif "stop" in violation.lower() or "ended" in violation.lower():
                icon = "⏹️"
            else:
                icon = "⚠️"
            
            alert_text = f"[{timestamp}] {icon} {student_name}: {violation}"
            
            # IMPORTANT: Add to activity list BEFORE updating UI
            self.add_to_activity_log(alert_text, severity)
            
            # Update alert count - IMPORTANT: Do this AFTER adding to log
            self.alerts_label.setText(f"Alerts: {self.alert_count}")
            
            # Force UI update
            QtWidgets.QApplication.processEvents()
            
            # Show notification popup for high severity alerts
            if severity == 'high':
                QtWidgets.QMessageBox.warning(self, "🚨 HIGH SEVERITY ALERT", 
                    f"Student: {student_name}\n\nViolation: {violation}\n\nSeverity: HIGH\n\nImmediate action recommended!")
            
            # Flash window attention for medium/high alerts
            if severity in ['high', 'medium']:
                self.flash_window()
            
            # Debug: Print confirmation
            print(f"[DASHBOARD] Alert #{self.alert_count} added to activity log: {alert_text}")
                
        except Exception as e:
            print(f"[DASHBOARD] Error handling alert: {e}")
            traceback.print_exc()
    
    def flash_window(self):
        """Flash window to get attention"""
        original_color = self.palette().color(self.backgroundRole())
        flash_color = QtGui.QColor(255, 100, 100)
        
        def restore_color():
            palette = self.palette()
            palette.setColor(self.backgroundRole(), original_color)
            self.setPalette(palette)
        
        # Flash the window
        palette = self.palette()
        palette.setColor(self.backgroundRole(), flash_color)
        self.setPalette(palette)
        
        QtCore.QTimer.singleShot(200, restore_color)
    
    def add_to_activity_log(self, message, alert_type="info"):
        """Add a message to the activity log - FIXED VERSION"""
        if not hasattr(self, 'activity_list'):
            print(f"[DASHBOARD] Warning: No activity_list found!")
            return
        
        try:
            # Create the list item
            item = QtWidgets.QListWidgetItem(message)
            
            # Set color based on alert type
            if alert_type == "high":
                item.setBackground(QtGui.QColor(80, 30, 30))
                item.setForeground(QtGui.QColor(255, 150, 150))
                font = QtGui.QFont()
                font.setBold(True)
                item.setFont(font)
            elif alert_type == "medium":
                item.setBackground(QtGui.QColor(80, 60, 30))
                item.setForeground(QtGui.QColor(255, 200, 100))
                font = QtGui.QFont()
                font.setBold(True)
                item.setFont(font)
            elif alert_type == "success":
                item.setBackground(QtGui.QColor(30, 80, 30))
                item.setForeground(QtGui.QColor(150, 255, 150))
            elif alert_type == "error":
                item.setBackground(QtGui.QColor(80, 30, 30))
                item.setForeground(QtGui.QColor(255, 150, 150))
            elif alert_type == "warning":
                item.setBackground(QtGui.QColor(80, 60, 30))
                item.setForeground(QtGui.QColor(255, 200, 100))
            else:  # info
                item.setBackground(QtGui.QColor(30, 30, 80))
                item.setForeground(QtGui.QColor(150, 150, 255))
            
            # Add to list
            self.activity_list.addItem(item)
            
            # Scroll to bottom
            self.activity_list.scrollToBottom()
            
            # Force UI update
            QtWidgets.QApplication.processEvents()
            
            # Debug output
            print(f"[DASHBOARD] Added to activity log: {message}")
            
            # Keep only last 200 items (increased from 100)
            if self.activity_list.count() > 200:
                # Keep header and remove oldest item
                if self.activity_list.count() > 1:  # Make sure we have items beyond header
                    self.activity_list.takeItem(1)  # Remove item after header
            
        except Exception as e:
            print(f"[DASHBOARD] Error adding to activity log: {e}")
            traceback.print_exc()
    
    def refresh_dashboard(self):
        """Refresh all dashboard elements"""
        try:
            # Update connected students count
            connected_students = self.server.get_connected_students()
            connected_count = len(connected_students)
            self.connection_label.setText(f"Connected: {connected_count}")
            
            # Update verified students count
            identified = self.server.get_identified_students()
            identified_count = len(identified)
            self.identified_label.setText(f"Verified: {identified_count}")
            
            # Update status bar with counts
            self.statusBar().showMessage(f"Students: {connected_count} connected, {identified_count} verified, Alerts: {self.alert_count}")
            
            # Debug output
            # print(f"[DASHBOARD] Refresh: {connected_count} connected, {identified_count} verified")
            
        except Exception as e:
            print(f"[DASHBOARD] Error refreshing: {e}")
    
    def update_preview(self):
        """Update video previews"""
        try:
            # Get frames for all students
            student_frames = self.server.get_student_frames()
            all_students_info = self.server.get_all_students_info()
            
            # Track which students have been displayed
            displayed_students = set()
            
            # Process video label 1
            if hasattr(self, 'videolabel'):
                if 'videolabel' in self.video_label_students:
                    client_key = self.video_label_students['videolabel']
                    student_info = all_students_info.get(client_key)
                    
                    if student_info:
                        # Find this student's frame
                        student_found = False
                        for name, student_id, frame in student_frames:
                            if name == student_info.get('name') and student_id == student_info.get('id'):
                                self.update_video_label(self.videolabel, frame, name, student_id)
                                self._update_name_label('videolabel', student_info)
                                displayed_students.add((name, student_id))
                                student_found = True
                                break
                        
                        if not student_found:
                            self.show_placeholder(self.videolabel, f"📷 No video from {student_info.get('name', 'Student')}")
                else:
                    self.show_placeholder(self.videolabel, "👤 Waiting for student...")
                    if 'videolabel' in self.name_labels:
                        self.name_labels['videolabel'].setText("Student 1: Not Connected")
                        self.name_labels['videolabel'].setStyleSheet("""
                            QLabel {
                                font-weight: bold;
                                font-size: 14px;
                                color: #888;
                                padding: 5px;
                                background-color: #2a2a2a;
                                border-radius: 5px;
                                border: 1px solid #444;
                            }
                        """)
            
            # Process video label 2 if exists
            if hasattr(self, 'videolabel2'):
                if 'videolabel2' in self.video_label_students:
                    client_key = self.video_label_students['videolabel2']
                    student_info = all_students_info.get(client_key)
                    
                    if student_info:
                        # Find this student's frame
                        student_found = False
                        for name, student_id, frame in student_frames:
                            if (name, student_id) not in displayed_students:
                                if name == student_info.get('name') and student_id == student_info.get('id'):
                                    self.update_video_label(self.videolabel2, frame, name, student_id)
                                    self._update_name_label('videolabel2', student_info)
                                    displayed_students.add((name, student_id))
                                    student_found = True
                                    break
                        
                        if not student_found:
                            self.show_placeholder(self.videolabel2, f"📷 No video from {student_info.get('name', 'Student')}")
                else:
                    self.show_placeholder(self.videolabel2, "👤 Waiting for student...")
                    if 'videolabel2' in self.name_labels:
                        self.name_labels['videolabel2'].setText("Student 2: Not Connected")
                        self.name_labels['videolabel2'].setStyleSheet("""
                            QLabel {
                                font-weight: bold;
                                font-size: 14px;
                                color: #888;
                                padding: 5px;
                                background-color: #2a2a2a;
                                border-radius: 5px;
                                border: 1px solid #444;
                            }
                        """)
            
        except Exception as e:
            # Only print error occasionally to avoid spam
            import random
            if random.random() < 0.01:
                print(f"[DASHBOARD] Preview error: {e}")
    
    def _update_name_label(self, label_name, student_info):
        """Update a student name label with info"""
        if label_name not in self.name_labels:
            return
        
        label = self.name_labels[label_name]
        name = student_info.get('name', 'Unknown')
        student_id = student_info.get('id', 'Unknown')
        is_identified = student_info.get('is_identified', False)
        cheating_score = student_info.get('cheating_score', 0)
        
        status = "✅ Verified" if is_identified else "❌ Not Verified"
        score_text = f" | Score: {cheating_score}" if cheating_score > 0 else ""
        
        # Get label number
        if label_name == 'videolabel':
            label_num = "1"
        elif label_name == 'videolabel2':
            label_num = "2"
        else:
            label_num = ""
        
        label.setText(f"👤 {name} ({student_id}) - {status}{score_text}")
        
        # Color based on verification status
        if is_identified:
            label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    color: #4CAF50;
                    padding: 5px;
                    background-color: #1a2a1a;
                    border-radius: 5px;
                    border: 2px solid #4CAF50;
                }
            """)
        else:
            label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    color: #f44336;
                    padding: 5px;
                    background-color: #2a1a1a;
                    border-radius: 5px;
                    border: 2px solid #f44336;
                }
            """)
    
    def update_video_label(self, label, frame, name, student_id):
        """Update a specific video label with frame"""
        if frame is None or frame.size == 0:
            self.show_placeholder(label, f"📷 No video from {name}")
            return
        
        try:
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except:
                rgb = frame
            
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            
            qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
            
            if qimg.isNull():
                self.show_placeholder(label, f"❌ Invalid frame from {name}")
                return
            
            pixmap = QtGui.QPixmap.fromImage(qimg)
            label_size = label.size()
            scaled_pixmap = pixmap.scaled(
                label_size,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            
            label.setPixmap(scaled_pixmap)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
        except Exception as e:
            print(f"[DASHBOARD] Error updating video label: {e}")
            self.show_placeholder(label, f"⚠️ Error: {name}")
    
    def show_placeholder(self, label, message):
        """Show placeholder message in video label"""
        label.setText(message)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                color: #aaaaaa;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #333;
                border-radius: 10px;
                padding: 20px;
            }
        """)
    
    def generate_report(self):
        """Generate cheating report"""
        try:
            report_data = self.server.get_cheating_report()
            
            # Create and show report window
            report_window = ReportWindow(report_data, self)
            report_window.exec()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Report Error", f"Failed to generate report: {str(e)}")
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            self.stop_server()
        except Exception:
            pass
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    try:
        server = ProctorServer(csv_path="students.csv")
        window = ProctorDashboard(server)
        window.setWindowTitle("👨‍🏫 Proctor Dashboard")
        window.resize(800, 600)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        QtWidgets.QMessageBox.critical(None, "❌ Fatal Error", 
            f"Failed to start application:\n\n{str(e)}")
        print(f"Error: {e}")
        traceback.print_exc()