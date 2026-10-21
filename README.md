# Cobble Hardware Design

## ESP32S3-supermini Pinout
![alt text](resources/diagram-3200.png)
Link: https://www.espboards.dev/esp32/esp32-s3-super-mini/

## Cobble-board-test
the Cobble-board-test/ folder contains the single layer layout design used for the cobble smoke test board.  

### Pin mapping
| ESP32-S3-super-mini Pin | Function | Notes | CircuitPython |
| --- | --- | --- | --- |
| GPIO5 / ADC1_CH4 | Light Sensor | Read analog value for representative light level measurements. | board.A4 |
| GPIO39 | Light Sensor | this pin is digital only and should be set to input no pull up/down | board.IO39 |
| GPIO40 | Vibration Sensor | configure pin as input with pull up.  vibration will be active low | board.IO40 |
| GPIO9 | PushButton | configure pin as input with pull up.  PushButton will be active low | board.IO9 |
| GPIO8 | Buzzer | **Never leave high!**.  set as output low when not in use.  drive with PWM 50% duty cycle to create sound | board.IO8 |
| GPIO6 | SCL | Use for I2C communications with device on J3 Stemma or J4 Grove connectors | board.IO6 |
| GPIO7 | SDA | Use for I2C communications with devices on J3 Stemma or J4 Grove connectors | board.IO7 |
| GPIO48 | neopixel | neopixel is attached to this pin | board.IO48 |


### Design notes
Note about 5V Power:
- When USB is connected this will be 5V from VBUS
- When running from a battery this will be Vbatt-V_protection_diode
- Battery can only charge when USB is connected and power switch is 'ON'

### CicuitPython Notes
Testing completed with: 
- Version: 10.3.1
- Using the ESP32-S3-Zero build of CircuitPython.  It is a good standin for the super mini on our board: https://circuitpython.org/board/waveshare_esp32_s3_zero/
- the `boot_out.txt` file is an informational text file automatically generated on the root of the CIRCUITPY drive every time a CircuitPython board powers up or resets.  Contains:
  - CircuitPython Version
  - Build Date
  - Board Model
  - Board ID
  - UID
  - MAC

#### Tips & tricks
- **Pin objects**: 
  - Digital pins are `board.IOx` (e.g. `board.IO9`)
  - The analog light pin is `board.A4` (GPIO5 / ADC1_CH4).
- **Analog input**: 
  - Use `analogio.AnalogIn(pin)`. There is no `board.ADC()`.
  - Read the value with `.value` (0–65535)
- **Digital input**: 
  - set direction with `digitalio.Direction.INPUT`
- **Digital input Pull UP / DOWN**: 
  - set a pull up with `.pull = digitalio.Pull.UP`
  - set a pull down with `.pull = digitalio.Pull.DOWN`
- **I2C**: 
  - Use `busio.I2C(scl_pin, sda_pin)` to configure the I2C
- **NeoPixel**: the constructor is `neopixel.NeoPixel(pin, n, brightness=...)` —
  the `pixel_bit_depth` keyword is not accepted on this build.
- **Light Sensor**: due to a design issue the lightsensor is connected to IO39 and A4.  reading the light sensor is done with A4, but IO39 needs to be set as an input without configuring a pull up so it does not impact the reading of A4.

### Example Code Snippets
#### **I2C**: Configure I2C bus and scan for devices
``` python
i2c = busio.I2C(board.IO6, board.IO7)  # SCL, SDA for J3/J4 connectors
def scan_i2c():`
    """Scan the I2C bus and return list of connected device addresses."""
    devices = []
    if not i2c.try_lock():
        return devices
    try:
        for addr in range(0x08, 0x78):
            try:
                i2c.writeto(addr, b"")
                devices.append(addr)
            except OSError:
                pass
    finally:
        i2c.unlock()
    return devices

```
#### **Speaker**: Configure pin for PWM and play tone
``` python
piezo = pwmio.PWMOut(board.IO8, frequency=440, duty_cycle=0, variable_frequency=True)

# 8 notes of a C Major octave (C5 to C6) in Hertz
OCTAVE_NOTES = [
    523,  # C5
    587,  # D5
    659,  # E5
    698,  # F5
    784,  # G5
    880,  # A5
    988,  # B5
]

def startup_song():
    # Loop through each note in the octave scale
    for freq in OCTAVE_NOTES:
        piezo.frequency = freq
        piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
        time.sleep(0.1)           # Play note for 0.1s
    
    # Mute tone and clean up hardware resource
    piezo.duty_cycle = 0

```
#### **RGB LED Neopixel**: Configure pin and show RGB colors
``` python
import neopixel

# Initialize NeoPixel on the default board pin (or replace board.NEOPIXEL with board.IOx)
pixel = neopixel.NeoPixel(board.IO48, 1, brightness=0.2)

# Set color to Green (RGB: Red=0, Green=255, Blue=0)
pixel[0] = (0, 255, 0)

def wheel(pos):
    """Return an RGB tuple for a position 0-255 around the color wheel."""
    pos %= 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)

# Rainbow fade state: hue position (0-255) and per-step increment
hue = 0
HUE_STEP = 2  # higher = faster cycle

def rainbow():
    """Advance the hue and set the pixel to the new rainbow color."""
    global hue
    hue = (hue + HUE_STEP) % 256
    pixel[0] = wheel(hue)
```

#### Included modules:
_asyncio
_bleio
_bleio (native)
_eve
_pixelmap
adafruit_bus_device
adafruit_pixelbuf
aesio
alarm
analogbufio
analogio
array
atexit
audiobusio
audiocore
audioi2sin
audiomixer
audiomp3
binascii
bitbangio
bitmapfilter
bitmaptools
board
builtins
builtins.pow3
busdisplay
busio
busio.SPI
busio.UART
canio
codeop
collections
countio
digitalio
displayio
epaperdisplay
errno
espcamera
espidf
espnow
espulp
fontio
fourwire
framebufferio
frequencyio
getpass
gifio
hashlib
i2cdisplaybus
io
ipaddress
jpegio
json
keypad
keypad.KeyMatrix
keypad.Keys
keypad.ShiftRegisterKeys
keypad_demux
keypad_demux.DemuxKeyMatrix
locale
lvfontio
math
max3421e
mdns
memorymap
microcontroller
msgpack
neopixel_write
neopixel
nvm
onewireio
os
os.getenv
paralleldisplaybus
ps2io
pulseio
pwmio
qrio
rainbowio
random
re
rgbmatrix
rotaryio
rtc
sdcardio
sdioio
select
sharpdisplay
socketpool
socketpool.socketpool.AF_INET6
ssl
storage
struct
supervisor
supervisor.get_setting
synthio
sys
terminalio
tilepalettemapper
time
touchio
traceback
ulab
usb
usb_audio
usb_cdc
usb_hid
usb_midi
vectorio
warnings
watchdog
wifi
zlib
