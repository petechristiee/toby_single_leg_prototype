"""
pre-run checklist

1. install required packages:
   py -m pip install keyboard matplotlib pyserial python-can

2. for modes 1-3 (servo uart):
   - connect power correctly
   - connect jst gh uart cable to motor uart port
   - connect usb serial adapter to pc
   - know the correct com port
   - make sure the motor is in the expected servo-uart workflow

3. for modes 4-5 (mit can):
   - use a usb-to-can adapter, not just a usb serial adapter
   - know the correct can interface / channel / bitrate
   - know the motor can id
   - start with very small commands only

4. safe testing order:
   - mode 1 first
   - mode 2 second
   - mode 3 third
   - mode 5 fourth
   - mode 4 last

5. live test safety:
   - secure the motor
   - keep it unloaded at first
   - be ready to cut power
   - use e for emergency stop
   - use q to quit

important note:
- mode 3 is for servo uart
- mode 4 is for mit can live control
- mode 5 is for mit can dry run only
- mit can packing may need adjustment depending on the exact cubemars firmware/protocol generation
"""

import keyboard
import time
import math
import matplotlib.pyplot as plt
from collections import deque
import serial
import can

# -----------------------------
# speed values in output rad/s
# -----------------------------
slow_speed = 1.5
medium_speed = 3.0
fast_speed = 4.5

# -----------------------------
# ak40-10 conversion values for output rad/s -> erpm
# -----------------------------
reduction_ratio = 10
pole_pairs = 14

# -----------------------------
# flip these if direction feels backwards
# -----------------------------
cw_sign = 1
ccw_sign = -1

# -----------------------------
# emergency stop flag
# -----------------------------
estop_active = False

# -----------------------------
# graph settings
# -----------------------------
max_points = 300
times = deque(maxlen=max_points)
speeds = deque(maxlen=max_points)
start_time = time.time()

# -----------------------------
# serial settings for servo uart modes
# -----------------------------
mode = 1
com_port = None
baud_rate = 115200
serial_timeout = 0.1
ser = None

# -----------------------------
# can settings for mit mode
# these are example defaults only
# -----------------------------
can_interface = "pcan"
can_channel = "PCAN_USBBUS1"
can_bitrate = 1000000
can_bus = None
motor_can_id = 1

# -----------------------------
# mit mode defaults
# these are conservative placeholders
# -----------------------------
mit_kp_default = 0.0
mit_kd_default = 1.0
mit_torque_ff_default = 0.0

# legacy-style mit packing ranges
# these may need adjustment for your exact motor/firmware
P_MIN = -12.5
P_MAX = 12.5
V_MIN = -50.0
V_MAX = 50.0
KP_MIN = 0.0
KP_MAX = 500.0
KD_MIN = 0.0
KD_MAX = 5.0
T_MIN = -18.0
T_MAX = 18.0


# -----------------------------
# convert output rad/s to erpm
# -----------------------------
def rad_s_to_erpm(rad_s):
    output_rpm = rad_s * 60.0 / (2.0 * math.pi)
    motor_rpm = output_rpm * reduction_ratio
    erpm = motor_rpm * pole_pairs
    return int(round(erpm))


# -----------------------------
# crc16 for cubemars servo uart packet
# -----------------------------
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


# -----------------------------
# signed int32 to 4 bytes
# -----------------------------
def int32_to_bytes(value):
    return value.to_bytes(4, byteorder="big", signed=True)


# -----------------------------
# build cubemars servo speed packet
# -----------------------------
def build_servo_speed_packet(erpm):
    command_id = 0x08
    payload = bytes([command_id]) + int32_to_bytes(erpm)
    data_length = len(payload)

    crc = crc16_ccitt(payload)
    crc_hi = (crc >> 8) & 0xFF
    crc_lo = crc & 0xFF

    packet = bytes([0x02, data_length]) + payload + bytes([crc_hi, crc_lo, 0x03])
    return packet


# -----------------------------
# mit helpers
# -----------------------------
def float_to_uint(x, x_min, x_max, bits):
    span = x_max - x_min
    if span <= 0:
        raise ValueError("invalid range")
    x = max(min(x, x_max), x_min)
    return int((x - x_min) * ((1 << bits) - 1) / span)


def uint_to_float(x_int, x_min, x_max, bits):
    span = x_max - x_min
    return float(x_int) * span / ((1 << bits) - 1) + x_min


# -----------------------------
# build legacy-style mit can packet
# this may need adjustment for exact firmware generation
# -----------------------------
def build_mit_can_packet_legacy(p_des, v_des, kp, kd, t_ff):
    p_int = float_to_uint(p_des, P_MIN, P_MAX, 16)
    v_int = float_to_uint(v_des, V_MIN, V_MAX, 12)
    kp_int = float_to_uint(kp, KP_MIN, KP_MAX, 12)
    kd_int = float_to_uint(kd, KD_MIN, KD_MAX, 12)
    t_int = float_to_uint(t_ff, T_MIN, T_MAX, 12)

    data = [0] * 8
    data[0] = (p_int >> 8) & 0xFF
    data[1] = p_int & 0xFF
    data[2] = (v_int >> 4) & 0xFF
    data[3] = ((v_int & 0xF) << 4) | ((kp_int >> 8) & 0xF)
    data[4] = kp_int & 0xFF
    data[5] = (kd_int >> 4) & 0xFF
    data[6] = ((kd_int & 0xF) << 4) | ((t_int >> 8) & 0xF)
    data[7] = t_int & 0xFF

    return data


# -----------------------------
# ask which mode to run
# -----------------------------
def choose_mode():
    while True:
        print("")
        print("choose a mode:")
        print("1 = test mode")
        print("2 = serial dry run (servo uart)")
        print("3 = live motor mode (servo uart)")
        print("4 = mit mode (can)")
        print("5 = mit can dry run")
        choice = input("enter 1, 2, 3, 4, or 5: ").strip()

        if choice in ["1", "2", "3", "4", "5"]:
            return int(choice)
        else:
            print("invalid choice, try again")


# -----------------------------
# ask for serial settings if needed
# -----------------------------
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


# -----------------------------
# ask for can settings if needed
# -----------------------------
def get_can_settings():
    global can_interface, can_channel, can_bitrate, motor_can_id
    global mit_kp_default, mit_kd_default, mit_torque_ff_default

    print("")
    can_interface = input("enter can interface (example: pcan): ").strip() or "pcan"
    can_channel = input("enter can channel (example: PCAN_USBBUS1): ").strip() or "PCAN_USBBUS1"

    bitrate_input = input("enter can bitrate or press enter to use 1000000: ").strip()
    if bitrate_input != "":
        try:
            can_bitrate = int(bitrate_input)
        except ValueError:
            print("invalid bitrate, using 1000000")
            can_bitrate = 1000000

    can_id_input = input("enter motor can id or press enter to use 1: ").strip()
    if can_id_input != "":
        try:
            motor_can_id = int(can_id_input)
        except ValueError:
            print("invalid motor can id, using 1")
            motor_can_id = 1

    kp_input = input("enter default mit kp or press enter to use 0.0: ").strip()
    if kp_input != "":
        try:
            mit_kp_default = float(kp_input)
        except ValueError:
            print("invalid kp, using 0.0")
            mit_kp_default = 0.0

    kd_input = input("enter default mit kd or press enter to use 1.0: ").strip()
    if kd_input != "":
        try:
            mit_kd_default = float(kd_input)
        except ValueError:
            print("invalid kd, using 1.0")
            mit_kd_default = 1.0

    torque_input = input("enter default mit torque feedforward or press enter to use 0.0: ").strip()
    if torque_input != "":
        try:
            mit_torque_ff_default = float(torque_input)
        except ValueError:
            print("invalid torque ff, using 0.0")
            mit_torque_ff_default = 0.0


# -----------------------------
# open serial port
# -----------------------------
def open_motor_port():
    global ser
    try:
        ser = serial.Serial(com_port, baud_rate, timeout=serial_timeout)
        time.sleep(2)
        print(f"opened serial port {com_port} at {baud_rate} baud")
    except Exception as e:
        print(f"could not open serial port: {e}")
        ser = None


# -----------------------------
# open can bus
# -----------------------------
def open_can_bus():
    global can_bus
    try:
        can_bus = can.Bus(interface=can_interface, channel=can_channel, bitrate=can_bitrate)
        print(f"opened can bus: interface={can_interface}, channel={can_channel}, bitrate={can_bitrate}")
    except Exception as e:
        print(f"could not open can bus: {e}")
        can_bus = None


# -----------------------------
# mit special commands
# -----------------------------
def mit_enter_motor_mode():
    global can_bus
    if can_bus is None:
        print("can bus is not open")
        return

    msg = can.Message(
        arbitration_id=motor_can_id,
        data=[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC],
        is_extended_id=False
    )
    can_bus.send(msg)
    print("sent mit enter motor mode")


def mit_exit_motor_mode():
    global can_bus
    if can_bus is None:
        print("can bus is not open")
        return

    msg = can.Message(
        arbitration_id=motor_can_id,
        data=[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFD],
        is_extended_id=False
    )
    can_bus.send(msg)
    print("sent mit exit motor mode")


def mit_set_zero():
    global can_bus
    if can_bus is None:
        print("can bus is not open")
        return

    msg = can.Message(
        arbitration_id=motor_can_id,
        data=[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE],
        is_extended_id=False
    )
    can_bus.send(msg)
    print("sent mit set zero")


# -----------------------------
# mode 1
# -----------------------------
def send_speed_command_test(speed):
    erpm = rad_s_to_erpm(speed)
    print(f"test mode -> {speed:.2f} rad/s  |  approx {erpm} erpm")


# -----------------------------
# mode 2
# -----------------------------
def send_speed_command_dry_run(speed):
    erpm = rad_s_to_erpm(speed)

    if erpm > 50000:
        erpm = 50000
    elif erpm < -50000:
        erpm = -50000

    packet = build_servo_speed_packet(erpm)
    print(f"dry run -> {speed:.2f} rad/s  |  {erpm} erpm  |  packet: {packet.hex(' ')}")


# -----------------------------
# mode 3
# -----------------------------
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

        print(f"live servo uart -> sent {speed:.2f} rad/s  |  {erpm} erpm")

    except Exception as e:
        print(f"serial write failed: {e}")


# -----------------------------
# mode 4
# -----------------------------
def send_mit_can_command(p_des, v_des, kp, kd, t_ff):
    global can_bus

    if can_bus is None:
        print("can bus is not open")
        return

    try:
        data = build_mit_can_packet_legacy(p_des, v_des, kp, kd, t_ff)
        msg = can.Message(
            arbitration_id=motor_can_id,
            data=data,
            is_extended_id=False
        )
        can_bus.send(msg)
        print(f"mit can -> p={p_des:.2f}, v={v_des:.2f}, kp={kp:.2f}, kd={kd:.2f}, t={t_ff:.2f}")
    except Exception as e:
        print(f"mit can send failed: {e}")


# -----------------------------
# mode 5
# -----------------------------
def send_mit_can_dry_run(p_des, v_des, kp, kd, t_ff):
    try:
        data = build_mit_can_packet_legacy(p_des, v_des, kp, kd, t_ff)
        print(
            f"mit dry run -> "
            f"p={p_des:.2f}, v={v_des:.2f}, kp={kp:.2f}, kd={kd:.2f}, t={t_ff:.2f}  |  "
            f"can id={motor_can_id}  |  data: {' '.join(f'{byte:02X}' for byte in data)}"
        )
    except Exception as e:
        print(f"mit dry run failed: {e}")


# -----------------------------
# wrapper
# -----------------------------
def send_speed_command(speed):
    if mode == 1:
        send_speed_command_test(speed)
    elif mode == 2:
        send_speed_command_dry_run(speed)
    elif mode == 3:
        send_speed_command_real(speed)
    elif mode == 4:
        send_mit_can_command(
            p_des=0.0,
            v_des=speed,
            kp=mit_kp_default,
            kd=mit_kd_default,
            t_ff=mit_torque_ff_default
        )
    elif mode == 5:
        send_mit_can_dry_run(
            p_des=0.0,
            v_des=speed,
            kp=mit_kp_default,
            kd=mit_kd_default,
            t_ff=mit_torque_ff_default
        )


# -----------------------------
# repeated zero commands for stop
# -----------------------------
def emergency_stop():
    if mode in [1, 2, 3]:
        for _ in range(5):
            send_speed_command(0.0)
            time.sleep(0.02)
    elif mode == 4:
        for _ in range(5):
            send_mit_can_command(
                p_des=0.0,
                v_des=0.0,
                kp=mit_kp_default,
                kd=mit_kd_default,
                t_ff=0.0
            )
            time.sleep(0.02)
    elif mode == 5:
        for _ in range(5):
            send_mit_can_dry_run(
                p_des=0.0,
                v_des=0.0,
                kp=mit_kp_default,
                kd=mit_kd_default,
                t_ff=0.0
            )
            time.sleep(0.02)


# -----------------------------
# choose mode
# -----------------------------
mode = choose_mode()

if mode in [2, 3]:
    get_serial_settings()
    open_motor_port()
elif mode == 4:
    get_can_settings()
    open_can_bus()
    if can_bus is not None:
        enter_choice = input("send MIT enter motor mode command now? (y/n): ").strip().lower()
        if enter_choice == "y":
            mit_enter_motor_mode()

        zero_choice = input("send MIT set zero command now? (y/n): ").strip().lower()
        if zero_choice == "y":
            mit_set_zero()
elif mode == 5:
    get_can_settings()

# -----------------------------
# graph setup
# -----------------------------
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
    print("running in serial dry run mode (servo uart)")
elif mode == 3:
    print("running in live motor mode (servo uart)")
elif mode == 4:
    print("running in mit mode (can)")
    print("warning: this mit implementation may need adjustment for your exact cubemars firmware/protocol generation")
elif mode == 5:
    print("running in mit can dry run mode")
    print("no live can messages will be sent")

last_speed = 0.0

try:
    while True:
        # quit program
        if keyboard.is_pressed('q'):
            emergency_stop()
            if mode == 4 and can_bus is not None:
                exit_choice = input("send MIT exit motor mode command before closing? (y/n): ").strip().lower()
                if exit_choice == "y":
                    mit_exit_motor_mode()
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
        if can_bus is not None:
            can_bus.shutdown()
            print("can bus closed")
    except Exception:
        pass

    try:
        plt.ioff()
        plt.close('all')
    except Exception:
        pass
