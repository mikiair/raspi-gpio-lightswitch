#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2021 by Michael Heise"
__license__ = "LGPL"
__version__ = "0.2.1"
__date__ = "06/29/2021"

"""Configurable python service to run on Raspberry Pi
   and evaluate one GPIO-in to toggle one GPIO-out as light switch.
"""

# standard imports
import configparser
import sys
import logging
from systemd.journal import JournalHandler

# 3rd party imports
import gpiozero

# local imports
# - none -


class RaspiGPIOLightSwitch:
    def __init__(self):
        self._isValidGPIO = False
        self.CONFIGFILE = "raspi-gpio-lightswitch.conf"
        self.valuesUpDn = ["up", "dn", "upex", "dnex"]
        self.valuesPressRelease = ["press", "release"]
        self.config = None

    def initLogging(log):
        """initialize logging to journal"""
        log_fmt = logging.Formatter("%(levelname)s %(message)s")
        logHandler = JournalHandler()
        logHandler.setFormatter(log_fmt)
        log.addHandler(logHandler)
        log.setLevel(logging.INFO)
        return

    def readConfigFile():
        """read the config file"""
        try:
            self.config = configparser.ConfigParser()
            self.config.read(self.CONFIGFILE)
            return True
        except Exception:
            log.error("Accessing config file '{0}' failed!", CONFIGFILE)
            return False

    def initGPIO():
        """evaluate the data read from config file to
        set the GPIO input and output
        """
        configGPIO = self.config["GPIO"]

        log.info("Button configuration = '{0}'".format(configGPIO["Button"]))

        buttonConfig = configGPIO["Button"].split(",")

        pudStr = buttonConfig[1].lower()
        if not pudStr in valuesUpDn:
            log.error("Invalid resistor configuration! Only 'UP' or 'DN' allowed!")
            return False

        pud = None
        active = None
        if pudStr == "up":
            pud = True
        if pudStr == "dn":
            pud = False
        if pudStr == "upex":
            active = False
        if pudStr == "dnex":
            active = True

        eventStr = buttonConfig[2].lower()
        if not eventStr in valuesPressRelease:
            log.error("Invalid event configuration! Only 'PRESS' or 'RELEASE' allowed!")
            return False

        event = True if eventStr == "press" else False

        try:
            if len(buttonConfig) == 4:
                bouncetime = int(buttonConfig[3])
            else:
                bouncetime = 200
        except:
            log.error("Invalid bounce time! (only integer >0 allowed)")
            return false

        try:
            self._button = gpiozero.Button(
                int(buttonConfig[0]),
                pull_up=pud,
                active_state=active,
                bouncetime=bouncetime,
            )
            if event:
                self._button.when_pressed = toggleLight
            else:
                self._button.when_released = toggleLight
        except:
            log.error("Error while setting up GPIO input for button!")
            return False

        log.info("Light configuration = '{0}'".format(configGPIO["Light"]))

        try:
            lightConfig = int(configGPIO["Light"])
            self._light = gpiozero.LED(lightConfig)
        except:
            log.info("Error while setting up GPIO output for light!")
            return False

        self._isValidGPIO = True
        return True

    def switchLight(state):
        """switch the output pin to the desired state"""
        self._lightonoff = state
        if state:
            self._light.on()
        else:
            self._light.off()
        log.info("Light was set to {0}.".format(getOnOffStr(self._lightonoff)))
        return

    def toggleLight():
        """toggle the output pin"""
        log.info(
            "Callback - toggle light output from {0} to {1}...".format(
                getOnOffStr(self._lightonoff), getOnOffStr(not self._lightonoff)
            )
        )
        self._light.Toggle()
        self._lightonoff = self._light.is_lit
        return

    def getOnOffStr(state):
        return "On" if state else "Off"


try:
    log = logging.getLogger(__name__)

    lightswitch = RaspiGPIOLightswitch()
    lightswitch.initLogging(log)

    log.info("Reading configuration file...")
    if not lightswitch.readConfigFile():
        sys.exit(-2)

    if not lightswitch.config["GPIO"]:
        log.error("Invalid configuration file! (No [GPIO] section)")
        sys.exit(-3)

    log.info("Init GPIO configuration.")
    if not lightswitch.initGPIO():
        sys.exit(-3)

    log.info("Enter service loop...")
    while True:
        pass

except Exception as e:
    if log:
        log.exception("Unhandled exception: {0}".format(e.args[0]))
    sys.exit(-1)
finally:
    if isValidGPIO:
        if log:
            log.info("Finally setting output to off state.")
        lightswitch.switchLight(False)
