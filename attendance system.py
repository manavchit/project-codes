attendance system

import face_recognition
import cv2
import paho.mqtt.client as mqtt
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import simpledialog
from typing import List, Dict, Optional
from pathlib import Path
from datetime import date
from picamera2 import Picamera2
import time
from database_manager import DatabaseManager

class FaceDatabase:
    def _init_(self, images_dir: str = "faces"):
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(exist_ok=True)
        self.known_face_encodings: List[np.ndarray] = []
        self.known_face_names: List[str] = []
        self.load_known_faces()

    def load_known_faces(self) -> None:
        for image_path in self.images_dir.glob("*.png"):
            try:
                name = image_path.stem
                face_image = face_recognition.load_image_file(str(image_path))
                face_encodings = face_recognition.face_encodings(face_image)

                if face_encodings:
                    self.known_face_encodings.append(face_encodings[0])
                    self.known_face_names.append(name)
                else:
                    print(f"No face found in {image_path}")
            except Exception as e:
                print(f"Error loading {image_path}: {e}")

    def add_face(self, name: str, image: np.ndarray) -> bool:
        try:
            image_path = self.images_dir / f"{name}.png"
            cv2.imwrite(str(image_path), image)

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_image)

            if not face_encodings:
                raise ValueError("No face detected in image")

            self.known_face_encodings.append(face_encodings[0])
            self.known_face_names.append(name)
            return True
        except Exception as e:
            print(f"Error adding face: {e}")
            return False

class AttendanceSystem:
    def _init_(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Attendance System")
        self.root.geometry("500x400")

        # Initialize face database and database manager
        self.face_db = FaceDatabase()
        self.db_manager = DatabaseManager()

        # Initialize MQTT client
        self.mqtt_broker = "broker.hivemq.com"
        self.mqtt_port = 1883
        self.mqtt_topic = "Manav/Attendance"
        self.mqtt_client = mqtt.Client()

        # Connect to the MQTT broker
        self.connect_mqtt()

        self.lecture_name: str = ""
        self.camera_active: bool = False
        self.process_this_frame: bool = True
        self.marked_faces: set = set()

        self.picam2 = Picamera2()  # Initialize the camera here

        self.setup_gui()

    def connect_mqtt(self):
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()  # Start MQTT network loop
            print("Connected to MQTT broker")
        except Exception as e:
            print(f"Could not connect to MQTT broker: {e}")

    def publish_message(self, message: str):
        try:
            self.mqtt_client.publish(self.mqtt_topic, message)
            print(f"Published message: {message}")
        except Exception as e:
            print(f"Error publishing message: {e}")

    def setup_gui(self) -> None:
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        title_label = ttk.Label(main_frame, text="Smart Attendance System",
                              font=("Helvetica", 16))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Label(main_frame, text="Enter Lecture Name:").grid(row=1, column=0)
        self.lecture_entry = ttk.Entry(main_frame)
        self.lecture_entry.grid(row=1, column=1, padx=5, pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="Start Attendance",
                                  command=self.start_attendance)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.scan_btn = ttk.Button(btn_frame, text="Scan Face",
                                 command=self.scan_face, state=tk.DISABLED)
        self.scan_btn.grid(row=0, column=1, padx=5)

        self.capture_btn = ttk.Button(btn_frame, text="Add New Face",
                                    command=self.capture_new_face)
        self.capture_btn.grid(row=0, column=2, padx=5)

        self.status_label = ttk.Label(main_frame, text="Status: Ready",
                                    font=("Helvetica", 10))
        self.status_label.grid(row=3, column=0, columnspan=2, pady=10)

    def start_attendance(self) -> None:
        self.lecture_name = self.lecture_entry.get().strip()

        if not self.lecture_name:
            messagebox.showerror("Error", "Please enter a valid lecture name")
            return

        self.marked_faces.clear()
        self.status_label.config(text=f"Taking attendance for: {self.lecture_name}")
        self.scan_btn.config(state=tk.NORMAL)

    def scan_face(self) -> None:
        if self.camera_active:
            return

        self.camera_active = True
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
        self.picam2.start()

        # Allow camera to warm up
        time.sleep(2)

        try:
            while self.camera_active:
                frame = self.picam2.capture_array()

                # Resize the frame to speed up processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                if self.process_this_frame:
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    if face_locations:
                        face_encodings = face_recognition.face_encodings(
                            rgb_small_frame, face_locations)

                        for face_encoding in face_encodings:
                            matches = face_recognition.compare_faces(
                                self.face_db.known_face_encodings, face_encoding)

                            if not matches:
                                continue

                            face_distances = face_recognition.face_distance(
                                self.face_db.known_face_encodings, face_encoding)
                            best_match_index = np.argmin(face_distances)

                            if matches[best_match_index]:
                                name = self.face_db.known_face_names[best_match_index]
                                self.mark_attendance(name)

                self.process_this_frame = not self.process_this_frame

                cv2.imshow('Video', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            messagebox.showerror("Error", f"Camera error: {str(e)}")
        finally:
            self.picam2.stop()
            cv2.destroyAllWindows()
            self.camera_active = False

    def capture_new_face(self) -> None:
        name = simpledialog.askstring("Input", "Enter person's name:")
        if not name:
            return

        try:
            self.picam2.configure(self.picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
            self.picam2.start()

            # Allow camera to warm up
            time.sleep(2)

            while True:
                frame = self.picam2.capture_array()
                cv2.imshow('Capture (Press SPACE to take photo)', frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord(' '):  # Space key
                    if self.face_db.add_face(name, frame):
                        messagebox.showinfo("Success", f"Added {name} to database")
                    else:
                        messagebox.showerror("Error", "Failed to add face")
                    break
                elif key == ord('q'):  # Q key
                    break

        except RuntimeError as e:
            messagebox.showerror("Error", f"Camera error: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        finally:
            self.picam2.stop()
            cv2.destroyAllWindows()

    def mark_attendance(self, name: str) -> None:
        try:
            if name not in self.marked_faces:
                today = date.today().isoformat()
                if self.db_manager.mark_attendance(name, self.lecture_name, today):
                    self.marked_faces.add(name)
                    self.status_label.config(text=f"Marked {name} as present")

                    # Publish attendance update to MQTT
                    self.publish_message(f"{name} marked present for {self.lecture_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark attendance: {str(e)}")

    def on_closing(self) -> None:
        self.camera_active = False
        self.picam2.stop()  # Ensure the camera is stopped when closing the app
        self.mqtt_client.loop_stop()  # Stop MQTT loop
        self.root.destroy()

if _name_ == "_main_":
    root = tk.Tk()
    app = AttendanceSystem(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
