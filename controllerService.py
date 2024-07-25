import socket
import vgamepad as vg
import signal
import sys

gamepad = vg.VX360Gamepad()

# Function to process joystick commands
def process_joystick_commands(commands, gamepad, is_left):
    for command in commands:
        coords = command.split(' ')[0]  # Take only the first part for joystick coordinates
        x, y = map(float, coords.split(','))
        if is_left:
            gamepad.left_joystick_float(x, y)
            print(f"Set left joystick: (x={x}, y={y})")
        else:
            gamepad.right_joystick_float(x, y)
            print(f"Set right joystick: (x={x}, y={y})")
        gamepad.update()

def process_button_command(button_command, gamepad):
    command_mapping = {
        'aBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        'bBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        'xBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        'yBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
        'lbBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
        'rbBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
        'lsBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
        'rsBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        'upDir ': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
        'downDir ': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
        'leftDir ': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
        'rightDir ': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        'startBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
        'backBtn ': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK
    }

    if button_command.startswith("button,"):
        button_name = button_command.split(",")[1]
        button_id = command_mapping.get(button_name)
        if button_name == "rtBtn ":
            gamepad.right_trigger(value=255)
            print("trigger 255")
        if button_name == "ltBtn ":
            gamepad.left_trigger(value=255)
            print("trigger 255")
        if button_id is not None:
            gamepad.press_button(button=button_id)
            print(f"Pressed button: {button_name}")
        else:
            print(f"Button {button_name} not found in command mapping.")
    elif button_command.startswith("release,"):
        button_name = button_command.split(",")[1]
        button_id = command_mapping.get(button_name)
        if button_name == "rtBtn ":
            gamepad.right_trigger(value=0)
            print("trigger 0")
        if button_name == "ltBtn ":
            gamepad.left_trigger(value=0)
            print("trigger 0")

        if button_id is not None:
            gamepad.release_button(button=button_id)
            print(f"Released button: {button_name}")
        else:
            print(f"Button {button_name} not found in command mapping.")
    gamepad.update()

def process_command(data, gamepad):
    if 'LeftJOY:' in data or 'RightJOY:' in data:
        left_commands = data.split('LeftJOY:')
        right_commands = data.split('RightJOY:')
        process_joystick_commands(left_commands[1:], gamepad, is_left=True)
        process_joystick_commands(right_commands[1:], gamepad, is_left=False)
    else:
        process_button_command(data, gamepad)

def signal_handler(sig, frame):
    print('Shutting down server...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

HOST = '0.0.0.0'
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print("Waiting for connections...")

    while True:
        conn, addr = server_socket.accept()
        print(f"Connected to: {addr}")
        with conn:
            try:
                while True:
                    data = conn.recv(1024).decode()
                    if not data:
                        break
                    print(f"Received: {data}")
                    process_command(data, gamepad)
                    gamepad.update()
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Waiting for next connection...")