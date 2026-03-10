# toby_single_leg_prototype

this repository contains code and test material for a single leg prototype for a future quadruped robot.

## current goal

get a cubemars ak40-10 motor moving from a pc keyboard through **servo-mode uart** before moving toward stm32-based control.

## hardware used

- cubemars ak40-10
- power supply
- usb serial adapter
- jst gh to uart connection
- windows pc

## what uart means in this project

uart stands for **universal asynchronous receiver-transmitter**.

for this project, uart is the serial communication link between the pc and the motor. the script does not control the motor through the cubemars upper computer software. instead, it sends command packets directly through a **usb serial adapter**.

the communication path is:

```text
pc running python script
-> usb serial adapter
-> jst gh uart cable
-> cubemars motor uart port
```

in simple terms:
- the pc runs the python script
- the script opens a **com port** on windows
- the usb serial adapter turns that pc serial connection into a uart connection
- the motor receives the uart command packets and responds to them

this is why the script asks for a **com port** in serial dry run mode and live motor mode.

## before running anything

download the script file from this repository first.

the script file should be named:

```text
motor_keyboard_test.py
```

a simple option is to download it into your downloads folder, for example:

```text
C:\Users\Owner\Downloads
```

make sure the file is actually saved as:

```text
motor_keyboard_test.py
```

and not:

```text
motor_keyboard_test.py.txt
```

## software needed

install the required python packages in command prompt:

```bash
py -m pip install keyboard matplotlib pyserial
```

if needed, you can also install `pyserial` by itself with:

```bash
py -m pip install pyserial
```

## how to run the script

once the script has been downloaded and the installs are complete, run the script from command prompt using:

```bash
py "FILE PATH OF motor_keyboard_test.py"
```

for example, if the script is in your downloads folder:

```bash
py "C:\Users\Owner\Downloads\motor_keyboard_test.py"
```

you can also move into the folder first and then run:

```bash
cd %USERPROFILE%\Downloads
py motor_keyboard_test.py
```

## script modes

when the script starts, it will ask you to choose a mode:

- `1` = test mode  
  only prints the commanded speed and shows the live graph

- `2` = serial dry run  
  opens the serial port and shows what would be sent, but does not actually move the motor

- `3` = live motor mode (**servo uart**)  
  opens the serial port and sends the real **servo-mode uart** motor command packet

important note:

- the current live script is written for **servo mode over uart**
- **mit mode is not the same protocol**
- cubeMars documents **servo mode serial communication** separately from **mit / force control**, and the MIT interface is tied to **CAN ID**, not the same uart packet path used in this script

## controls

- hold `d` = clockwise at medium speed
- hold `a` = counterclockwise at medium speed
- hold `w` + `d` or `a` = faster
- hold `s` + `d` or `a` = slower
- press `e` = emergency stop
- press `r` = reset emergency stop
- press `q` = quit

## speed setup

the script currently uses output shaft speed values in rad/s:

- slow = `1.5`
- medium = `3.0`
- fast = `4.5`

the script converts these to **erpm** internally for cubemars servo uart commands.

the ak40-10 has a **10:1 reduction ratio**, and cubemars’s upper computer materials show speed-unit conversion among rpm, erpm, rad/s, and dps. 

## packet format used by the current script

the current live script is based on the documented **cubemars servo mode serial message protocol**.

the packet structure used in the script is:

- frame head = `0x02`
- data length
- data frame
- checksum
- frame tail = `0x03`

for speed control, the script uses the **servo speed command** with command id:

- `0x08`

cubemars shows example speed-loop packets including:

- `02 05 08 00 00 03 E8 2B 58 03` for `+1000 erpm`
- `02 05 08 FF FF FC 18 43 78 03` for `-1000 erpm`

the script starts from output shaft speed in **rad/s**, then converts it internally to **erpm** before building the final packet. 

## recommended testing order

1. download `motor_keyboard_test.py`
2. install the required python packages
3. run **mode 1** first
4. confirm keyboard controls and live graph work
5. run **mode 2** second
6. confirm the correct com port opens and packet output looks normal
7. run **mode 3** only after the motor is safely mounted and ready for live testing

## serial setup

for mode 2 or mode 3, the script will ask for:

- com port, for example `COM3`
- baud rate, or press enter to use `115200`

to list available serial ports, run:

```bash
py -m serial.tools.list_ports
```

## how uart relates to the com port

on windows, the usb serial adapter usually appears as a **com port** such as `COM3` or `COM5`.

that means:
- the adapter is plugged into the pc
- windows has recognized it
- the python script can try to open that serial connection

if the wrong com port is selected, the script will not be able to talk to the motor.

## cubemars upper computer setup for ak40-10

before starting, download the CubeMars Upper Computer software from:

```text
https://www.cubemars.com/technical-support-and-software-download.html
```

for this setup:
- model = **AK40-10**
- software version = **V1.32**

cubemars’s r-link / upper computer materials show the pc connection workflow, including refreshing ports, selecting the serial connection, and connecting to the motor. 

## upper computer connection steps

1. connect the **power/ground cable** to the motor’s middle port  
2. connect the other ends to the **power supply ground and power**
3. turn the **power supply on**, but do **not** raise the voltage above zero yet
4. connect the **JST GH connector** to the motor’s **UART port**
5. connect the other end of the JST GH cable to a **USB serial adapter**
6. plug the USB serial adapter into the PC
7. open the **Upper Computer `.exe`**
8. accept the Windows warning if prompted
9. if the language is not correct, toggle the language button in the bottom left
10. click **Refresh** to display available serial / COM ports
11. select the COM port connected to the UART adapter
12. click **CONNECT**
13. you should see **Connected** in the bottom right of the screen

## if upper computer does not show connected

if you do **not** see **Connected**, do this:

1. enter the **mit control** section
2. press **Debug**
3. this opens the serial terminal
4. **MIT Mode** in the top right should turn red
5. a warning should pop up saying the connected driver is now in MIT mode
6. now give the motor about **20–24 V**
7. motor parameters should now appear in the middle of the screen

## if debug was not needed

if the connection worked normally:

1. raise the power supply to about **20–24 V**
2. you should now see the **time (s)** axis for the graphs moving
3. you can explore the basic settings under **servo / mit mode**

## encoder calibration

if encoder calibration is needed:

1. type the command:

```text
calibrate
```

2. include a space after the word when sending it if required by the software workflow
3. click **send command**
4. the motor may move slightly while phase order is checked
5. the software should generate a lookup table mapping angle information for the motor

cubemars documents encoder identification / calibration through the upper computer workflow and notes that identification should be done under no-load conditions. 

## changing can id

each motor needs a unique can id so there is no communication conflict.

to change the can id, send:

```text
set_can_id XX
```

replace `XX` with the desired can id number.

cubemars documents can id configuration in the upper computer workflow. 

## mit mode vs servo mode

**servo mode**:
- this is the mode used by the current python script
- cubemars documents a **servo mode serial message protocol**
- this protocol uses a framed **uart / serial** packet format
- the current script builds this type of packet for live testing

**mit mode**:
- commonly used in quadruped-style applications
- cubemars also refers to this as **force control mode**
- the upper computer MIT interface uses a **CAN ID**
- position mode uses **position + kp + kd**
- velocity mode uses **speed + kd**
- torque mode uses **torque**

in other words, for this repository:

- **servo mode = uart packet workflow used by the current script**
- **mit mode = separate control workflow and should not be assumed to use the same live uart packet format as mode 3**

cubemars’s MIT / force control documentation shows CAN-based control with packed command fields including desired position, speed, `kp`, `kd`, and current / torque. 

## mit control parameters

if working in **mit mode** through cubemars tools, the main control inputs are different from the current servo-uart script.

cubemars documents the mit / force control interface like this:

- **position mode** uses desired position with **kp** and **kd**
- **velocity mode** uses desired speed with **kd**
- **torque mode** uses desired torque

this is one reason mit mode should be treated as a separate workflow from the current live uart script. 

## using the python script with upper computer

in **mode 3** of the python script, the script sends a real **servo-mode uart** motor command packet.

during real testing in **mode 3**, the CubeMars Upper Computer may display the **actual behaviour of the motor**, such as live response and graph movement, if the motor and software are connected properly.

important note:

- the upper computer and the python script usually cannot control the **same serial / com port at the same time**
- the current live script is intended for **servo uart testing**
- if using **mit mode**, treat that as a separate control path rather than assuming it is the same as the current uart script

## modifying the script

the script may be modified to test other parameters, such as:
- different speed values
- different key mappings
- different control logic
- other safe test conditions

only do this if the changes are **safe** and the motor is securely mounted.

recommended rules when modifying the script:
- start with low speeds
- keep the motor unloaded at first
- secure the motor before live motion
- test one change at a time
- be ready to cut power immediately if behaviour is unexpected

## important notes

- this script is intended for **servo mode uart** control using a usb serial adapter
- speeds are treated as output **rad/s** in the script
- the script converts rad/s to **erpm** internally before sending the live packet
- the current packet builder is based on the documented **servo mode serial** packet structure
- the motor should be securely mounted before using live motor mode
- test mode and dry run mode should be used before live motor mode
- **mit mode** should be treated separately from the current live uart script
- upper computer can be useful for confirming motor response and viewing live behaviour during setup and testing

## if packages are missing

if you get a module error, install the required packages again:

```bash
py -m pip install keyboard matplotlib pyserial
```

or install `pyserial` by itself if that is the missing package:

```bash
py -m pip install pyserial
```

## if the script will not run

make sure:

- python is installed
- the packages are installed
- the script file was downloaded first
- you are using the correct file path
- the file is actually named `motor_keyboard_test.py` and not `motor_keyboard_test.py.txt`

## example run command

for this setup, the script was run with:

```bash
py "C:\Users\Owner\Downloads\motor_keyboard_test.py"
```

## protocol notes used for this project

the current script and notes are based on cubemars documentation describing:

- **servo mode serial message protocol**
- **servo speed-loop packet examples**
- **erpm-based speed commands**
- **mit / force control inputs such as kp and kd**
- **the upper computer mit interface using can id**

## project status

current focus:

- pc keyboard testing
- uart motor communication
- upper computer verification
- safe speed testing
- preparing for later stm32 integration
