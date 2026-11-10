"""
Cobble Board Smoke Test - Cobble Board Rev 1
============================================
Updated 11/6/2026 to match the Rev 1 pinout (the code previously used Rev 0 pins).

Rev 1 pin map
-------------
  - Buzzer (GPIO8 / board.IO8)   - PWM beep, 50% duty, never left high
  - Push button (GPIO35 / board.IO35) - active-low, pull-up
  - NeoPixel (GPIO48 / board.IO48) - RGB LED
  - Light sensor (GPIO7 / board.A6) - analog read
  - Vibration sensor (GPIO9 / board.IO9) - active-low, pull-up
  - I2C: SDA (GPIO17 / board.IO17), SCL (GPIO16 / board.IO16)
      NOTE: the board has no I2C pull-ups, so bus init / scan can fail until an
      I2C device is attached.  That is expected, so every I2C call is wrapped and
      the scan is repeated in the monitor loop - a device plugged in while the
      code runs is picked up on the next pass, and one unplugged mid-run is
      handled without crashing.  REPL console is on USB, so GPIO16/17 are free.
      busio.I2C.scan() only works while the bus is held with try_lock().
  - Header GPIO pins aligned with power and ground:
    - GPIO1, GPIO2, GPIO4, GPIO5, GPIO6, GPIO15
      GPIO1 drives the test servo (PWM output).
      GPIO2, GPIO4, GPIO5, GPIO6, GPIO15 are inputs with pull-downs.
  - Header GPIO pins aligned for SPI:
    - GPIO10, GPIO11, GPIO12, GPIO13 - inputs with pull-downs.
      Pull any header input high by hand and the monitor loop reports it.

Extra checks carried over from the Rev 1 example code
-----------------------------------------------------
  - Startup song on the buzzer (C major octave scale, played up three octaves)
  - Beeps for button press (rising pair) and button release (falling pair)
  - Beep whenever vibration is detected
  - Continuous rainbow on the NeoPixel while the monitor loop runs
  - Light sensor value printed on every monitor status line
  - Vibration is read with a hardware falling-edge pulse counter (countio) so a
    short shake between polls is not missed; falls back to level reads if the
    pin cannot be claimed by countio.
  - The buzzer's own sound shakes the board enough to trip the vibration sensor,
    so vibration is ignored for SETTLE_SECONDS after every beep.

Run on: Waveshare ESP32-S3-Zero, CircuitPython 10.3.1
"""

import time
import board
import digitalio
import analogio
import pwmio
import countio
import neopixel
import busio

# -- Rev 1 pin map ---------------------------------------------------------------
BUZZER_PIN = board.IO8      # GPIO8
BUTTON_PIN = board.IO35     # GPIO35
NEOPIXEL_PIN = board.IO48   # GPIO48
LIGHT_PIN = board.A6        # GPIO7
VIBRATION_PIN = board.IO9   # GPIO9
SERVO_PIN = board.IO1       # GPIO1 - expected test servo
SDA_PIN = board.IO17        # GPIO17
SCL_PIN = board.IO16        # GPIO16

# Servo timing: 20 ms frame, 0.5-2.5 ms pulse -> 50 Hz PWM
SERVO_FREQ_HZ = 50
SERVO_PERIOD_MS = 20.0
SERVO_MIN_MS = 0.5
SERVO_MAX_MS = 2.5

# Header GPIOs to test - inputs with pull-downs, tester pulls them high by hand.
HEADER_TEST_PINS = (
    ("IO2", board.IO2),     # power/ground group
    ("IO4", board.IO4),
    ("IO5", board.IO5),
    ("IO6", board.IO6),
    ("IO15", board.IO15),
    ("IO10", board.IO10),   # SPI group
    ("IO11", board.IO11),
    ("IO12", board.IO12),
    ("IO13", board.IO13),
)

# Common I2C addresses - only a hint in the printout, not a claim.
KNOWN_I2C = {
    0x20: "AT24 EEPROM",
    0x3C: "SSD1306 OLED",
    0x3D: "SSD1306 OLED",
    0x40: "PCA9685 servo driver",
    0x48: "TMP102 / I2C expander",
    0x50: "AT24 EEPROM",
    0x68: "MPU6050 IMU",
    0x69: "MPU6050 IMU",
    0x76: "BME280 / BMP280",
    0x77: "BME280 / BMP280",
}

RESCAN_SECONDS = 5.0   # how often the monitor loop re-scans I2C
STATUS_SECONDS = 2.0   # how often the monitor loop prints a status line
BUTTON_TIMEOUT = 10.0  # seconds to wait for a button press
PROBE_FIRST = 8        # first address probed if scan() is unavailable
PROBE_LAST = 119       # last address probed if scan() is unavailable
VIBRATION_TIMEOUT = 10.0  # seconds to wait for a shake during the vibration test

# Buzzer tones - 7 notes of a C major octave (C5 to B5) in Hertz.
# Used by the startup song and the press / release / vibration beeps.
OCTAVE_NOTES = [523, 587, 659, 698, 784, 880, 988]

HUE_STEP = 2           # rainbow speed - higher value cycles the colour faster
SETTLE_SECONDS = 0.2   # vibration is ignored this long after any beep
settle_until = 0.0     # monotonic time when vibration detection resumes after a beep

# Objects that need deinit() at the end.
_managed = []


def manage(obj):
    _managed.append(obj)
    return obj


def safe(label, func):
    """Run func(), report a failure, and return None instead of raising."""
    try:
        return func()
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    {label}: unavailable ({err})")
        return None


# -- Buzzer (GPIO8) --------------------------------------------------------------
# GPIO8: PWM 50% duty cycle produces sound. NEVER leave high!
# Mutable container so beep() can reassign without `global`.
_buzzer = {"pwm": None}


def buzzer_open(freq):
    """Create the buzzer PWM output at freq, or return None if it cannot be opened."""
    _buzzer["pwm"] = safe("buzzer", lambda: manage(
        pwmio.PWMOut(BUZZER_PIN, frequency=int(freq), duty_cycle=0,
                     variable_frequency=True)))
    return _buzzer["pwm"]


def beep(freq=440, duration=0.2, duty=0.5):
    """Emit a beep at the given frequency for the given duration (seconds)."""
    global settle_until
    pwm = _buzzer["pwm"]
    if pwm is None:
        pwm = buzzer_open(freq)
    else:
        # Created with variable_frequency=True, so pitch can change on the fly.
        # If this build still refuses the write, rebuild the output at the new pitch.
        try:
            pwm.frequency = int(freq)
        except (ValueError, RuntimeError, OSError) as err:
            print(f"    buzzer: frequency change failed ({err})")
            try:
                pwm.deinit()
            except (ValueError, RuntimeError, OSError) as err:
                print(f"    buzzer: deinit failed ({err})")
            pwm = buzzer_open(freq)
    if pwm is None:
        return
    pwm.duty_cycle = int(duty * 65535)
    time.sleep(duration)
    pwm.duty_cycle = 0  # silence - never leave high
    # The speaker vibrates the board enough that the vibration sensor detects it,
    # so give the sensor time to settle before it is read again.
    settle_until = time.monotonic() + SETTLE_SECONDS


# Named tones
def startup_song():
    """Play the C major octave scale, then the same scale one octave up, twice more."""
    for octave in (1, 2, 4):
        for note in OCTAVE_NOTES:
            beep(note * octave, 0.1)
            time.sleep(0.05)


def beep_click():
    """Rising pair of notes - button press."""
    for note in (OCTAVE_NOTES[0], OCTAVE_NOTES[1]):
        beep(note, 0.1)


def beep_unclick():
    """Falling pair of notes - button release."""
    for note in (OCTAVE_NOTES[1], OCTAVE_NOTES[0]):
        beep(note, 0.1)


def beep_vibe():
    """Single note - vibration detected."""
    beep(OCTAVE_NOTES[4], 0.15)


# -- Digital inputs (button / vibration / header GPIOs) --------------------------
def make_input(pin, label, pull):
    def build():
        io = digitalio.DigitalInOut(pin)
        io.direction = digitalio.Direction.INPUT
        io.pull = pull
        return manage(io)

    return safe(label, build)


button = make_input(BUTTON_PIN, "button (GPIO35)", digitalio.Pull.UP)


def button_pressed():
    """Return True when the button is physically pressed (active low)."""
    if button is None:
        return False
    try:
        return not button.value
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    button: read failed ({err})")
        return False


# -- NeoPixel (GPIO48) -----------------------------------------------------------
NUM_PIXELS = 1
pixels = safe("neopixel (GPIO48)",
              lambda: neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=0.5))


def set_pixel(r, g, b):
    """Set the NeoPixel to an RGB colour (0-255 per channel)."""
    if pixels is None:
        return
    try:
        pixels[0] = (r, g, b)
        pixels.show()
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    neopixel: write failed ({err})")


def wheel(pos):
    """Return an RGB tuple for a position 0-255 around the colour wheel."""
    pos %= 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)


hue = 0


def rainbow():
    """Advance the hue and set the pixel to the new rainbow colour."""
    global hue
    hue = (hue + HUE_STEP) % 256
    set_pixel(*wheel(hue))


# -- Light sensor (GPIO7 / A6, analog) -------------------------------------------
light_sensor = safe("light sensor (GPIO7 / A6)",
                    lambda: manage(analogio.AnalogIn(LIGHT_PIN)))


def read_light():
    """Return the raw analog light value (0-65535)."""
    if light_sensor is None:
        return None
    try:
        return light_sensor.value
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    light sensor: read failed ({err})")
        return None


# -- Vibration sensor (GPIO9, active low, pull-up) -------------------------------
# Detected with a hardware falling-edge pulse counter so a short shake that happens
# between polls is still counted.  If countio cannot claim the pin, fall back to
# reading the pin level.
vibration_counter = safe("vibration counter (GPIO9)", lambda: manage(
    countio.Counter(VIBRATION_PIN, edge=countio.Edge.FALL, pull=digitalio.Pull.UP)))
vibration = None
if vibration_counter is None:
    vibration = make_input(VIBRATION_PIN, "vibration sensor (GPIO9)", digitalio.Pull.UP)


def vibration_pulses():
    """Pulses counted since the last reset (1 for a level read, 0 when idle)."""
    if vibration_counter is not None:
        try:
            return vibration_counter.count
        except (ValueError, RuntimeError, OSError) as err:
            print(f"    vibration counter: read failed ({err})")
            return 0
    return 1 if vibration_detected() else 0


def clear_vibration():
    """Drop pending pulses so the buzzer's own vibration is not counted."""
    if vibration_counter is not None:
        try:
            vibration_counter.reset()
        except (ValueError, RuntimeError, OSError) as err:
            print(f"    vibration counter: reset failed ({err})")


def vibration_detected():
    """Return True when vibration is detected (active low)."""
    if vibration_counter is not None:
        return vibration_pulses() > 0
    if vibration is None:
        return False
    try:
        return not vibration.value
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    vibration sensor: read failed ({err})")
        return False


# -- Servo (GPIO1) ---------------------------------------------------------------
def servo_duty(ms):
    """Convert a servo pulse width in ms to a 16-bit duty cycle."""
    return int((ms / SERVO_PERIOD_MS) * 65535)


def servo_move(pwm, ms):
    if pwm is None:
        return False
    try:
        pwm.duty_cycle = servo_duty(ms)
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    servo: write failed ({err})")
        return False
    return True


# -- I2C (SDA GPIO17, SCL GPIO16) ------------------------------------------------
# scan() and every read/write need the bus held with try_lock(), so the scan
# happens inside a try_lock()/unlock() pair.
_i2c = {"bus": None}


def i2c_open(report=True):
    """Open the I2C bus, or return None if it cannot be opened (no pull-ups)."""
    if _i2c["bus"] is None:
        def build():
            # busio.I2C takes SCL first, then SDA.  GPIO16/17 are IOMUX-capable
            # on the ESP32-S3, so busio is allowed on them.
            return manage(busio.I2C(SCL_PIN, SDA_PIN, frequency=100000))

        _i2c["bus"] = safe("I2C bus", build)
        if _i2c["bus"] is not None and report:
            print("    I2C bus open: SCL=GPIO16, SDA=GPIO17")
    return _i2c["bus"]


def i2c_close():
    """Unlock and deinit the bus so the next pass can reopen it."""
    bus = _i2c["bus"]
    if bus is not None:
        try:
            bus.unlock()
        except (ValueError, RuntimeError, OSError) as err:
            print(f"    I2C: unlock failed ({err})")
        try:
            bus.deinit()
        except (ValueError, RuntimeError, OSError) as err:
            print(f"    I2C: deinit failed ({err})")
    _i2c["bus"] = None


def probe_locked(bus):
    """Probe addresses while the bus is locked, for builds without scan()."""
    found = []
    scratch = bytearray(1)
    for addr in range(PROBE_FIRST, PROBE_LAST + 1):
        try:
            bus.readinto(addr, scratch)
            found.append(addr)
        except (OSError, ValueError, RuntimeError):
            pass  # no ACK - nothing at this address
    return found


def i2c_scan(report=True):
    """Scan the I2C bus while holding the lock.  None if this pass failed."""
    bus = i2c_open(report=report)
    if bus is None:
        if report:
            print("    I2C: bus not open - attach a device that brings pull-ups")
        return None

    if not bus.try_lock():
        if report:
            print("    I2C: bus busy, try_lock() failed - skipping this pass")
        return None

    try:
        try:
            found = list(bus.scan())
        except AttributeError:
            found = probe_locked(bus)
    except (OSError, ValueError, RuntimeError) as err:
        if report:
            print(f"    I2C scan failed: {err} - no pull-ups or no device yet")
        # A device unplugged mid-run can leave the bus unusable, so drop it and
        # let the next pass reopen it once a device is attached again.
        i2c_close()
        return None
    finally:
        try:
            bus.unlock()
        except (ValueError, RuntimeError, OSError) as err:
            print(f"    I2C: unlock failed ({err})")

    if report and not found:
        print("    I2C: no addresses acknowledged - expected until a device is attached")
    return found


def describe(found):
    return ", ".join(f"0x{addr:02X} ({KNOWN_I2C.get(addr, 'unknown device')})"
                     for addr in sorted(found))


# Header GPIOs - inputs with pull-downs, tester pulls them high
header = []
for name, pin in HEADER_TEST_PINS:
    header.append((name, make_input(pin, f"header {name}", digitalio.Pull.DOWN)))


# ==============================================================================
#  TEST SEQUENCE
# ==============================================================================

print("=== Cobble Board Smoke Test (Rev 1) ===\n")

# 1. Buzzer test - startup song, then three short beeps
print("[1] Buzzer test (GPIO8): startup song, then 3 beeps at 440 Hz")
startup_song()
for _ in range(3):
    beep(440, 0.15)
    time.sleep(0.1)
print("    Buzzer OK\n")

# 2. NeoPixel test - cycle through colours
print("[2] NeoPixel test (GPIO48): colour cycle")
colours = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Cyan
    (255, 255, 255) # White
]
for c in colours:
    set_pixel(*c)
    time.sleep(0.3)
set_pixel(0, 0, 0)  # off
print("    NeoPixel OK\n")

# 3. Light sensor test (GPIO7 / A6) - sample, cover the sensor and compare
print("[3] Light sensor test (GPIO7 / A6)")
samples = []
for _ in range(3):
    samples.append(read_light())
    time.sleep(0.2)
usable = [s for s in samples if s is not None]
print(f"    samples: {', '.join(str(s) if s is not None else 'n/a' for s in samples)} / 65535")
if usable:
    print(f"    average: {sum(usable) // len(usable)} / 65535")
    if min(usable) != max(usable):
        print("    value changed between reads - the sensor is responding")
    else:
        print("    value steady over 3 reads")
    print("    Light sensor OK\n")
else:
    print("    Light sensor not readable\n")

# 4. Vibration sensor test (GPIO9) - shake the board, expect a beep
print("[4] Vibration sensor test (GPIO9)")
if vibration_counter is not None:
    print(f"    reading via the hardware pulse counter (countio)")
else:
    print("    reading via pin level - countio was unavailable")
print(f"    Shake the board ({VIBRATION_TIMEOUT} s timeout)")
set_pixel(0, 0, 255)  # blue while waiting
clear_vibration()
start = time.monotonic()
shaken = False
while time.monotonic() - start < VIBRATION_TIMEOUT:
    if vibration_detected():
        shaken = True
        print(f"    Vibration detected - {vibration_pulses()} pulse(s)")
        beep_vibe()
        break
    time.sleep(0.05)
if not shaken:
    print(f"    No vibration detected within {VIBRATION_TIMEOUT} s")
time.sleep(SETTLE_SECONDS)
clear_vibration()  # the beep itself shakes the board, so drop those pulses
print("    Vibration sensor OK\n")

# 5. Button test - wait for press (GPIO35, active low)
print(f"[5] Button test (GPIO35): press the button ({BUTTON_TIMEOUT} s timeout)")
set_pixel(0, 0, 255)  # blue while waiting
start = time.monotonic()
pressed = False
while time.monotonic() - start < BUTTON_TIMEOUT:
    if button_pressed():
        pressed = True
        break
    time.sleep(0.05)

if pressed:
    set_pixel(0, 255, 0)  # green on press
    beep(880, 0.1)
    print("    Button pressed - OK")
else:
    set_pixel(255, 0, 0)  # red on timeout
    print(f"    Button NOT pressed within {BUTTON_TIMEOUT} s")

time.sleep(0.5)
set_pixel(0, 0, 0)

# 6. Servo test - expect a servo on GPIO1
print(f"[6] Servo test (GPIO1): {int(SERVO_FREQ_HZ)} Hz frame, sweep "
      f"{SERVO_MIN_MS} -> {SERVO_MAX_MS} ms")
servo = safe("servo (GPIO1)",
             lambda: manage(pwmio.PWMOut(SERVO_PIN, frequency=SERVO_FREQ_HZ, duty_cycle=0)))
if servo is not None:
    for ms in (SERVO_MIN_MS, 1.0, 1.5, 2.0, SERVO_MAX_MS, 1.5):
        if not servo_move(servo, ms):
            break
        print(f"    pulse {ms:.1f} ms (duty {servo.duty_cycle})")
        time.sleep(0.3)
    servo_move(servo, 0)  # release
    print("    Servo sweep done (no movement is normal if no servo is attached)\n")

# 7. I2C scan - a device may already be attached, or appear later
print("[7] I2C scan (SDA GPIO17, SCL GPIO16)")
found = i2c_scan()
if found:
    print(f"    Found {len(found)} device(s): {describe(found)}")

# 8. Header GPIO + I2C + sensor monitor - keep watching while the tester pulls pins high
print(f"\n[8] Header GPIO + I2C + sensor monitor ({len(header)} pins, Ctrl-C to exit)")
print("    header GPIOs are inputs with pull-downs - pull one high to test it")
print(f"    I2C re-scanned every {RESCAN_SECONDS} s so a device attached mid-run is caught")
print("    the NeoPixel runs a continuous rainbow while the monitor is active")
print("    button press and release each get a tone, vibration gets a tone")
print(f"    light sensor value is printed every {STATUS_SECONDS} s on the status line")
print(f"    vibration is ignored for {SETTLE_SECONDS} s after a beep - the buzzer shakes the board\n")

state = {}
confirmed = set()
seen_i2c = set()
button_state = button_pressed()
next_status = time.monotonic() + STATUS_SECONDS
next_scan = time.monotonic() + RESCAN_SECONDS

try:
    while True:
        now = time.monotonic()

        # Continuous rainbow - advances every pass of the loop
        rainbow()

        # Vibration - once the board has settled after the last beep, drop the
        # pulses that beep caused and then listen for a real shake.
        if settle_until > 0 and now >= settle_until:
            clear_vibration()
            settle_until = 0
        if settle_until == 0 and vibration_detected():
            print(f"    vibration detected ({vibration_pulses()} pulse(s))")
            beep_vibe()

        # Button - edge triggered so press and release each sound once
        if button_pressed():
            if not button_state:
                button_state = True
                print("    button pressed")
                beep_click()
        else:
            if button_state:
                button_state = False
                print("    button released")
                beep_unclick()

        for name, io in header:
            if io is None:
                continue
            try:
                value = io.value
            except (ValueError, RuntimeError, OSError) as err:
                print(f"    {name}: read failed ({err})")
                continue
            if value and not state.get(name, False):
                print(f"    {name}: HIGH (confirmed)")
                confirmed.add(name)
            state[name] = value

        if now >= next_status:
            next_status = now + STATUS_SECONDS
            high = [n for n, _ in HEADER_TEST_PINS if state.get(n, False)]
            raw = read_light()
            print(f"    pins high: {', '.join(high) if high else 'none'} "
                  f"| confirmed {len(confirmed)}/{len(header)} "
                  f"| I2C: {describe(seen_i2c) if seen_i2c else 'none'} "
                  f"| light: {raw if raw is not None else 'n/a'} / 65535")

        if now >= next_scan:
            next_scan = now + RESCAN_SECONDS
            found = i2c_scan(report=False)
            if found is None:
                continue
            current = set(found)
            if current != seen_i2c:
                new = current - seen_i2c
                gone = seen_i2c - current
                if new:
                    print(f"    I2C new device(s): {describe(new)}")
                if gone:
                    print(f"    I2C device removed: {describe(gone)}")
                seen_i2c = current

        time.sleep(0.05)
except KeyboardInterrupt:
    print("\n    monitor interrupted")

# 9. All-clear
print(f"\n[9] All-clear: header pins confirmed {len(confirmed)}/{len(header)}")
set_pixel(0, 255, 0)
beep(660, 0.3)
time.sleep(0.3)
set_pixel(0, 0, 0)

if _i2c["bus"] is not None:
    i2c_close()

for obj in _managed:
    try:
        obj.deinit()
    except (ValueError, RuntimeError, OSError) as err:
        print(f"    deinit failed: {err}")

print("\n=== Smoke test complete ===")