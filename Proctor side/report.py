# report.py
import sys
from datetime import datetime
from PyQt6 import QtWidgets, QtGui, QtCore

class ReportWindow(QtWidgets.QDialog):
    """Window to display student activity report"""
    def __init__(self, report_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Student Activity Report")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Title
        title = QtWidgets.QLabel("📊 STUDENT ACTIVITY REPORT")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                padding: 12px;
                color: #4CAF50;
                background-color: #1a1a1a;
                border-radius: 8px;
                border: 2px solid #4CAF50;
            }
        """)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Report content
        self.report_text = QtWidgets.QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        layout.addWidget(self.report_text)
        
        # Buttons - Only Save and Close
        button_layout = QtWidgets.QHBoxLayout()
        
        save_button = QtWidgets.QPushButton("💾 Save Report")
        save_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 10px 20px;
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        save_button.clicked.connect(self.save_report)
        
        close_button = QtWidgets.QPushButton("❌ Close")
        close_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 10px 20px;
                background-color: #f44336;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        close_button.clicked.connect(self.close)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.report_data = report_data
        
        # Display report
        self.display_report()
    
    # ========== MERGE SORT ALGORITHM ==========
    
    def merge_sort_students_by_name(self, student_items):
        """Merge Sort algorithm to sort students by name (A-Z)"""
        if len(student_items) <= 1:
            return student_items
        
        # Split the list into two halves
        mid = len(student_items) // 2
        left_half = student_items[:mid]
        right_half = student_items[mid:]
        
        # Recursively sort both halves
        left_sorted = self.merge_sort_students_by_name(left_half)
        right_sorted = self.merge_sort_students_by_name(right_half)
        
        # Merge the sorted halves
        return self._merge_by_name(left_sorted, right_sorted)
    
    def _merge_by_name(self, left, right):
        """Merge helper function for merge sort"""
        merged = []
        i = j = 0
        
        # Compare and merge
        while i < len(left) and j < len(right):
            left_name = left[i][1].get('name', '').lower()
            right_name = right[j][1].get('name', '').lower()
            
            if left_name <= right_name:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        
        # Add remaining elements
        merged.extend(left[i:])
        merged.extend(right[j:])
        
        return merged
    
    def get_all_students_sorted(self):
        """Get all students sorted by name using merge sort"""
        if not self.report_data:
            return []
        
        # Combine connected and historical students
        all_students = []
        
        # Add connected students
        connected_items = list(self.report_data.get('connected_students', {}).items())
        all_students.extend(connected_items)
        
        # Add historical (disconnected) students
        historical_items = list(self.report_data.get('historical_students', {}).items())
        all_students.extend(historical_items)
        
        # Sort using merge sort
        return self.merge_sort_students_by_name(all_students)
    
    # ========== REPORT DISPLAY ==========
    
    def display_report(self):
        """Display the sorted report"""
        sorted_students = self.get_all_students_sorted()
        report_text = self.format_report(sorted_students)
        self.report_text.setPlainText(report_text)
    
    def format_report(self, sorted_students):
        """Format report with student names and activities"""
        if not sorted_students:
            return "No student data available.\n\nNo activities were recorded during the exam session."
        
        text = "=" * 60 + "\n"
        text += "STUDENT ACTIVITY REPORT\n"
        text += "=" * 60 + "\n\n"
        
        # Report info
        text += f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if self.report_data:
            exam_duration = self.report_data.get('exam_duration', 'N/A')
            text += f"Exam Duration: {exam_duration}\n"
        
        text += f"Total Students: {len(sorted_students)}\n\n"
        
        # Display each student with their activities
        for student_id, student_data in sorted_students:
            text += self._format_student_section(student_id, student_data)
        
        text += "\n" + "=" * 60 + "\n"
        text += "END OF REPORT\n"
        text += "=" * 60 + "\n"
        
        return text
    
    def _format_student_section(self, student_id, student_data):
        """Format individual student section"""
        name = student_data.get('name', 'Unknown Student')
        cheating_score = student_data.get('cheating_score', 0)
        alerts = student_data.get('alerts', [])
        
        text = f"👤 {name} (ID: {student_id})\n"
        text += f"Cheating Score: {cheating_score}/100\n"
        text += f"Violations: {len(alerts)}\n\n"
        
        # Show all alerts/activities
        if alerts:
            for alert in alerts:
                timestamp = alert.get('timestamp', 'N/A')
                violation = alert.get('violation', 'Unknown')
                
                # Simple formatting
                text += f"  • [{timestamp}] {violation}\n"
        else:
            text += "  ✅ No violations detected\n"
        
        text += "\n" + "-" * 40 + "\n\n"
        
        return text
    
    def save_report(self):
        """Save report to file"""
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "💾 Save Report", "student_activity_report.txt", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.report_text.toPlainText())
                QtWidgets.QMessageBox.information(self, "✅ Success", 
                    f"Report saved successfully to:\n{file_name}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "❌ Error", 
                    f"Failed to save report:\n{str(e)}")