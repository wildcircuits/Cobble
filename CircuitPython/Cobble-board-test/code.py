print("Hello World!")

import time
import board
import pwmio
import digitalio
import countio
import analogio
import neopixel


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

# Set up GPIO7 with variable frequency enabled so we can change pitch on the fly
piezo = pwmio.PWMOut(board.IO8, frequency=440, duty_cycle=0, variable_frequency=True)

# Initialize GPIO9 as a digital input with an internal pull-up resistor
button = digitalio.DigitalInOut(board.IO9)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

wrongADC = digitalio.DigitalInOut(board.IO39)
wrongADC.direction = digitalio.Direction.INPUT

# Initialize GPIO9 as a digital input with an internal pull-up resistor
# vibe = digitalio.DigitalInOut(board.IO40)
# vibe.direction = digitalio.Direction.INPUT
# vibe.pull = digitalio.Pull.UP

# Initialize GPIO40 hardware pulse counter with pull-up (Vibration Sensor)
# Catches falling-edge triggers in hardware even during delays
vibe_counter = countio.Counter(board.IO40, edge=countio.Edge.FALL, pull=digitalio.Pull.UP)

# Analog light sensor on IO39 (analog pins use board.A0, not IO39)
light = analogio.AnalogIn(board.A4)


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

def startup_song():
    # Loop through each note in the octave scale
    for freq in OCTAVE_NOTES:
        piezo.frequency = freq
        piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
        time.sleep(0.1)           # Play note for 0.1s
    
    for freq in OCTAVE_NOTES:
        piezo.frequency = freq * 2
        piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
        time.sleep(0.1)           # Play note for 0.1s
        
    for freq in OCTAVE_NOTES:
        piezo.frequency = freq * 4
        piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
        time.sleep(0.1)     
    
    # Mute tone and clean up hardware resource
    piezo.duty_cycle = 0


def beep_click():
    f1 = OCTAVE_NOTES[0]
    f2 = OCTAVE_NOTES[1]    

    piezo.frequency = f1
    piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
    time.sleep(0.1)   

    piezo.frequency = f2
    piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
    time.sleep(0.1)   

    piezo.duty_cycle = 0

def beep_unclick():
    f2 = OCTAVE_NOTES[0]
    f1 = OCTAVE_NOTES[1]    

    piezo.frequency = f1
    piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
    time.sleep(0.1)   

    piezo.frequency = f2
    piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
    time.sleep(0.1)   

    piezo.duty_cycle = 0

def beep_vibe():
    piezo.frequency = OCTAVE_NOTES[4]
    piezo.duty_cycle = 32768  # Start tone (50% duty cycle)
    time.sleep(0.1) 
    piezo.duty_cycle = 0  

pressed = True
startup_song()
while True:
    # Fade the NeoPixel across the rainbow every loop
    rainbow()

    # Report light sensor reading each iteration (0-65535)
    print(f"Light: {light.value}")

    # 1. Check for hardware vibration interrupts
    if vibe_counter.count > 0:
        print(f"Vibration Detected! Pulses: {vibe_counter.count}")
        vibe_counter.reset()  # Clear pulse counter
        beep_vibe()

        # The speaker vibrates the board enough that the vibration sensor detects it
        # This delay is long enough that any vibrations from the speaker can be cleared before continuing
        time.sleep(0.2) # this 
        vibe_counter.reset()  # Clear pulse counter

    # With a pull-up resistor, the logic is inverted:
    # False (LOW)  = Button pressed (connected to GND)
    # True (HIGH)  = Button released (pulled up to 3.3V)
    if not button.value:
        print("Button pressed!") 
    
    if not button.value:
        if pressed:
            pressed = False
            beep_click()
    else:
        if not pressed:
            pressed = True
            beep_unclick()
            
    
    time.sleep(0.1)