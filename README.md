# Cobble Hardware Design

## ESP32S3-supermini Pinout
![alt text](resources/diagram-3200.png)
Link: https://www.espboards.dev/esp32/esp32-s3-super-mini/

## Cobble-board-test
the Cobble-board-test/ folder contains the single layer layout design used for the cobble smoke test board.  

### Pin mapping
| ESP32-S3-super-mini Pin | Function | Notes |
| --- | --- | --- |
| GPIO5 / ADC1_CH4 | Light Sensor | Read analog value for representative light level measurements |
| GPIO39 | Light Sensor | this pin is digital only and should be set to input no pull up/down |
| GPIO40 | Vibration Sensor | configure pin as input with pull up.  vibration will be active low |
| GPIO9 | PushButton | configure pin as input with pull up.  PushButton will be active low |
| GPIO10 | Buzzer | **Never leave high!**.  set as output low when not in use.  drive with PWM 50% duty cycle to create sound |
| GPIO6 | SCL | Use for I2C communications with device on J3 Stemma or J4 Grove connectors |
| GPIO7 | SDA | Use for I2C communications with devices on J3 Stemma or J4 Grove connectors |

### Design notes
Note about 5V Power:
- When USB is connected this will be 5V from VBUS
- When running from a battery this will be Vbatt-V_protection_diode
- Battery can only charge when USB is connected and power switch is 'ON'

