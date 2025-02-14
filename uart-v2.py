import serial
import os
from threading import Timer
import time
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sys

# Suppress tkinter deprecation warning
os.environ["TK_SILENCE_DEPRECATION"] = "1"

# Setup serial communication
try:
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1.0  # Increased to 1 second
    )
    print("[LOG] Using hardware UART at /dev/serial0.")
except serial.serialutil.SerialException as e:
    print(f"[ERROR] Failed to initialize UART: {e}")
    exit(1)

# Key configuration
KEY_PRESS_DURATION = "1000"  # Default milliseconds duration for key closure
KEY_LABELS = [
    "Key 0", "Key 1", "Key 2", "Key 3",
    "Key 4", "Key 5", "Key 6", "Key 7"
]

# Timer configuration
DISPLAY_UPDATE_INTERVAL = 0.75

# Add at top with other constants
MAX_ERRORS = 3  # Maximum consecutive errors before showing error message
error_counter = 0  # Global counter for consecutive errors

class UARTInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UART Communicator - Keypad Interface")
        self.setFixedSize(480, 800)
        
        # Apply global stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #01331A;
            }
            QPushButton {
                background-color: #01331A;
                color: #FAAF40;
                border: 2px solid #C1C1C1;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                min-height: 60px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #024827;
                border-color: #FAAF40;
            }
            QPushButton:pressed {
                background-color: #036d3a;
            }
        """)

        # Central widget setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Display frame
        display_frame = QFrame()
        display_frame.setStyleSheet("""
            QFrame {
                background-color: black;
                border: 2px solid white;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-family: 'Courier';
                font-size: 16px;
                font-weight: bold;
            }
        """)
        display_layout = QVBoxLayout(display_frame)
        
        self.upper_label = QLabel(" " * 20)
        self.lower_label = QLabel(" " * 20)
        display_layout.addWidget(self.upper_label)
        display_layout.addWidget(self.lower_label)
        main_layout.addWidget(display_frame)

        # Button grid
        button_grid = QGridLayout()
        button_grid.setSpacing(20)
        self.buttons = []
        
        for i in range(8):
            row = (i // 2)
            col = i % 2
            button = QPushButton(KEY_LABELS[i])
            
            # Add hover animation effect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setColor(QColor("#FAAF40"))
            shadow.setOffset(0, 0)
            button.setGraphicsEffect(shadow)
            
            button.clicked.connect(lambda checked, n=i: send_key_command(n))
            button_grid.addWidget(button, row, col)
            self.buttons.append(button)

        main_layout.addLayout(button_grid)

        # Footer
        footer = QLabel("SVA Next Gen Phase II")
        footer.setStyleSheet("""
            QLabel {
                color: #FAAF40;
                font-size: 10px;
                font-style: italic;
            }
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer)

        # Setup periodic display updates using Qt Timer
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(lambda: send_display_command(0))
        self.display_timer.start(int(DISPLAY_UPDATE_INTERVAL * 1000))

    def closeEvent(self, event):
        # Cleanup when closing the application
        self.display_timer.stop()
        event.accept()

# Modify your display update function to work with Qt labels
def send_display_command(n):
    global error_counter
    command = f"DISPLAY {n}\r"
    print(f"[DEBUG] Sending DISPLAY command: {command.strip()}")

    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(command.encode())
        response = ser.read(41)
        
        if not response:
            error_counter += 1
            print(f"[WARNING] No response from VMC (Attempt {error_counter}/{MAX_ERRORS})")
            if error_counter >= MAX_ERRORS:
                window.upper_label.setText("Timeout Error")
                window.lower_label.setText("No VMC Response")
                error_counter = MAX_ERRORS
            return
            
        error_counter = 0
        
        if response.endswith(b'\r'):
            response = response[:-1]
            
        response_str = response.decode()
        print(f"[DEBUG] Raw display response: '{response_str}'")

        if len(response_str) == 40:
            upper_line = response_str[:20]
            lower_line = response_str[20:]
            window.upper_label.setText(upper_line)
            window.lower_label.setText(lower_line)
            print(f"[LOG] Display updated: {response_str}")
            
    except (serial.SerialTimeoutException, Exception) as e:
        error_counter += 1
        print(f"[WARNING] Communication error (Attempt {error_counter}/{MAX_ERRORS}): {e}")
        
        if error_counter >= MAX_ERRORS:
            window.upper_label.setText("Error")
            window.lower_label.setText("Check Connection")
            error_counter = MAX_ERRORS
            print("[ERROR] Max consecutive errors reached")

# Command execution function
def send_key_command(key_number):
    global last_key_press_time
    command = f"KEY {key_number} {KEY_PRESS_DURATION}\r"
    print(f"[DEBUG] Sending command: {command.strip()}")

    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(command.encode())

        response = ser.read_until(b'\r').decode().strip()
        print(f"[DEBUG] Raw key response: '{response}'")  # Debug line

        if response:
            print(f"[LOG] Received response: {response}")
            # if response == "ACK":
            #     key_labels[key_number].config(text=f"Key {key_number}: ACK")
            # elif response == "NACK":
            #     key_labels[key_number].config(text=f"Key {key_number}: NACK")
            # else:
            #     key_labels[key_number].config(text=f"Key {key_number}: UNKNOWN")
        else:
            print("[WARNING] No response received from hardware.")
            # key_labels[key_number].config(text=f"Key {key_number}: No Response")
        last_key_press_time = time.time()  # Update the timestamp after key press
    except Exception as e:
        print(f"[ERROR] Failed to send command: {e}")
        # key_labels[key_number].config(text=f"Key {key_number}: Error")

if __name__ == "__main__":
    # Initialize Qt application
    app = QApplication(sys.argv)
    
    # Create main window
    window = UARTInterface()
    window.show()
    
    # Start Qt event loop
    sys.exit(app.exec())