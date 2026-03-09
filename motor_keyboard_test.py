import keyboard
import time
import math
import matplotlib.pyplot as plt
from collections import deque
import serial

# speed values in output rad/s
slow_speed = 1.5
medium_speed = 3.0
fast_speed = 4.5

# ak40-10 values used for output rad/s -> erpm conversion
reduction_ratio = 10
pole_pairs = 14

# flip these if the direction feels backwards
cw_sign = 1
ccw_sign = -1

# emergency stop flag
estop_active = False

# graph settings
max_points = 300
times = deque(maxlen=max_points)
speeds = deque(maxlen=max_points)
start_time = time.time()

# serial settings
mode = 1
com_port = None
baud_rate = 115200
serial_timeout = 0.1
ser = None


# convert output rad/s to erpm
def rad_s_to_erpm(rad_s):
    output_rpm = rad_s * 60.0 / (2.0 * math.pi)
    motor_rpm = output_rpm * reduction_ratio
    erpm = motor_rpm * pole_pairs
    return int(round(erpm))


# crc16 for cubemars servo uart packet
def crc16_ccitt(data):
    crc = 0
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# signed int32 to 4 bytes
def int32_to_bytes(value):
    return value.to_bytes(4, byteorder="big", signed=True)


# build cubemars servo speed packet
def build_servo_speed_packet(erpm):
    command_id = 0x08
    payload = bytes([command_id]) + int32_to_bytes(erpm)
    data_length = len(payload)

    crc = crc16_ccitt(payload)
    crc_hi = (crc >> 8) & 0xFF
    crc_lo = crc & 0xFF

    packet = bytes([0x02, data_length]) + payload + bytes([crc_hi, crc_lo, 0x03])
    return packet


# ask which mode to run
def choose_mode():
    while True:
        print("")
        print("choose a mode:")
        print("1 = test mode")
        print("2 = serial dry run")
        print("3 = live motor mode")
        choice = input("enter 1, 2, or 3: ").strip()

        if choice in ["1", "2", "3"]:
            return int(choice)
        else:
            print("invalid choice, try again")


# ask for serial settings if needed
def get_serial_settings():
    global com_port, baud_rate

    print("")
    com_port = input("enter the com port for the usb serial adapter (example: COM3): ").strip()

    baud_input = input("enter baud rate or press enter to use 115200: ").strip()
    if baud_input != "":
        try:
            baud_rate = int(baud_input)
        except ValueError:
            print("invalid baud rate, using 115200")
            baud_rate = 115200


# open serial port
def open_motor_port():
    global ser
    try:
        ser = serial.Serial(com_port, baud_rate, timeout=serial_timeout)
        time.sleep(2)
        print(f"opened serial port {com_port} at {baud_rate} baud")
    except Exception as e:
        print(f"could not open serial port: {e}")
        ser = None


# mode 1
def send_speed_command_test(speed):
    erpm = rad_s_to_erpm(speed)
    print(f"test mode -> {speed:.2f} rad/s  |  approx {erpm} erpm")


# mode 2
def send_speed_command_dry_run(speed):
    erpm = rad_s_to_erpm(speed)

    if erpm > 50000:
        erpm = 50000
    elif erpm < -50000:
        erpm = -50000

    packet = build_servo_speed_packet(erpm)
    print(f"dry run -> {speed:.2f} rad/s  |  {erpm} erpm  |  packet: {packet.hex(' ')}")


# mode 3
def send_speed_command_real(speed):
    global ser

    if ser is None:
        print("serial port is not open")
        return

    try:
        erpm = rad_s_to_erpm(speed)

        if erpm > 50000:
            erpm = 50000
        elif erpm < -50000:
            erpm = -50000

        packet = build_servo_speed_packet(erpm)
        ser.write(packet)

        print(f"live motor -> sent {speed:.2f} rad/s  |  {erpm} erpm")

    except Exception as e:
        print(f"serial write failed: {e}")


# wrapper
def send_speed_command(speed):
    if mode == 1:
        send_speed_command_test(speed)
    elif mode == 2:
        send_speed_command_dry_run(speed)
    elif mode == 3:
        send_speed_command_real(speed)


# repeated zero commands for stop
def emergency_stop():
    for _ in range(5):
        send_speed_command(0.0)
        time.sleep(0.02)


# choose mode
mode = choose_mode()

if mode in [2, 3]:
    get_serial_settings()
    open_motor_port()

# graph setup
plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [])
ax.set_title("commanded motor speed")
ax.set_xlabel("time (s)")
ax.set_ylabel("speed (rad/s)")
ax.grid(True)
ax.set_ylim(-fast_speed * 1.2, fast_speed * 1.2)

print("")
print("controls:")
print("hold d = clockwise at medium speed")
print("hold a = counterclockwise at medium speed")
print("hold w + d or a = faster")
print("hold s + d or a = slower")
print("press e = emergency stop")
print("press r = reset emergency stop")
print("press q = quit")

print("")
print("speed setup:")
print(f"slow   = {slow_speed:.2f} rad/s")
print(f"medium = {medium_speed:.2f} rad/s")
print(f"fast   = {fast_speed:.2f} rad/s")

if mode == 1:
    print("running in test mode")
elif mode == 2:
    print("running in serial dry run mode")
elif mode == 3:
    print("running in live motor mode")

last_speed = 0.0

try:
    while True:
        # quit program
        if keyboard.is_pressed('q'):
            emergency_stop()
            print("program ended")
            break

        # emergency stop latch
        if keyboard.is_pressed('e'):
            if not estop_active:
                estop_active = True
                emergency_stop()
                print("emergency stop activated - press r to reset")

        # reset emergency stop
        if keyboard.is_pressed('r'):
            if estop_active:
                estop_active = False
                print("emergency stop cleared")

        # choose target speed
        if estop_active:
            target_speed = 0.0
        else:
            speed_mag = medium_speed

            if keyboard.is_pressed('w'):
                speed_mag = fast_speed
            elif keyboard.is_pressed('s'):
                speed_mag = slow_speed

            if keyboard.is_pressed('d') and not keyboard.is_pressed('a'):
                target_speed = cw_sign * speed_mag
            elif keyboard.is_pressed('a') and not keyboard.is_pressed('d'):
                target_speed = ccw_sign * speed_mag
            else:
                target_speed = 0.0

        # only send when speed changes
        if target_speed != last_speed:
            send_speed_command(target_speed)
            last_speed = target_speed

        # update graph
        current_time = time.time() - start_time
        times.append(current_time)
        speeds.append(target_speed)

        line.set_xdata(times)
        line.set_ydata(speeds)

        if len(times) > 1:
            ax.set_xlim(max(0, times[0]), times[-1] + 0.1)
        else:
            ax.set_xlim(0, 5)

        fig.canvas.draw()
        fig.canvas.flush_events()

        time.sleep(0.03)

except Exception as e:
    print(f"program error: {e}")

finally:
    try:
        keyboard.unhook_all()
    except Exception:
        pass

    try:
        if ser is not None and ser.is_open:
            ser.close()
            print("serial port closed")
    except Exception:
        pass

    try:
        plt.ioff()
        plt.close('all')
    except Exception:
        pass