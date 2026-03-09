# toby_single_leg_prototype

this repository contains code and test material for a single leg prototype for a future quadruped robot.

## current goal

get a cubemars ak40-10 motor moving from a pc keyboard through uart before moving to stm32 control.

## hardware used
For the test modes in the associated script, only a PC is required
- cubemars ak40-10
- usb serial adapter
- jst gh to uart connection
- windows pc

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

once the installs are complete, run the script from command prompt using:

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

- `3` = live motor mode  
  opens the serial port and sends the real motor command packet

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

the script converts these to erpm internally for cubemars servo uart commands.

## recommended testing order

1. run **mode 1** first
2. confirm keyboard controls and live graph work
3. run **mode 2** second
4. confirm the correct com port opens and packet output looks normal
5. run **mode 3** only after the motor is safely mounted and ready for live testing

## serial setup

for mode 2 or mode 3, the script will ask for:

- com port, for example `COM3`
- baud rate, or press enter to use `115200`

to list available serial ports, run:

```bash
py -m serial.tools.list_ports
```

## important notes

- this script is intended for uart control using a usb serial adapter
- speeds are treated as output rad/s in the script
- the script converts rad/s to erpm internally
- the motor should be securely mounted before using live motor mode
- test mode and dry run mode should be used before live motor mode

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
- uart motor communication
- safe speed testing
- preparing for later stm32 integration
