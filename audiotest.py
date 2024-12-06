# The MIT License (MIT)
# Copyright (c) 2022 Mike Teachman
# https://opensource.org/licenses/MIT
#
# Purpose:  Play a WAV audio file out of a speaker or headphones
#

import os
import time
import machine
from machine import Pin

from wavplayer import WavPlayer
time.sleep_ms(500)

# ======= I2S CONFIGURATION =======
SCK_PIN = 11
WS_PIN = 12
SD_PIN = 13
I2S_ID = 0
BUFFER_LENGTH_IN_BYTES = 40000
# ======= I2S CONFIGURATION =======
wp = WavPlayer(
    id=I2S_ID,
    sck_pin=Pin(SCK_PIN),
    ws_pin=Pin(WS_PIN),
    sd_pin=Pin(SD_PIN),
    ibuf=BUFFER_LENGTH_IN_BYTES,
)
while True:
    print('PLAYING')
    wp.play("audio.start.wav", loop=False)
    # wait until the entire WAV file has been played
    while wp.isplaying() == True:
        # other actions can be done inside this loop during playback
        pass
    time.sleep_ms(500)


