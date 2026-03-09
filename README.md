# toby_single_leg_prototype

this repository contains code, notes, and testing material for a single leg prototype for TOBY.

## current goal

get a cubemars ak40-10 motor moving from a pc keyboard through uart before moving to stm32 control.

## current hardware

- cubemars ak40-10
- usb serial adapter
- pc
- uart connection through jst gh

## current software

- python
- keyboard
- matplotlib
- pyserial

## current script features

- test mode
- serial dry run mode
- live motor mode
- live speed graph
- emergency stop latch

## next steps

- verify uart motor movement
- move control logic to stm32
- expand toward single leg control
