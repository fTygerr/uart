import serial
import os
from threading import Timer
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
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

# Add this variable at the top with other globals
last_key_press_time = 0

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(80)
        self.setCursor(Qt.PointingHandCursor)
        
        # Animation setup
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(100)
        
        # Shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        self.shadow.setColor(QColor(250, 175, 64, 180))
        rect = self.geometry()
        self._animation.setStartValue(rect)
        self._animation.setEndValue(QRect(rect.x()-2, rect.y()-2, rect.width()+4, rect.height()+4))
        self._animation.start()

    def leaveEvent(self, event):
        self.shadow.setColor(QColor(0, 0, 0, 80))
        rect = self.geometry()
        self._animation.setStartValue(rect)
        self._animation.setEndValue(QRect(rect.x()+2, rect.y()+2, rect.width()-4, rect.height()-4))
        self._animation.start()

class MenuOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set size to match parent (fullscreen)
        self.setGeometry(parent.geometry())
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # Return button
        return_btn = QPushButton("Return to Program")
        return_btn.clicked.connect(self.hide)
        layout.addWidget(return_btn)
        
        # Exit button
        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #662222;
            }
            QPushButton:hover {
                background-color: #883333;
            }
        """)
        exit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(exit_btn)
        
        self.hide()

class UARTInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window flags for true fullscreen without decorations
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        
        # Theme state
        self.is_dark_theme = True
        
        # Create stacked widget for multiple pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create main page
        self.main_page = QWidget()
        self.setup_main_page()
        self.stacked_widget.addWidget(self.main_page)
        
        # Create menu page
        self.menu_page = QWidget()
        self.setup_menu_page()
        self.stacked_widget.addWidget(self.menu_page)
        
        # Apply initial theme
        self.apply_theme()

    def setup_main_page(self):
        # Main page layout
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 10, 20, 20)

        # Set the dark background for main page
        self.main_page.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
            }
            QFrame {
                background-color: #1e1e1e;
                border: 2px solid #3a3a3a;
                border-radius: 15px;
                padding: 15px;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
        """)

        # Display frame with menu button
        display_frame = QFrame()
        display_frame.setObjectName("displayFrame")  # Add object name for styling
        display_layout = QVBoxLayout(display_frame)
        
        # Header container for menu button
        header_container = QWidget()
        header_container.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Menu button
        menu_button = QPushButton("⋮")
        menu_button.setFixedSize(30, 30)
        menu_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                border-radius: 15px;
                font-size: 24px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """)
        menu_button.clicked.connect(self.show_menu)
        
        header_layout.addStretch()
        header_layout.addWidget(menu_button)
        display_layout.addWidget(header_container)
        
        # Display labels
        self.upper_label = QLabel(" " * 20)
        self.lower_label = QLabel(" " * 20)
        self.upper_label.setAlignment(Qt.AlignCenter)
        self.lower_label.setAlignment(Qt.AlignCenter)
        display_layout.addWidget(self.upper_label)
        display_layout.addWidget(self.lower_label)
        main_layout.addWidget(display_frame)

        # Button grid in a card-like container
        button_container = QFrame()
        button_container.setObjectName("buttonContainer")  # Add object name for styling
        button_layout = QGridLayout(button_container)
        button_layout.setSpacing(15)
        
        self.buttons = []
        for i in range(8):
            row = (i // 2)
            col = i % 2
            button = ModernButton(KEY_LABELS[i])
            button.clicked.connect(lambda checked, n=i: send_key_command(n))
            button_layout.addWidget(button, row, col)
            self.buttons.append(button)

        main_layout.addWidget(button_container)

        # Add stretch to push content up
        main_layout.addStretch(1)

        # Footer with version info
        footer = QLabel("SVA Next Gen Phase II")
        footer.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                font-style: italic;
                margin-bottom: 20px;
            }
        """)
        footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer)

        # Setup periodic display updates
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(lambda: send_display_command(0))
        self.display_timer.start(int(DISPLAY_UPDATE_INTERVAL * 1000))

    def setup_menu_page(self):
        self.menu_page.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
        """)
        
        # Menu page layout
        menu_layout = QVBoxLayout(self.menu_page)
        menu_layout.setAlignment(Qt.AlignCenter)
        menu_layout.setSpacing(20)
        
        # Theme toggle button
        self.theme_btn = QPushButton("Switch to Light Theme" if self.is_dark_theme else "Switch to Dark Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        menu_layout.addWidget(self.theme_btn)
        
        # Return button
        return_btn = QPushButton("Return to Program")
        return_btn.clicked.connect(self.show_main)
        menu_layout.addWidget(return_btn)
        
        # Exit button
        exit_btn = QPushButton("Exit")
        exit_btn.setObjectName("exitButton")  # Add object name for styling
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #662222;
                color: #ffffff !important;  /* Force white text always */
            }
            QPushButton:hover {
                background-color: #883333;
            }
        """)
        exit_btn.clicked.connect(QApplication.instance().quit)
        menu_layout.addWidget(exit_btn)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.theme_btn.setText("Switch to Light Theme" if self.is_dark_theme else "Switch to Dark Theme")
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_theme:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        # Main page dark theme
        self.main_page.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
            }
            QFrame {
                background-color: #1e1e1e;
                border: 2px solid #3a3a3a;
                border-radius: 15px;
                padding: 15px;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
            }
            
            /* Display frame specific styles */
            QFrame#displayFrame QLabel {
                color: #00ff00;
                font-family: 'Courier';
                font-size: 18px;
                font-weight: bold;
            }
        """)
        
        # Menu page dark theme
        self.menu_page.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
            QPushButton#exitButton {
                background-color: #662222;
            }
            QPushButton#exitButton:hover {
                background-color: #883333;
            }
        """)

    def apply_light_theme(self):
        # Main page light theme
        self.main_page.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f0f0, stop:1 #e0e0e0);
            }
            QFrame {
                background-color: #ffffff;
                border: 2px solid #dddddd;
                border-radius: 15px;
                padding: 15px;
            }
            QPushButton {
                background-color: #f8f8f8;
                color: #333333;
                border: none;
                border-radius: 15px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
            QLabel {
                color: #333333;
            }
            
            /* Display frame specific styles */
            QFrame#displayFrame {
                background-color: #ffffff;
            }
            QFrame#displayFrame QLabel {
                color: #0066cc;
                font-family: 'Courier';
                font-size: 18px;
                font-weight: bold;
            }
            
            /* Button container specific styles */
            QFrame#buttonContainer {
                background-color: #f5f5f5;
            }
        """)
        
        # Menu page light theme
        self.menu_page.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: none;
                border-radius: 15px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
            }
            QPushButton#exitButton {
                background-color: #662222;
                color: #ffffff;
            }
            QPushButton#exitButton:hover {
                background-color: #883333;
            }
        """)

    def show_menu(self):
        self.stacked_widget.setCurrentIndex(1)  # Show menu page

    def show_main(self):
        self.stacked_widget.setCurrentIndex(0)  # Show main page

    def closeEvent(self, event):
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
        response = ser.read(41)  # Read exactly 41 characters (40 display chars + CR)
        
        if not response:
            error_counter += 1
            print(f"[WARNING] No response from VMC (Attempt {error_counter}/{MAX_ERRORS})")
            if error_counter >= MAX_ERRORS:
                window.upper_label.setText("Timeout Error")
                window.lower_label.setText("No VMC Response")
                error_counter = MAX_ERRORS
            return
            
        error_counter = 0  # Success - reset error counter
        
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
        print(f"[DEBUG] Raw key response: '{response}'")

        if response:
            print(f"[LOG] Received response: {response}")
        else:
            print("[WARNING] No response received from hardware.")
            
        last_key_press_time = time.time()
        
    except Exception as e:
        print(f"[ERROR] Failed to send command: {e}")

if __name__ == "__main__":
    # Initialize Qt application
    app = QApplication(sys.argv)
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Create main window
    window = UARTInterface()
    window.show()
    
    # Start Qt event loop
    sys.exit(app.exec_())