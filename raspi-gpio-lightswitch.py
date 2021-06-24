#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2021 by Michael Heise"
__license__ = "LGPL"
__version__ = "0.1.0"
__date__ = "06/22/2021"

"""Configurable python service to run on Raspberry Pi
and evaluate one GPIO-in to toggle one GPIO-out as light switch.
"""

# standard imports
import configparser
import sys
import logging
from systemd.journal import JournalHandler

# 3rd party imports
import RPi.GPIO as GPIO

# local imports

def initGPIO(configGPIO):
    GPIO.setmode(GPIO.BCM)
    
    buttonConfig = configGPIO["Button"].split()
    if buttonConfig[1].lower() == "up":
        pud = GPIO.PUD_UP
    elif buttonConfig[1].lower() == "dn":
        pud = GPIO.PUD_DOWN
    else
        log.error("Invalid resistor configuration! Only 'UP' or 'DN' allowed!")
        sys.exit(-3)
            
    if buttonConfig[2].lower() == "fall":
        edge = GPIO.FALLING
    elif buttonConfig[2].lower() == "rise":
        edge = GPIO.RISING
    else
        log.error("Invalid edge configuration! Only 'RISE' or 'FALL' allowed!")
        sys.exit(-3)
        
    GPIO.setup(buttonConfig[0], GPIO.IN, pull_up_down=pud)
    if buttonConfig.count()=4:
        GPIO.add_event_detect(buttonConfig[0], edge, callback=toggleLight, bouncetime=buttonConfig[3])
    else:
        GPIO.add_event_detect(buttonConfig[0], edge, callback=toggleLight, bouncetime=200)

    lightConfig = configGPIO["Light"]
    GPIO.setup(lightConfig, GPIO.OUT)
    return

def cleanupGPIO():
    GPIO.cleanup()
    return

def switchLight(state):
    lightonoff = state
    GPIO.output(lightConfig, lightonoff)
    return

def toggleLight():
    switchLight(not lightonoff)
    return

CONFIGFILE = "raspi-gpio-lightswitch.conf"

#CRITICAL 50
#ERROR 40
#WARNING 30
#INFO 20
#DEBUG 10
#NOTSET 0

try:
    log = logging.getLogger(__name__)
    log.addHandler(JournalHandler())
    log.setLevel(logging.INFO)
    
    try:
        config = configparser.ConfigParser()
        config.read(CONFIGFILE)
    except Exception as e:
        log.error("Accessing config file '{0}' failed!", CONFIGFILE)
        sys.exit(-2)

    if not config["GPIO"]:
        log.error("Invalid configuration file!")
        sys.exit(-3)

    initGPIO(config["GPIO"])
    
    while True:
        
except Exception as e:
    if log:
        log.exception("Unknown exception occured!")
    sys.exit(-1)
finally:
    if gpio:
        switchLight(False)
        cleanupGPIO()