# toby_single_leg_prototype

this repository contains code and test material for a single leg prototype for a future quadruped robot.

## current goal

get a cubemars ak40-10 motor moving from a pc keyboard through **servo-mode uart**, while also building a **mit can** testing path for future quadruped-style control and STM32 integration.

## hardware used

- cubemars ak40-10
- power supply
- usb serial adapter
- jst gh to uart connection
- windows pc
- usb-to-can adapter for mit can testing

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
py -m pip install keyboard matplotlib pyserial python-can
```

if needed, you can also install packages individually:

```bash
py -m pip install keyboard
py -m pip install matplotlib
py -m pip install pyserial
py -m pip install python-can
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

## communication overview

this project now includes **two communication paths**:

### servo uart path
used for:
- mode 2 = servo uart dry run
- mode 3 = live servo uart motor control

hardware path:

```text
pc running python script
-> usb serial adapter
-> jst gh uart cable
-> cubemars motor uart port
```

### mit can path
used for:
- mode 4 = live mit can mode
- mode 5 = mit can dry run

hardware path:

```text
pc running python script
-> usb-to-can adapter
-> can connection
-> motor can interface
```

important note:
- **servo uart** and **mit can** are not the same workflow
- modes 2 and 3 use **uart**
- modes 4 and 5 use **can**
- for mit testing, you need a **usb-to-can adapter**, not only a usb serial adapter

## script modes

when the script starts, it will ask you to choose a mode:

- `1` = test mode  
  only prints the commanded speed and shows the live graph

- `2` = serial dry run (**servo uart**)  
  opens the serial setup and shows what would be sent, but does not actually move the motor

- `3` = live motor mode (**servo uart**)  
  opens the serial port and sends the real servo-mode uart motor command packet

- `4` = mit mode (**can**)  
  opens the can interface and sends live mit-style can commands

- `5` = mit can dry run  
  does not send live can traffic, but shows the mit can packet data that would be transmitted

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

for servo uart mode, the script converts these internally to **erpm** before building the final packet.

## recommended testing order

1. download `motor_keyboard_test.py`
2. install the required python packages
3. run **mode 1** first
4. confirm keyboard controls and live graph work
5. run **mode 2** second
6. confirm the correct com port opens and servo packet output looks normal
7. run **mode 3** only after the motor is safely mounted and ready for live testing
8. run **mode 5** before trying live mit can
9. run **mode 4** last, only after the can setup is known and safe

## servo uart setup

for mode 2 or mode 3, the script will ask for:

- com port, for example `COM3`
- baud rate, or press enter to use `115200`

to list available serial ports, run:

```bash
py -m serial.tools.list_ports
```

on windows, the usb serial adapter usually appears as a **com port** such as `COM3` or `COM5`.

that means:
- the adapter is plugged into the pc
- windows has recognized it
- the python script can try to open that serial connection

if the wrong com port is selected, the script will not be able to talk to the motor.

## mit can setup

for mode 4 or mode 5, the script will ask for:

- can interface, for example `pcan`
- can channel, for example `PCAN_USBBUS1`
- can bitrate, default `1000000`
- motor can id
- default mit values such as `kp`, `kd`, and torque feedforward

important note:
- you need a **usb-to-can adapter** for mit can modes
- mode 5 is the safest way to inspect the can packets before sending anything live
- the mit can implementation in this project is a practical starting point and may need adjustment depending on the exact cubemars firmware or protocol generation

## servo packet format used by the current script

the current live servo script is based on a framed servo-uart packet workflow.

the packet structure used in the script is:

- frame head = `0x02`
- data length
- data frame
- checksum
- frame tail = `0x03`

for speed control, the script uses command id:

- `0x08`

the speed value is sent as **erpm**.

the script starts from output shaft speed in **rad/s**, then converts it internally to **erpm** before building the final packet.

## mit can packet notes

the mit can part of the script uses:
- packed 8-byte command data
- desired position
- desired velocity
- `kp`
- `kd`
- torque feedforward

mode 4 sends live mit can commands.

mode 5 prints the packet bytes only, so you can inspect the data before doing live testing.

the current mit packing in this repository should be treated as a **legacy-style starting point**, not a guaranteed final implementation for every cubemars firmware version.

## cubemars upper computer setup for ak40-10

before starting, download the CubeMars Upper Computer software from:

```text
https://www.cubemars.com/technical-support-and-software-download.html
```

for this setup:
- model = **AK40-10**
- software version = **V1.32**

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

## changing can id

each motor needs a unique can id so there is no communication conflict.

to change the can id, send:

```text
set_can_id XX
```

replace `XX` with the desired can id number.

## using the python script with upper computer

in **mode 3**, the python script sends live **servo uart** motor commands.

during real testing in **mode 3**, the CubeMars Upper Computer may display the **actual behaviour of the motor**, such as live response and graph movement, if the motor and software are connected properly.

important note:

- the upper computer and the python script usually cannot control the **same serial / com port at the same time**
- the current live uart script is intended for **servo uart testing**
- mit can testing should be treated as a separate control path

## modifying the script

the script may be modified to test other parameters, such as:
- different speed values
- different key mappings
- different control logic
- different default mit values
- other safe test conditions

only do this if the changes are **safe** and the motor is securely mounted.

recommended rules when modifying the script:
- start with low speeds
- keep the motor unloaded at first
- secure the motor before live motion
- test one change at a time
- be ready to cut power immediately if behaviour is unexpected

## important notes

- modes 2 and 3 are for **servo uart**
- modes 4 and 5 are for **mit can**
- speeds are treated as output **rad/s** in the script
- the servo-uart path converts rad/s to **erpm**
- the motor should be securely mounted before any live mode is used
- test mode and dry run modes should be used before live modes
- upper computer can be useful for confirming motor response and viewing live behaviour during setup and testing
- mit can live mode may need adjustment depending on the exact cubemars firmware or protocol generation

## if packages are missing

if you get a module error, install the required packages again:

```bash
py -m pip install keyboard matplotlib pyserial python-can
```

or install a missing package by itself, for example:

```bash
py -m pip install keyboard
py -m pip install matplotlib
py -m pip install pyserial
py -m pip install python-can
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

## project status

current focus:

- pc keyboard testing
- servo uart communication
- mit can packet testing
- upper computer verification
- safe speed testing
- preparing for later stm32 integration
