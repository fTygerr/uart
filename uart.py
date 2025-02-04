import tkinter as tk
import serial
import os
from threading import Timer
import time

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

# Command to send display data
def send_display_command(n):
    global error_counter
    command = f"DISPLAY {n}\r"
    print(f"[DEBUG] Sending DISPLAY command: {command.strip()}")

    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(command.encode())
     
        # Read exactly 41 characters (40 display chars + CR)
        response = ser.read(41)
        
        if not response:
            error_counter += 1
            print(f"[WARNING] No response from VMC (Attempt {error_counter}/{MAX_ERRORS})")
            if error_counter >= MAX_ERRORS:
                upper_label.config(text="Timeout Error")
                lower_label.config(text="No VMC Response")
                error_counter = MAX_ERRORS
            return
            
        # Success - reset error counter
        error_counter = 0
        
        # Remove the trailing CR if present
        if response.endswith(b'\r'):
            response = response[:-1]
            
        response_str = response.decode()
        print(f"[DEBUG] Raw display response: '{response_str}'")

        if len(response_str) == 40:
            upper_line = response_str[:20]
            lower_line = response_str[20:]
            upper_label.config(text=upper_line)
            lower_label.config(text=lower_line)
            print(f"[LOG] Display updated: {response_str}")
        # elif: response_str == "NACK":
        #     upper_label.config(text="NACK Received")
        #     lower_label.config(text="Invalid Command")
        #     print("[WARNING] Received NACK. Invalid DISPLAY command parameter.")
        # else:
        #     upper_label.config(text="Error - Invalid")
        #     lower_label.config(text="String Length")
        #     print(f"[WARNING] Invalid response length: {len(response_str)} chars")
            
    except (serial.SerialTimeoutException, Exception) as e:
        error_counter += 1
        print(f"[WARNING] Communication error (Attempt {error_counter}/{MAX_ERRORS}): {e}")
        
        if error_counter >= MAX_ERRORS:
            upper_label.config(text="Error")
            lower_label.config(text="Check Connection")
            error_counter = MAX_ERRORS
            print("[ERROR] Max consecutive errors reached")

# Modify the periodic update to add a small delay after key presses
last_key_press_time = 0  # Add this with other globals

def periodic_display_update():
    send_display_command(0)
    Timer(DISPLAY_UPDATE_INTERVAL, periodic_display_update).start()

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

# Close the application function
def close_application(event):
    root.quit()

# GUI Setup
root = tk.Tk()
root.title("UART Communicator - Keypad Interface")
root.configure(bg="#a30319")  # Match root background with frame
# root.attributes("-fullscreen", True)  # Commented out fullscreen
root.geometry("480x800")  # Set a fixed window size instead
root.bind("<Escape>", close_application)

# Frame for buttons and labels
frame = tk.Frame(root, bg="#a30319", width=480, height=800)  # Full-screen frame
frame.place(relx=0.5, rely=0.5, anchor="center")

# Display area with border
display_frame = tk.Frame(frame, bg="black", highlightbackground="white", highlightthickness=2)
display_frame.grid(row=0, column=0, columnspan=2, pady=(10, 20))

# Add two 20-character lines in the display
upper_label = tk.Label(
    display_frame,
    text=" " * 20,  # Placeholder text
    bg="black",
    fg="white",
    font=("Courier", 16, "bold"),
    anchor="w",
    width=20
)
upper_label.pack(pady=5)

lower_label = tk.Label(
    display_frame,
    text=" " * 20,  # Placeholder text
    bg="black",
    fg="white",
    font=("Courier", 16, "bold"),
    anchor="w",
    width=20
)
lower_label.pack(pady=5)

# Create buttons and labels
buttons = []
# key_labels = []

for i in range(8):  # 8 keys (0-7)
    row = (i // 2) + 2
    col = i % 2

    # Button for each key
    button = tk.Button(
        frame,
        text=KEY_LABELS[i],
        width=10,  # Reduced button width
        height=2,  # Reduced button height
        bg="#a30319",
        fg="#FAAF40",
        activebackground="#a30319",
        activeforeground="#FAAF40",
        highlightbackground="#C1C1C1",
        highlightthickness=2,
        font=("Arial", 14, "bold"),
        command=lambda n=i: send_key_command(n)
    )
    button.grid(row=row * 2, column=col, padx=20, pady=20)
    buttons.append(button)

    # Label below each button
    # label = tk.Label(
    #     frame,
    #     text=f"Key {i}: Waiting",
    #     bg="#01331A",
    #     fg="#FAAF40",
    #     font=("Arial", 10)
    # )
    # label.grid(row=row * 2 + 1, column=col, padx=5, pady=5)
    # key_labels.append(label)

# Add footer text
footer = tk.Label(
    root,
    text="SVA Next Gen Phase II",
    bg="#01331A",
    fg="#FAAF40",
    font=("Arial", 10, "italic")
)
footer.place(relx=0.5, rely=1.0, anchor="s", y=-5)

# Start periodic display updates
print("[LOG] Starting periodic display updates.")
Timer(DISPLAY_UPDATE_INTERVAL, periodic_display_update).start()

print("[LOG] GUI initialized. Ready for interaction.")
root.mainloop()