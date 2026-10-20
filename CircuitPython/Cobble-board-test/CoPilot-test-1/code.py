"""
Cobble Board Smoke Test
=======================
Exercises all major features of the Cobble test board:
  - Buzzer (GPIO8 / board.IO8)  – PWM beep
  - Push Button (GPIO9 / board.IO9) – active-low, pull-up
  - NeoPixel (GPIO48 / board.IO48) – RGB LED
  - Light Sensor (GPIO5 / board.A4) – analog read
  - Vibration Sensor (GPIO40 / board.IO40) – active-low, pull-up

Run on: Waveshare ESP32-S3-Zero, CircuitPython 10.3.1
"""

import time
import board
import digitalio
import analogio
import pwmio
import neopixel

# ── Pin setup ────────────────────────────────────────────────────────────────
BUZZER_PIN   = board.IO8
BUTTON_PIN   = board.IO9
NEOPIXEL_PIN = board.IO48
LIGHT_PIN    = board.A4
VIBRATION_PIN = board.IO40

# ── Buzzer ───────────────────────────────────────────────────────────────────
# GPIO8: PWM 50% duty cycle produces sound. NEVER leave high!
# Use a mutable container so beep() can reassign without `global`.
_buzzer = {"pwm": pwmio.PWMOut(BUZZER_PIN, frequency=440, duty_cycle=0)}

def beep(freq=440, duration=0.2, duty=0.5):
    """Emit a beep at the given frequency for the given duration (seconds)."""
    # PWMOut.frequency is read-only on this build – deinit and recreate
    _buzzer["pwm"].deinit()
    _buzzer["pwm"] = pwmio.PWMOut(BUZZER_PIN, frequency=freq, duty_cycle=0)
    _buzzer["pwm"].duty_cycle = int(duty * 65535)
    time.sleep(duration)
    _buzzer["pwm"].duty_cycle = 0  # silence – never leave high

# ── Push Button (active low, pull-up) ─────────────────────────────────────────
button = digitalio.DigitalInOut(BUTTON_PIN)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

def button_pressed():
    """Return True when the button is physically pressed (active low)."""
    return not button.value

# ── NeoPixel (RGB LED) ────────────────────────────────────────────────────────
NUM_PIXELS = 1
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=0.5)

def set_pixel(r, g, b):
    """Set the NeoPixel to an RGB colour (0-255 per channel)."""
    pixels[0] = (r, g, b)
    pixels.show()

# ── Light Sensor (analog) ────────────────────────────────────────────────────
light_sensor = analogio.AnalogIn(LIGHT_PIN)

def read_light():
    """Return the raw analog light value (0-65535)."""
    return light_sensor.value

# ── Vibration Sensor (active low, pull-up) ───────────────────────────────────
vibration = digitalio.DigitalInOut(VIBRATION_PIN)
vibration.direction = digitalio.Direction.INPUT
vibration.pull = digitalio.Pull.UP

def vibration_detected():
    """Return True when vibration is detected (active low)."""
    return not vibration.value

# ═══════════════════════════════════════════════════════════════════════════
#  TEST SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════

print("=== Cobble Board Smoke Test ===\n")

# 1. Buzzer test – three short beeps
print("[1] Buzzer test: 3 beeps at 440 Hz")
for i in range(3):
    beep(440, 0.15)
    time.sleep(0.1)
print("    Buzzer OK\n")

# 2. NeoPixel test – cycle through colours
print("[2] NeoPixel test: colour cycle")
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

# 3. Light sensor test
print("[3] Light sensor test")
raw = read_light()
print(f"    Raw value: {raw} / 65535")
print("    Light sensor OK\n")

# 4. Vibration sensor test
print("[4] Vibration sensor test")
vib = vibration_detected()
print(f"    Vibration detected: {vib}")
print("    Vibration sensor OK\n")

# 5. Button test – wait for press (up to 10 s)
print("[5] Button test: press the button (10 s timeout)")
set_pixel(0, 0, 255)  # blue while waiting
start = time.time()
pressed = False
while time.time() - start < 10:
    if button_pressed():
        pressed = True
        break
    time.sleep(0.05)

if pressed:
    set_pixel(0, 255, 0)  # green on press
    beep(880, 0.1)
    print("    Button pressed – OK")
else:
    set_pixel(255, 0, 0)  # red on timeout
    print("    Button NOT pressed within 10 s")

time.sleep(0.5)
set_pixel(0, 0, 0)

# 6. All-clear
print("\n[6] All-clear: green flash + final beep")
set_pixel(0, 255, 0)
beep(660, 0.3)
time.sleep(0.3)
set_pixel(0, 0, 0)

print("\n=== Smoke test complete ===")
 