# Cobble smoke test board - sensor exercise script
#
# On startup: plays "Twinkle Twinkle Little Star" on the buzzer.
# In the loop:
#   - Prints light sensor (analog + digital), vibration, and button readings.
#   - Scans the I2C bus and prints any connected devices.
#   - Push button (active low): NeoPixel changes to a random color.

import board
import busio
import time
import random
import pwmio
import analogio
import digitalio
import neopixel

# --- Pin setup (from README pin mapping) ---
LIGHT_ANALOG_PIN = board.A4      # ADC1_CH4 analog light reading
LIGHT_DIGITAL_PIN = board.IO39    # digital-only light input, no pull
VIBRATION_PIN = board.IO40        # input pull-up, active low
BUTTON_PIN = board.IO9            # input pull-up, active low
BUZZER_PIN = board.IO8            # output, never leave high
NEOPIXEL_PIN = board.IO48

i2c = busio.I2C(board.IO6, board.IO7)  # SCL, SDA for J3/J4 connectors

# NeoPixel: 1 pixel, brightness 0.5
PIXEL_COUNT = 1
neopixel = neopixel.NeoPixel(NEOPIXEL_PIN, PIXEL_COUNT, brightness=0.5)

# Buzzer: PWM output, driven low when not sounding
buzzer_pwm = pwmio.PWMOut(BUZZER_PIN, frequency=1000, duty_cycle=0)

# Light sensors
light_analog = analogio.AnalogIn(LIGHT_ANALOG_PIN)
light_digital = digitalio.DigitalInOut(LIGHT_DIGITAL_PIN)
light_digital.direction = digitalio.Direction.INPUT  # no pull

# Vibration: input with pull-up, active low
vibration = digitalio.DigitalInOut(VIBRATION_PIN)
vibration.direction = digitalio.Direction.INPUT
vibration.pull = digitalio.Pull.UP

# Push button: input with pull-up, active low
button = digitalio.DigitalInOut(BUTTON_PIN)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# --- Song: Super Mario Bros theme (opening) ---
NOTES = {
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46,
    'G5': 783.99, 'A5': 880.00, 'B5': 987.77, 'C6': 1046.50,
    'E4': 329.63, 'G4': 392.00, 'C4': 261.63
}
TEMPO = 180  # beats per minute
BEAT = 60.0 / TEMPO

# (note, duration in beats) — 'R' = rest
MEL = [
    # Bounce: C C G C E G
    ('E5', 0.25), ('E5', 0.5), ('E5', 0.5), ('C5', 0.25), ('E5', 0.5), ('G5', 1), ('G4', 1),
]


def play_song():
    """Play the melody on the buzzer using PWM square wave."""
    print("Playing startup song...")
    global buzzer_pwm
    for note, beats in MEL:
        freq = NOTES[note]
        duration = beats * BEAT
        buzzer_pwm.deinit()
        buzzer_pwm = pwmio.PWMOut(BUZZER_PIN, frequency=int(freq / 2), duty_cycle=0x8000)
        time.sleep(duration)
        buzzer_pwm.deinit()
        time.sleep(0.02)
    buzzer_pwm = pwmio.PWMOut(BUZZER_PIN, frequency=1000, duty_cycle=0)


def random_neopixel_color():
    """Set the NeoPixel to a random RGB color."""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    neopixel[0] = (r, g, b)
    print(f"  NeoPixel -> ({r}, {g}, {b})")


def scan_i2c():
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


# --- Startup ---
print("Cobble board test starting")
neopixel.fill((0, 0, 0))
time.sleep(0.5)
play_song()
neopixel.fill((50, 50, 50))  # dim white to confirm pixel is alive

print("Song done. Press button for random NeoPixel color.")
print("Reading sensors every 2 seconds.\n")

# --- Main loop ---
while True:
    # Light sensor
    light_val = light_analog.value
    print(f"Light (analog): {light_val})")

    # Vibration sensor
    vib = not vibration.value  # active low, so True = vibrating
    if vib:
        print("  VIBRATION DETECTED")

    # I2C scan
    i2c_devs = scan_i2c()
    if i2c_devs:
        addrs = ", ".join(f"0x{a:02X}" for a in i2c_devs)
        print(f"  I2C devices: {addrs}")

    # Button: on press, set NeoPixel to random color
    if not button.value:  # active low
        random_neopixel_color()
        # Debounce: wait for release
        while not button.value:
            time.sleep(0.05)
        time.sleep(0.2)

    time.sleep(0.2)
