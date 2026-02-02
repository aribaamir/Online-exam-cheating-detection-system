# 🛡️ Online Exam Cheating Detection System

A Python-based client-server application designed to monitor students during online exams and assist proctors in detecting cheating activities in real time.

---

## 📌 Project Overview

The **Online Exam Cheating Detection System** helps maintain exam integrity by monitoring student behavior during online examinations.  
It captures live webcam video, detects suspicious activities such as window switching and copy-paste attempts, and immediately alerts the proctor through a centralized dashboard.

The system follows a **client-server architecture** where:
- **Students** run a client application
- **Proctors** monitor all students via a centralized dashboard

---

## 🎯 Key Features

- Student identity verification using a CSV database  
- Live webcam video streaming  
- Real-time cheating detection:
  - Window switching  
  - Copy / Paste attempts  
  - Alt + Tab usage  
- Instant alerts to the proctor dashboard  
- Activity logs with timestamps  
- Detailed post-exam reports  
- Supports multiple students simultaneously  

---

## 🧩 System Architecture

### Client (Student Side)
- Student authentication  
- Webcam streaming  
- Activity monitoring  
- Sends alerts to the server  

### Server (Proctor Side)
- Handles multiple student connections  
- Receives video streams  
- Processes cheating alerts  
- Updates dashboard in real time  
- Generates reports  

---

## 🛠️ Technologies Used

### Programming Language
- Python 3.x  

### GUI
- PyQt6 (Proctor Dashboard)  
- Tkinter (Student Application)  
- Qt Designer  

### Networking
- Socket  
- Pickle  
- Struct  

### Video Processing
- OpenCV  

### Activity Monitoring
- PyGetWindow  
- Keyboard  

### Concurrency
- Threading  

### Data Structures
- Doubly Linked List  
- Deque  
- CSV  

### Utilities
- NumPy  
- Datetime  
- Time  

---

## ⚙️ How It Works (Step-by-Step)

1. Proctor starts the server  
2. Students launch the student application  
3. Student identity is verified using `students.csv`  
4. Webcam feed starts streaming to the server  
5. Background threads monitor student activity  
6. Suspicious actions trigger instant alerts  
7. Proctor views live feeds and alerts on the dashboard  
8. After exam completion, a report is generated  

---

## 📊 Report Generation

The system generates reports containing:
- Student details  
- Violation type  
- Timestamps  
- Cheating score  
- Activity logs  

These reports help proctors make fair and evidence-based decisions.

---

## ⚠️ Limitations

- No AI or facial recognition  
- No screen or audio recording  
- Desktop-only (no mobile support)  
- Requires a webcam  
- Does not include exam questions or grading  
- Final decision always depends on the proctor  

---

## 🚀 Future Enhancements

- AI-based behavior detection  
- Facial recognition for identity verification  
- Screen recording  
- Web-based version  
- Mobile support  
- Audio monitoring  
- Cloud storage integration  
- Built-in exam and grading system  
