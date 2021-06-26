#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2021 by Michael Heise"
__license__ = "LGPL"
__version__ = "0.1.0"
__date__ = "06/25/2021"

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
# - none -

def initLogging():
    """ initialize logging to journal
    """
    global log = logging.getLogger(__name__)
    log_fmt = logging.Formatter("%(levelname)s %(message)s")
    logHandler = JournalHandler()
    logHandler.setFormatter(log_fmt)
    log.addHandler(logHandler)
    log.setLevel(logging.INFO)
    return

def initGPIO(configGPIO):
    """ evaluate the data read from config file to
        set the GPIO input and output
    """
    GPIO.setmode(GPIO.BCM)
    
    log.info("Button configuration = '{0}'".format(configGPIO["Button"]))
        
    buttonConfig = configGPIO["Button"].split(",")
    pudStr = buttonConfig[1].lower()
    if pudStr == "up":
        pud = GPIO.PUD_UP
    elif pudStr == "dn":
        pud = GPIO.PUD_DOWN
    else
        log.error("Invalid resistor configuration! Only 'UP' or 'DN' allowed!")
        return False
            
    edgeStr = buttonConfig[2].lower()
    if edgeStr == "fall":
        edge = GPIO.FALLING
    elif edgeStr == "rise":
        edge = GPIO.RISING
    else
        log.error("Invalid edge configuration! Only 'RISE' or 'FALL' allowed!")
        return False
        
    try:
        if buttonConfig.count()=4:
            bouncetime = int(buttonConfig[3])
        else:
            bouncetime = 200
    except:
        log.error("Invalid bounce time! (only integer >0 allowed)")
        return false

    try:
        GPIO.setup(buttonConfig[0], GPIO.IN, pull_up_down=pud)
        GPIO.add_event_detect(int(buttonConfig[0]), edge, callback=toggleLight, bouncetime=bouncetime)
    except:
        log.error("Error while setting up GPIO input for button!")
        return False

    log.info("Light configuration = '{0}'".format(configGPIO["Light"]))
    
    try:
        lightConfig = int(configGPIO["Light"])
        GPIO.setup(lightConfig, GPIO.OUT)
    except:
        log.info("Error while setting up GPIO output for button!")
        return False
    
    global isValidGPIO = True
    return True

def cleanupGPIO():
    """ clean the used GPIO pins
    """
    if log:
        log.info("Cleaning up GPIO resources.")
    GPIO.cleanup()
    global isValidGPIO = False
    return

def switchLight(state):
    """ switch the output pin to the desired state
    """
    global lightonoff = state
    GPIO.output(lightConfig, lightonoff)
    log.info("Light was set to {0}.".format(getOnOffStr(lightonoff)))
    return

def toggleLight():
    """ toggle the output pin
    """
    log.info("Callback - toggle light output from {0} to {1}...".format(getOnOffStr(lightonoff),
                                                                        getOnOffStr(not lightonoff)))
    switchLight(not lightonoff)
    return

def getOnOffStr(state):
    return "On" if state else "Off"

CONFIGFILE = "raspi-gpio-lightswitch.conf"

#CRITICAL 50
#ERROR 40
#WARNING 30
#INFO 20
#DEBUG 10
#NOTSET 0

try:
    isValidGPIO = False
    
    initLogging()
    
    log.info("Reading configuration file...")
    try:
        config = configparser.ConfigParser()
        config.read(CONFIGFILE)
    except Exception as e:
        log.error("Accessing config file '{0}' failed!", CONFIGFILE)
        sys.exit(-2)

    if not config["GPIO"]:
        log.error("Invalid configuration file! (No [GPIO] section)")
        sys.exit(-3)

    log.info("Init GPIO configuration:")
    if not initGPIO(config["GPIO"]):
        sys.exit(-3)
    
    log.info("Setting defined inital off state.")
    switchLight(False)
    
    log.info("Starting service loop...")
    while True:
        
except Exception as e:
    if log:
        log.exception("Unhandled exception: {0}".format(e.args[0]))
    sys.exit(-1)
finally:
    if isValidGPIO:
        if log:
            log.info("Finally setting output to off state.")
        switchLight(False)
    cleanupGPIO()