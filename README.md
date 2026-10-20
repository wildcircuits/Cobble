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


#### API quirks for this build (10.3.1, waveshare_esp32_s3_zero)
These differ from the generic CircuitPython docs and from other builds.

- **Pin objects**: digital pins are `board.IOx` (e.g. `board.IO9`), not `board.GPIOx`.
  The analog light pin is `board.A4` (GPIO5 / ADC1_CH4).
- **Analog input**: use `analogio.AnalogIn(pin)`. There is no `board.ADC()`.
  Read the value with `.value` (0–65535), not `.read_value`.
- **Digital input**: set direction with `digitalio.Direction.INPUT`, not
  `digitalio.DigitalInOut.DIR_INPUT`.
- **Digital input PullUp**: set a pull p with `.pull = digitalio.Pull.UP`
- **I2C**: there is no top-level `i2c` module and no `board.I2C()`. Use
  `busio.I2C(scl_pin, sda_pin)`.
- **I2C scan**: the `I2C` object has no `probe_addr()` method. Scan by trying
  `i2c.writeto(addr, b"")` for each address while holding `i2c.try_lock()`.
- **PWM**: `PWMOut.frequency` is read-only — you cannot retune a running PWM
  object. To change frequency, `deinit()` the object and create a new
  `pwmio.PWMOut(pin, frequency=..., duty_cycle=...)`.
- **NeoPixel**: the constructor is `neopixel.NeoPixel(pin, n, brightness=...)` —
  the `pixel_bit_depth` keyword is not accepted on this build.
- **Light Sensor**: due to a design issue the lightsensor is connected to IO39 and A4.  reading the light sensor is done with A4, but IO39 needs to be set as an input without configuring a pull up so it does not impact the reading of A4.

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
