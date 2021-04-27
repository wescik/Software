import RPi.GPIO as GPIO
import spidev # To communicate with SPI devices
from numpy import interp    # To scale values
# import math


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


'''
Drivers outputs assignments

      CH1    CH2    CH3    CH4    CH5    CH6
C1    23     7      19     17     24     12
C2    27     25     6      22     5      16
PWM   18            13

Other digital signals assignments
DC ENABLE: 21
JOY1_DIG_IO: 20
JOY2_DIG_IO: 26
JOY3_DIG_IO: 4 

Communication interfaces assignments
UART: Tx: 14, Rx: 15
SPI: MISO: 9 , MOSI: 10, SCK: 11, ADC nSS: 8 (SPI0, CE0)
IIC: SDA: 2, SCL: 3

ADC channels assignments
Vbat: CH1
Ibat: (CH0-CH1) * 10 // Shunt resistor is 0R1
JOY1_X: CH2
JOY1_Y: CH3
JOY2_X: CH4
JOY2_Y: CH5
JOY3_X: CH6
JOY3_Y: CH7

'''

driver_ctrl_pins = (23, 27, 7, 25, 19, 6, 17, 22, 24, 5, 12, 16)
pwm_ctrl_pins = (18, 13)
conv_en_pin = 21
digital_gpio_pins = (20, 26, 4)
#gpio_fn = ('IN', 'IN', 'IN')
CH1_pins = (driver_ctrl_pins[0], driver_ctrl_pins[1])
CH2_pins = (driver_ctrl_pins[2], driver_ctrl_pins[3])
CH3_pins = (driver_ctrl_pins[4], driver_ctrl_pins[5])
CH4_pins = (driver_ctrl_pins[6], driver_ctrl_pins[7])
CH5_pins = (driver_ctrl_pins[8], driver_ctrl_pins[9])
CH6_pins = (driver_ctrl_pins[10], driver_ctrl_pins[11])
rotation_CW = (0,1)
rotation_CCW = (1,0)
rotation_stop = (0,0)


# Create PWM objects for motor control
GPIO.setup(pwm_ctrl_pins, GPIO.OUT, initial=GPIO.LOW)
CH1_PWM = GPIO.PWM(pwm_ctrl_pins[0], 1000)
CH3_PWM = GPIO.PWM(pwm_ctrl_pins[1], 1000)

# Create a SPI object for ADC transfers handling
spi = spidev.SpiDev()


def Analog_IN_Init():
    spi.open(0,0)
    spi.max_speed_hz = 1350000
    return 'OK'

def GPIO_Init(io1 = 'IN', io2 = 'IN', io3 = 'IN'):
    global gpio_fn
    temp_gpio_fn = ['IN', 'IN', 'IN']
    if io1 == 'OUT':
        GPIO.setup(digital_gpio_pins[0], GPIO.OUT, initial=GPIO.LOW)
        temp_gpio_fn[0] = 'OUT'
    else:
        GPIO.setup(digital_gpio_pins[0], GPIO.IN)
    if io2 == 'OUT':
        GPIO.setup(digital_gpio_pins[1], GPIO.OUT, initial=GPIO.LOW)
        temp_gpio_fn[1] = 'OUT'
    else:
        GPIO.setup(digital_gpio_pins[1], GPIO.IN)
    if io3 == 'OUT':
        GPIO.setup(digital_gpio_pins[2], GPIO.OUT, initial=GPIO.LOW)
        temp_gpio_fn[2] = 'OUT'
    else:
        GPIO.setup(digital_gpio_pins[2], GPIO.IN)
    gpio_fn = tuple(temp_gpio_fn)
    return 'OK'

def Joy_GPIO_Read(joy_no):
    x = joy_no - 1
    if gpio_fn[x] == 'IN':
        return ('HIGH' if GPIO.input(digital_gpio_pins[x]) == 1 else 'LOW')
    else:
        return 'NOK'
    
def Joy_Axis_Digital_Read(joy_no, axis):
    if joy_no < 1 or joy_no > 3:
        return 'NOK'
    channel = joy_no * 2
    if axis == 'Y':
        channel += 1
    elif axis != 'X':
        return 'NOK'
    value = _RAW_ADC_Value(channel)
    if value < 248:
        return 'LOW'
    elif value > 620:
        return 'HIGH'
    else:
        return 'MAYBE'



def Joy_GPIO_Set(joy_no, state):
    x = joy_no - 1
    if gpio_fn[x] == 'OUT':
        GPIO.output(digital_gpio_pins[x], state)
        return ('HIGH' if state else 'LOW')
    else:
        return 'NOK'

# Read MCP3008 data
def _RAW_ADC_Value(channel):
    adc = spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data

def Batt_Voltage():
    voltage = round(interp(_RAW_ADC_Value(1), [0, 1023], [0, 10]), 2)
    return voltage
    
# useless sh#t - current is almost allways too small for reasonable masurement
def Batt_Current():
    current = round((interp(_RAW_ADC_Value(1), [0, 1023], [0, 10]) - interp(_RAW_ADC_Value(0), [0, 1023], [0, 10])) * 10, 3)
    return current

def Joy_Axis(joy_no, axis):
    if joy_no < 1 or joy_no > 3:
        return 'NOK'
    channel = joy_no * 2
    if axis == 'Y':
        channel += 1
    elif axis != 'X':
        return 'NOK'
    value = round(interp(_RAW_ADC_Value(channel), [0, 1023], [-100, 100]), 0)
    return value

def Potentiometer_Value(joy_no, axis):
    if joy_no < 1 or joy_no > 3:
        return 'NOK'
    channel = joy_no * 2
    if axis == 'Y':
        channel += 1
    elif axis != 'X':
        return 'NOK'
    value = round(interp(_RAW_ADC_Value(channel), [0, 1023], [0, 100]), 0)
    return value    

def Drivers_Init():
    # Setup all the control pins as digital output and set them to LO
    GPIO.setup(conv_en_pin, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(driver_ctrl_pins, GPIO.OUT, initial=GPIO.LOW)
    # Switch off PWMs
    CH1_PWM.stop()
    CH3_PWM.stop()
    return 'OK'
	
def DC_Converter_Enable(newstate):
    GPIO.output(conv_en_pin, (1 if bool(newstate) else 0))
    return 'OK'


def Motor_CW(channel, pwm = 100):
    if pwm < 0:
        pwm = 0
    if pwm > 100:
        pwm = 100
    if channel == 1:
        GPIO.output(CH1_pins, rotation_CW)
        CH1_PWM.start(pwm)
    elif channel == 2:
        GPIO.output(CH2_pins, rotation_CW)
    elif channel == 3:
        GPIO.output(CH3_pins, rotation_CW)
        CH3_PWM.start(pwm)
    elif channel == 4:
        GPIO.output(CH4_pins, rotation_CW)
    elif channel == 5:
        GPIO.output(CH5_pins, rotation_CW)
    elif channel == 6:
        GPIO.output(CH6_pins, rotation_CW)
    else:
        return 'NOK'
    return 'OK'

def Motor_CCW(channel, pwm = 100):
    if pwm < 0:
        pwm = 0
    if pwm > 100:
        pwm = 100
    if channel == 1:
        GPIO.output(CH1_pins, rotation_CCW)
        CH1_PWM.start(pwm)
    elif channel == 2:
        GPIO.output(CH2_pins, rotation_CCW)
    elif channel == 3:
        GPIO.output(CH3_pins, rotation_CCW)
        CH3_PWM.start(pwm)
    elif channel == 4:
        GPIO.output(CH4_pins, rotation_CCW)
    elif channel == 5:
        GPIO.output(CH5_pins, rotation_CCW)
    elif channel == 6:
        GPIO.output(CH6_pins, rotation_CCW)
    else:
        return 'NOK'
    return 'OK'
        
def Motor_stop(channel):
    if channel == 1:
        GPIO.output(CH1_pins, rotation_stop)
        CH1_PWM.stop()
    elif channel == 2:
        GPIO.output(CH2_pins, rotation_stop)
    elif channel == 3:
        GPIO.output(CH3_pins, rotation_stop)
        CH3_PWM.stop()
    elif channel == 4:
        GPIO.output(CH4_pins, rotation_stop)
    elif channel == 5:
        GPIO.output(CH5_pins, rotation_stop)
    elif channel == 6:
        GPIO.output(CH6_pins, rotation_stop)
    elif channel == 'all':   # NOTICE - this has effect also on EACH output of drivers PCB
        GPIO.output(driver_ctrl_pins, 0)
        CH1_PWM.stop()
        CH3_PWM.stop()
    else:
        return 'NOK'
    return 'OK'

def LED_ON(channel):
    return Motor_CCW(channel)
	
def LED_OFF(channel):
    if channel == 1:
        GPIO.output(CH1_pins, rotation_CW)
        CH1_PWM.stop()
    elif channel == 2:
        GPIO.output(CH2_pins, rotation_CW)
    elif channel == 3:
        GPIO.output(CH3_pins, rotation_CW)
        CH3_PWM.stop()
    elif channel == 4:
        GPIO.output(CH4_pins, rotation_CW)
    elif channel == 5:
        GPIO.output(CH5_pins, rotation_CW)
    elif channel == 6:
        GPIO.output(CH6_pins, rotation_CW)
    else:
        return 'NOK'
    return 'OK'
	
def Signal_Light(channel, color):
    if color == 'green':
        col = (0,1)
    elif color == 'red_yellow':
        col = (1,0)
    elif color == 'red':
        col = (0,0)
    elif color == 'yellow':
        col = (1,1)
    else:
        return 'NOK'
    
    if channel == 1:
        GPIO.output(CH1_pins, col)
        CH1_PWM.start(100)
    elif channel == 2:
        GPIO.output(CH2_pins, col)
    elif channel == 3:
        GPIO.output(CH3_pins, col)
        CH3_PWM.start(100)
    elif channel == 4:
        GPIO.output(CH4_pins, col)
    elif channel == 5:
        GPIO.output(CH5_pins, col)
    elif channel == 6:
        GPIO.output(CH6_pins, col)
    else:
        return 'NOK'
    return 'OK'