import time
import board
import pulseio
import displayio
import math
import array
import digitalio
import adafruit_touchscreen
from audioio import AudioOut
from audiocore import RawSample
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_button import Button
from adafruit_display_shapes.triangle import Triangle

######### Hardware Constants ###########
CW_IS_HIGH = True        # constant to determine CW/CCW rotation of motor w.r.t DIR pin
MM_PER_ROTATION = 1.00   # constant for calibrating the stereotax

######### Initialise hardware ##########
display = board.DISPLAY
# Touchscreen setup
# -------Rotate 0:
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240), samples=4)

# Create PWM object but leave the duty cycle on zero so no movement occurs
pwm = pulseio.PWMOut(board.D4, duty_cycle=0, frequency=3200, variable_frequency=True)
audio = AudioOut(board.SPEAKER) 
direction_pin = digitalio.DigitalInOut(board.D3)
direction_pin.switch_to_output()

def generate_beep(frequency, duration, volume=1):
    samplerate = 8000
    length = int(samplerate * duration)  # samples
    sine_wave = array.array("H", [0] * length)
    for i in range(length):
        sine_wave[i] = int((1 + math.sin(math.pi * 2 * i * frequency / samplerate)) * volume * (2 ** 15 - 1))
    return RawSample(sine_wave)

short_beep = generate_beep(2600, 0.025, volume = 0.2)
long_beep = generate_beep(2400, 0.1, volume = 0.2)
very_long_beep = generate_beep(2400, 0.5, volume = 0.2)

def play_beep(length = 0):
    if length == 2:
        audio.play(very_long_beep)
    elif length == 1:
        audio.play(long_beep)
        while audio.playing:
            pass
        audio.play(short_beep)
    else:
        audio.play(short_beep)


############# Splash screen startup ##########
image_file = open("SWC_logo_320.bmp", "rb")
bitmap_contents = displayio.OnDiskBitmap(image_file)

splash_screen = displayio.TileGrid(
    bitmap_contents,
    pixel_shader=displayio.ColorConverter(),
    default_tile=0,
    x=0,  # Position relative to its parent group
    y=0,
    width=1,  # Number of tiles in the grid
    height=1,
)

display.brightness = 0.0
splash_group = displayio.Group(max_size=2)
splash_group.append(splash_screen)
display.show(splash_group)
for i in range(0,100):
    display.brightness = i/100
    time.sleep(0.01)

font_large = bitmap_font.load_font('/fonts/32-Terminus-Bold.bdf')
splash_group.append(label.Label(font_large, text="Loading...", x=80, y=200, color=0x000000))
font = bitmap_font.load_font('/fonts/24-Terminus.bdf')


############### Main UI ##############
button_enabled_colour = 0x505050
button_disabled_colour = 0x000000
maingroup = displayio.Group(max_size=12)
rowy = 0
maingroup.append(label.Label(font, text="Speed (mm/h)", x=2, y=rowy+8, max_glyphs=12))
maingroup.append(label.Label(font, text="Target (μm)", x=162, y=rowy+8, max_glyphs=13))
speedbutton = Button(x=0, y=rowy+25, width=158, height=60, name='speed',
                     label="01234.567", label_font=font_large, style=Button.SHADOWROUNDRECT,
                     fill_color=button_enabled_colour, label_color=0xFFFFFF, outline_color=0xFFFFFF)
targetbutton = Button(x=160, y=rowy+25, width=159, height=60, name='target',
                        label="5000", label_font=font_large, style=Button.SHADOWROUNDRECT,
                      fill_color=button_enabled_colour, label_color=0xFFFFFF, outline_color=0xFFFFFF)
maingroup.append(speedbutton)
maingroup.append(targetbutton)

rowy = 85
maingroup.append(label.Label(font, text="Time (min:s)", x=2, y=rowy+8, max_glyphs=13))
maingroup.append(label.Label(font, text="Position (μm)", x=160, y=rowy+8, max_glyphs=13))
timebutton = Button(x=0, y=rowy+25, width=158, height=60, label="0090:00", name='time', label_font = font_large, style=Button.ROUNDRECT,
                    fill_color=button_disabled_colour, label_color=0xFFFFFF, outline_color=0xFFFFFF)
posbutton = Button(x=160, y=rowy+25, width=159, height=60, label="0000", name='position', label_font = font_large, style=Button.SHADOWROUNDRECT,
                   fill_color=button_enabled_colour, label_color=0xFFFFFF, outline_color=0xFFFFFF)
maingroup.append(timebutton)
maingroup.append(posbutton)

startbutton = Button(x=0,y=180,height=60,width=159, name='start', 
                    label="Start", label_font = font_large, style=Button.SHADOWROUNDRECT,
                     fill_color=0x00D000, outline_color=0x606060)
stopbutton = Button(x=160,y=180,height=60,width=159, name='stop',
                    label="Stop", label_font = font_large, style=Button.SHADOWROUNDRECT,
                    fill_color=0xD00000, outline_color=0x606060)
maingroup.append(startbutton)
maingroup.append(stopbutton)

############# Editor UI #################
editgroup = displayio.Group(max_size=24)
edit_title = label.Label(font, text="Target position:", x=2, y=8, max_glyphs=22)
edit_value_label = label.Label(font, text="5.000",x=160, y=8, max_glyphs=18)
editgroup.append(edit_title)
editgroup.append(edit_value_label)
digits = []
for i in range(4):
    btn = Button(x=25+70*i, y=30, width=60, name='up%s' % i, 
                 height=60, style=Button.ROUNDRECT,
                 fill_color=0x000000, outline_color=0xFFFFFF)
    editgroup.append(btn)
    editgroup.append(Triangle(btn.x+btn.width//2, btn.y+btn.height//4, 
                                btn.x+btn.width//4, btn.y+btn.height//4*3,
                                btn.x+btn.width//4*3, btn.y+btn.height//4*3,
                                fill=0x00D0D0))
    digit = label.Label(font_large, text = "0", x=btn.x+btn.width//2 - 8, y=btn.y+btn.height+10)
    digits.append(digit) 
    editgroup.append(digit)
    btn = Button(x=25+70*i, y=125, width=60, name='dn%s' % i,
                 height=60, style=Button.ROUNDRECT,
                 fill_color=0x000000, outline_color=0xFFFFFF)
    editgroup.append(btn)
    editgroup.append(Triangle(btn.x+btn.width//2, btn.y+btn.height//4*3,
                              btn.x+btn.width//4, btn.y+btn.height//4,
                              btn.x+btn.width//4*3, btn.y+btn.height//4,
                              fill=0x00D0D0))
miscbutton = Button(x=25, y=190, height=50, width=130, label="Reset", name='misc', label_font=font_large, style=Button.ROUNDRECT,
                    fill_color=0xD00000, label_color=0xFFFFFF, outline_color=0xFFFFFF)
editgroup.append(miscbutton)
editgroup.append(Button(x=165, y=190, height=50, width=130, label="Done", name='done', label_font=font_large, style=Button.ROUNDRECT,
                    fill_color=0x303030, label_color=0xFFFFFF, outline_color=0xFFFFFF))

############# End of UI code #############

class App(): # global variables and default values
    view = 'main'
    editing_param = None
    activebutton = None
    default_speed_hz = 3
    speed_hz = 3
    _speed_mm_hour = 0
    target_um = 5000
    previous_target = None
    previous_speed = None
    position_um = 0
    motor_running = False
    motor_start_time = 0 
    motor_start_pos = 0
    motor_reverse = False
    is_homing = False


def calc_speed_from_hz():
    app._speed_mm_hour = app.speed_hz * 1.125 * MM_PER_ROTATION
    # this is because: 16 pulses per step, 200 steps/rev = 3200 pulses per rev
    # Revs per hour = F pulses per second * 3600 seconds per hour / 3200 pulses per rev

def load_value_into_digits(val):
    valstr = '%04d' % int(val)
    for i in range(4):
        digits[i].text = valstr[i]

def read_value_from_digits():
    valstr = "".join([digit.text for digit in digits])
    return int(valstr)

def start_editing(param):
    app.view = 'edit'
    app.editing_param = param
    if param == 'speed':
        miscbutton.label = 'Reset'
        edit_title.text = "Speed:"
        load_value_into_digits(app.speed_hz)
        # update_speed_string()
    elif param == 'target':
        miscbutton.label = 'Go home'
        edit_title.text = "Target pos:"
        load_value_into_digits(app.target_um)
    elif param == 'position':
        edit_title.text = "Current pos:"
        miscbutton.label = 'Zero'
        load_value_into_digits(app.position_um)
    refresh_editor()
    display.show(editgroup)
    time.sleep(0.1)

def refresh_editor():
    value = read_value_from_digits()
    if app.editing_param == 'speed':
        app.speed_hz = max(value, 1) # prevent user setting speed to 0
        calc_speed_from_hz()
        edit_value_label.text = "%s mm/hr" % round(app._speed_mm_hour, 3)
        # update_speed_string()
    elif app.editing_param == 'target':
        app.target_um = value
        edit_value_label.text = "%s μm" % app.target_um
    elif app.editing_param == 'position':
        app.position_um = value
        edit_value_label.text = "%s μm" % app.position_um

    
def stop_editing():
    app.view = 'main'
    display.show(maingroup)
    time.sleep(0.1)

def editor_change_digit(idx, increment):
    val = int(digits[idx].text) + increment
    val = min(max(val, 0),9) # constrain this digit
    digits[idx].text = str(val)
    refresh_editor()

def refresh():
    calc_speed_from_hz()
    # calculate the position (if motor is running)
    if app.motor_running:
        speed_um_per_second = app._speed_mm_hour / 3.6
        if app.motor_reverse:
            speed_um_per_second = -1 * speed_um_per_second
        app.position_um = app.motor_start_pos + speed_um_per_second * (time.monotonic() - app.motor_start_time)
        if (app.position_um >= app.target_um) != app.motor_reverse:
            ## We have reached the target.
            stop_motor()
            play_beep(2)
    pos_string = "%04d" % app.position_um
    # calculate the time remaining
    seconds_remaining = int(3.6 * abs(app.target_um - app.position_um) / app._speed_mm_hour)
    time_string = "%02d:%02d" % divmod(seconds_remaining, 60)
    # update button labels if the underlying value has changed
    speed_string = "-%0.2f" if app.motor_reverse else "%0.2f"
    speed_string = speed_string % app._speed_mm_hour
    if speedbutton.label != speed_string:
        speedbutton.label = speed_string
    if targetbutton.label != str(app.target_um):
        targetbutton.label = str(app.target_um)
    if posbutton.label != pos_string:
        posbutton.label = pos_string
    if timebutton.label != time_string:
        timebutton._label.text = time_string


def start_motor():
    pwm.frequency = app.speed_hz
    app.motor_reverse = app.position_um > app.target_um
    direction_pin.value = app.motor_reverse != CW_IS_HIGH # set the direction pin
    print("Motor speed %s direction %d" % (app.speed_hz, direction_pin.value))
    pwm.duty_cycle = 16384  # start the motor
    app.motor_running = True
    app.motor_start_time = time.monotonic()
    app.motor_start_pos = app.position_um
    speedbutton.body.fill = button_disabled_colour
    posbutton.body.fill = button_disabled_colour
    targetbutton.body.fill = button_disabled_colour
    startbutton.body.fill = button_disabled_colour
    startbutton._label.color = 0x333333   

def stop_motor():
    pwm.duty_cycle = 0  # stop the motor
    app.motor_running = False
    if app.is_homing:
        stop_homing()
    print("Stopped.")
    speedbutton.body.fill = button_enabled_colour
    posbutton.body.fill = button_enabled_colour
    targetbutton.body.fill = button_enabled_colour
    startbutton.body.fill = 0x00D000
    startbutton._label.color = 0x000000

def start_homing():
    print("Going home")
    # store current settings
    app.previous_speed = app.speed_hz
    app.previous_target = app.target_um
    # target the zero position, and set a high speed
    app.speed_hz = 1500
    app.target_um = 0
    app.is_homing = True
    start_motor()
    # startbutton.label = "Go home"

def stop_homing():
    print("Stop homing")
    # restore previous target and speed, for the next run
    app.target_um = app.previous_target
    app.speed_hz = app.previous_speed
    app.is_homing = False
    # startbutton.label = "Start"

# Prepare for launch
app = App()
calc_speed_from_hz()
display.show(maingroup)
############# MAIN LOOP ###############
while True:
    if app.view == 'main':
        refresh()
    p = ts.touch_point
    if p: # Screen was touched
        if app.view == 'main':
            for item in maingroup:
                if type(item)==Button: # was a button pressed?
                    if item.contains(p) and (item.name != 'time'):
                        if app.motor_running == (item.name == 'stop'):
                            item.selected = True
                            app.activebutton = item
                    else:
                        item.selected = False
        elif app.view == 'edit':
            for item in editgroup:
                if type(item)==Button: # was a button pressed?
                    if item.contains(p):
                        item.selected = True
                        app.activebutton = item
                    else:
                        item.selected = False
    else:
        if app.activebutton: # a button was released. Do an action.
            action = app.activebutton.name
            app.activebutton.selected = False
            app.activebutton=None
            # print(action)
            if not app.motor_running:
                if action == 'start':
                    play_beep(1)
                    start_motor()
                elif action in ['speed', 'target', 'position']:
                    play_beep()
                    start_editing(action)
                elif action == 'done':
                    play_beep(1)
                    stop_editing()
                elif action == 'misc':
                    if app.editing_param == 'speed':
                        # reset speed
                        play_beep()
                        app.speed_hz = app.default_speed_hz
                        stop_editing()
                    elif app.editing_param == 'position':
                        # set current position to zero
                        app.position_um = 0
                        play_beep(1)
                        stop_editing()
                    elif app.editing_param == 'target':
                        play_beep(1)
                        stop_editing()
                        start_homing()
                elif action.startswith('up'):
                    play_beep()
                    editor_change_digit(int(action[2]), 1)
                elif action.startswith('dn'):
                    play_beep()
                    editor_change_digit(int(action[2]), -1)
            else:
                if action == 'stop':
                    stop_motor()
                    play_beep(2)



 
