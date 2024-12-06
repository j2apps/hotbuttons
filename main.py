# This code was written for Northwestern University's DTC program by Jonah Kim
# Credit to Professor Michael Peshkin for code regarding microwave power readings
# Credit to Mike Teachman for the I2S audio code

# Imports
import math
import utime
import machine
import neopixel
from wavplayer import WavPlayer

# Give the serial monitor a bit to load
utime.sleep_ms(500)

# Interface Box (DIN8) Pins
microwave_power_pin = machine.ADC(machine.Pin(26, machine.Pin.IN, machine.Pin.PULL_DOWN))
microwave_start_pin = machine.Pin(21, machine.Pin.OUT)
# microwave_30sec_pin = machine.Pin(22, machine.Pin.OUT)
microwave_clear_pin = machine.Pin(19, machine.Pin.OUT)

# Neopixel pin
progress_bar_pin = machine.Pin(16, machine.Pin.OUT)

# Buttons pins
start_button_pin = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_DOWN)
# (time, audio, pin)
foods = [[45, 'f1', 0],
         [60, 'f2', 1],
         [90, 'f3', 2],
         [120, 'f4', 3],
         [390, 'f5', 4]]
# Replace each pin number with a pin object
for food in foods:
    pin = machine.Pin(food[2], machine.Pin.IN, machine.Pin.PULL_DOWN)
    food[2] = pin

# ======= I2S CONFIGURATION =======
SCK_PIN = 11
WS_PIN = 12
SD_PIN = 13
I2S_ID = 0
BUFFER_LENGTH_IN_BYTES = 40000
# ======= I2S CONFIGURATION =======
wp = WavPlayer(
    id=I2S_ID,
    sck_pin=machine.Pin(SCK_PIN),
    ws_pin=machine.Pin(WS_PIN),
    sd_pin=machine.Pin(SD_PIN),
    ibuf=BUFFER_LENGTH_IN_BYTES,
    root="audio"
)

# Constants
counts = 100  # how many 1mS readings to average
threshold = 16400  # higher than this if oven is heating.  
counts2volts = 1.92 / 38500  # this may be weird, why not 3.3/32767 ?
BUTTON_PRESS_TIME = 250 # Time (ms) to keep  signals to the relays of the interface box on HIGH
BUTTON_WAIT_TIME = 250 # Time (ms) to wait to send another signal to the relays of the interface box
CHECK_POWER_DELAY_TIME = 1250 # Time (ms) to wait before checking for microwave power after attempting to start the
# microwave
BUTTON_RESET_TIME = 30  # Start button will not work after this time (s) after pressing a food button
NUM_PIXELS = 8  # Number of LEDs in the Neopixel
PROGRESS_BAR_COLOR = (50, 0, 0)  # Color that each LED in the Neopixel lights up

# Instantiate progress bar
progress_bar = neopixel.NeoPixel(progress_bar_pin, NUM_PIXELS)


# Class used to manage state globally
class State():
    def __init__(self, foods, audios):
        self.foods = foods
        self.audios = audios
        self.currFood = None
        self.power = False
        self.timer = None
        self.progress = 0
        self.playing = False

# Maps keys for audios to audio files stored in the /audio directory
audios = {
    'f1': 'pizza.wav',
    'f2': 'veg.wav',
    'f3': 'starch.wav',
    'f4': 'meat.wav',
    'f5': 'tv.wav',
    'press_start': 'press_start.wav',
    'start': 'starting.wav',
    'cooking': 'cooking_warning.wav',
    'press_food': 'press_food.wav'
}
# Instantiate the state
state = State(foods, audios)


def playAudio(audio: str):
    """
    Plays audio from the file specified in state.audios[audio]
    :param audio:
    :return:
    """
    # If sound is currently playing, stop the current sound and play the new one
    if wp.isplaying():
        wp.stop()
    wp.play(state.audios[audio], loop=False)
    return


def microwaveOff():
    """
    Resets the progress bar
    Press clear twice on the microwave
    :return:
    """
    # Turn microwave off
    for i in range(2):
        microwave_clear_pin.value(1)
        utime.sleep_ms(BUTTON_PRESS_TIME)
        microwave_clear_pin.value(0)
        utime.sleep_ms(BUTTON_WAIT_TIME)

    # Reset progress bar
    resetTimer()
    for i in range(len(progress_bar)):
        progress_bar[i] = (0, 0, 0)
    progress_bar.write()
    state.progress = 0

    # Force state.power to be False temporarily
    state.power = False

    # Deinitialize the progress bar timer
    resetTimer()



def resetTimer():
    """
    Deinitializes the timer if it exists
    :return:
    """
    if isinstance(state.timer, machine.Timer):
        state.timer.deinit()


def progressBarCallback(t):
    """
    A recursive helper callback for the progress bar method
    :return:
    """
    if state.progress >= NUM_PIXELS:
        # If complete, shut off microwave
        microwaveOff()
    else:
        # Increment the progress bar
        progress_bar[state.progress] = PROGRESS_BAR_COLOR
        state.progress += 1
        progress_bar.write()


def startProgressBar(time: float):
    """
    Starts the progress bar with time
    Destroys current timer (food timer)
    Creates new timer for progress bar
    :param time: the total time the progress bar should be counting for
    :return:
    """
    # Turn the first LED on
    progress_bar[0] = PROGRESS_BAR_COLOR
    state.progress = 1
    progress_bar.write()

    # Deinitilize any current timers (food button timers)
    resetTimer()

    # Calculate the interval for each LED to turn on after
    dt = int(time / (NUM_PIXELS - 1))

    # Create the timer
    timer = machine.Timer(-1)
    state.timer = timer
    state.timer.init(mode=machine.Timer.PERIODIC, callback=progressBarCallback, period=dt)


def startMicrowave():
    """
    Looks up food time using foods for the currFood and starts the microwave
    Calls startProgressBar()
    :return:
    """
    # Calculate the number of presses to 30sec necessary and then press 30sec
    num30sec = math.ceil(state.currFood[0] / 30)

    # Press CLEAR twice
    for i in range(2):
        microwave_clear_pin.value(1)
        utime.sleep_ms(BUTTON_PRESS_TIME)
        microwave_clear_pin.value(0)
        utime.sleep_ms(BUTTON_WAIT_TIME)

    # Play audio telling the user that the microwave is attempting to start
    playAudio('start')

    # Press the +30sec button the appropriate number of times
    for i in range(num30sec):
        microwave_start_pin.value(1)
        utime.sleep_ms(BUTTON_PRESS_TIME)
        microwave_start_pin.value(0)
        utime.sleep_ms(BUTTON_WAIT_TIME)

    # Wait for the microwave to power up, then check if it is on
    utime.sleep_ms(CHECK_POWER_DELAY_TIME)
    listenMicrowavePower()

    # If the microwave is on, start the progress bar
    if state.power:
        startProgressBar(1000 * state.currFood[0])
        state.currFood = None

    return


def listenFoodButton():
    """
    listens for any food button that is on
    and sets currFood accordingly

    :return:
    """
    # Check which food buttons are currently being pushed
    on_pins = [food for food in foods if food[2].value() == 1]

    # If none are being pushed, do nothing
    if len(on_pins) == 0:
        return

    # If more than one button is pushed, do nothing
    if len(on_pins) > 1:
        return

    # If the power is on, tell the user and then do nothing
    if state.power:
        playAudio('cooking')
        while wp.isplaying():
            pass
        return

    # Otherwise, store the food button that is being press in food
    food = on_pins[0]

    # Play audio associated with food button
    playAudio(food[1])
    while wp.isplaying():
        pass
    playAudio('press_start')

    # Set the current food
    state.currFood = food

    # Delete the current timer
    if isinstance(state.timer, machine.Timer):
        resetTimer()

    # Create new timer to reset currFood
    def callback(t):
        state.currFood = None
    timer = machine.Timer(-1)
    state.timer = timer
    timer.init(mode=machine.Timer.ONE_SHOT, callback=callback, period=BUTTON_RESET_TIME * 1000)
    utime.sleep_ms(100)
    return


def listenStartButton():
    """
    listens for if the start button is on
    and calls startMicrowave() accordingly

    :return:
    """
    # If the start button is not being pressed, do nothing
    if start_button_pin.value() != 1:
        return

    # If the power is on, tell the user and then do nothing
    if state.power:
        playAudio('cooking')
        return

    # If there is not a food selected, tell the user and then do nothing
    if state.currFood is None:
        playAudio('press_food')
        return

    # Start the microwave and then wait to resume the main loop
    startMicrowave()
    utime.sleep_ms(1000)
    return


def listenMicrowavePower():
    """
    listens for if the microwave power is above a threshold
    and updates state.power accordingly

    :return:
    """
    # Sum the voltage over a time period
    voltsum = 0
    for i in range(counts):  # make a bunch of analog readings
        voltsum = voltsum + microwave_power_pin.read_u16()
        utime.sleep_ms(1)

    # Take the average voltage and check if it clears the threshold
    power = voltsum / counts <= threshold

    # If the microwave was on and now is off, call microwaveOff to stop the progress bar and counting
    if state.power and power:
        microwaveOff()
        pass

    state.power = power


def main():
    while True:
        listenMicrowavePower()
        listenFoodButton()
        listenStartButton()
        utime.sleep_ms(10)


utime.sleep_ms(500)
main()
