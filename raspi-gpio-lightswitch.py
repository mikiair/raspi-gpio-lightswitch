#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2021 by Michael Heise"
__license__ = "Apache License Version 2.0"
__version__ = "1.1.4"
__date__ = "11/06/2021"

"""Configurable python service to run on Raspberry Pi
   and evaluate one GPIO-in to control one GPIO-out as light switch.
"""

#    Copyright 2021 Michael Heise (mikiair)
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# standard imports
import configparser
import logging
import pathlib
import signal
import sys
import time
import weakref

# 3rd party imports
import gpiozero
from systemd.journal import JournalHandler

# local imports
# - none -


class RaspiGPIOLightSwitch:
    """Class for controlling a dimmable light
    through a switch connected to GPIOs on Raspberry.
    """

    CONFIGFILE = "/etc/raspi-gpio-lightswitch.conf"
    STATEFILE = "/home/pi/.raspi-gpio-lightswitch.state"

    VALUES_PULLUPDN = ["up", "dn", "upex", "dnex"]
    VALUES_PRESS_RELEASE = ["press", "release", "press_release", "release_press"]
    VALUES_DIMUPDN = ["up", "dn"]

    # state transition matrix by dimMode, eventMode, and source status
    # dictionary keys - source / values - target
    # 0: Off-r / 1: On-p / 2: On-r / 3: Off-p / 4: On-p2 / 5: Off-p2 / 6: On-h / 7: Off-h
    STATES = [
        [
            ({1: 2, 3: 0}, {0: 1, 2: 3}),
            ({1: 0, 3: 2}, {0: 3, 2: 1}),
            ({1: 2, 4: 0}, {0: 1, 2: 4}),
            ({3: 2, 5: 0}, {0: 3, 2: 5}),
        ],
        [
            ({1: 2, 3: 0}, {0: 1, 2: 9}),
            ({1: 9, 3: 2}, {0: 3, 2: 1}),
            ({1: 2, 4: 0}, {0: 1, 2: 9}),
            ({1: 2, 3: 2, 5: 0}, {0: 3, 2: 9}),
        ],
        [
            ({1: 2, 3: 0, 6: 2, 7: 0}, {0: 1, 2: 3}, {1: 6, 3: 7, 6: 6, 7: 7}),
            ({1: 0, 3: 2, 6: 2}, {0: 3, 2: 1}, {1: 6, 3: 6, 6: 6}),
            ({1: 2, 4: 0, 6: 2}, {0: 1, 2: 4}, {1: 6, 4: 6, 6: 6}),
            ({3: 2, 5: 0, 6: 2, 7: 0}, {0: 3, 2: 5}, {3: 6, 5: 7, 6: 6, 7: 7}),
        ],
    ]

    # action matrix by dimMode, eventMode, and target status
    # -1 - no action / 0 - light off / 1 - light on, restore / 2 - dim up/dn / None - undefined
    ACTIONS = [
        [
            (-1, 1, -1, 0, None, None, None, None),
            (0, -1, 1, -1, None, None, None, None),
            (0, 1, -1, None, -1, None, None, None),
            (-1, None, 1, -1, None, 0, None, None),
        ],
        [
            (-1, 2, -1, 0, None, None, None, None),
            (0, -1, 2, -1, None, None, None, None),
            (0, 2, -1, None, -1, None, None, None),
            (-1, -1, 2, -1, None, 0, None, None),
        ],
        [
            (-1, 1, -1, 0, None, None, 2, -1),
            (0, -1, 1, -1, None, None, 2, None),
            (0, 1, -1, None, -1, None, 2, None),
            (-1, None, 1, -1, None, 0, 2, -1),
        ],
    ]

    EVENT_RELEASE = 0
    EVENT_PRESS = 1
    EVENT_HOLD = 2

    def __init__(self):
        """Initialize service class."""
        self._finalizer = weakref.finalize(self, self.finalize)
        self.isValidGPIO = False
        self.config = None

    def remove(self):
        """Call finalizer before removing class instance."""
        self._finalizer()

    @property
    def removed(self):
        return not self._finalizer.alive

    def finalize(self):
        """Set valid state to false."""
        self.isValidGPIO = False

    def initLogging(self, log):
        """Initialize logging to journal."""
        log_fmt = logging.Formatter("%(levelname)s %(message)s")
        logHandler = JournalHandler()
        logHandler.setFormatter(log_fmt)
        log.addHandler(logHandler)
        log.setLevel(logging.INFO)
        # log.setLevel(logging.DEBUG)
        self._log = log
        self._log.info("Initialized logging.")

        pinf = type(gpiozero.Device._default_pin_factory()).__name__
        self._log.info(f"GPIO Zero default pin factory: {pinf}")
        return

    def readConfigFile(self):
        """Read the config file."""
        try:
            self._log.info(f"Reading configuration file... '{self.CONFIGFILE}'")
            self.config = configparser.ConfigParser()
            self.config.read(self.CONFIGFILE)
            return True
        except Exception as e:
            self._log.error(f"Accessing config file '{self.CONFIGFILE}' failed! ({e})")
            return False

    def validateStringInArray(self, paramName, configStr, validArray):
        """Validate if configuration string is in array with valid strings
        and return the respective index.
        """
        try:
            return validArray.index(configStr)
        except Exception:
            self._log.error(
                "Invalid {0} configuration! Only one of {1} allowed!".format(
                    paramName, "/".join(validArray)
                )
            )
            return -1

    def getButtonConfig(self, buttonConfig):
        """Get button configuration from split string."""
        if len(buttonConfig) < 3 or len(buttonConfig) > 4:
            self._log.error("Button configuration has too less or too many parameters!")
            return False

        self._buttonPin = int(buttonConfig[0])

        pudMode = self.validateStringInArray(
            "resistor", buttonConfig[1], self.VALUES_PULLUPDN
        )
        if pudMode == -1:
            return False

        try:
            pudSwitcher = {
                0: (True, None),
                1: (False, None),
                2: (None, False),
                3: (None, True),
            }
            self._pud, self._active = pudSwitcher[pudMode]
        except Exception as e:
            self._log.error(f"Could not convert pull resistor configuration! ({e})")
            return False

        self._eventMode = self.validateStringInArray(
            "event", buttonConfig[2], self.VALUES_PRESS_RELEASE
        )
        if self._eventMode == -1:
            return False

        if len(buttonConfig) == 4:
            try:
                self._bouncetime = int(buttonConfig[3])
            except Exception:
                self._log.error("Invalid bounce time! (only integer >0 allowed)")
                return False
        else:
            self._bouncetime = 100

        return True

    def checkDimModeRange(self):
        """Check dimMode for valid range (0...2)."""
        if self._dimMode > 2 or self._dimMode < 0:
            self._log.error("Dim mode must be in range 0...2")
            return False
        return True

    def checkDimConfigParamCount(self, dimConfigLen):
        """Check the number of parameters provided against selected dimMode."""
        if (self._dimMode == 0 and dimConfigLen > 1) or (
            dimConfigLen > self._dimMode + 2
        ):
            self._log.error("Wrong number of parameters for dim settings")
            return False
        return True

    def configureDimLevels(self, dimConfigLen, dimConfig):
        """Get the number of dim levels from the configuration or set default of 3."""
        # dimLevels number excludes 'off'
        if dimConfigLen > 1:
            self._dimLevels = int(dimConfig[1])
            if self._dimLevels <= 1:
                self._dimLevels = 3
        else:
            self._dimLevels = 3

        self._dimStep = 1.0 / self._dimLevels
        self._dimIndex = 0

    def configureDimDirection(self, dimConfigLen, dimConfig):
        if dimConfigLen > 2:
            dimDir = dimConfig[2].lower()
            if dimDir == self.VALUES_DIMUPDN[1]:
                self._dimStep = -self._dimStep
            elif dimDir != self.VALUES_DIMUPDN[0]:
                self._log.error("Invalid dim direction configuration!")
                return False
        return True

    def configureDimHoldtime(self, dimConfigLen, dimConfig):
        if dimConfigLen > 3:
            try:
                self._dimHoldSec = float(dimConfig[3])
            except Exception:
                self._log.error("Invalid hold time!")
                return False
        else:
            self._dimHoldSec = 1.5
        return True

    def getDimmingConfig(self, dimConfig):
        """Get dimming options from config split string."""
        self._dimMode = int(dimConfig[0])

        if not self.checkDimModeRange():
            return False

        dimConfigLen = len(dimConfig)
        if not self.checkDimConfigParamCount(dimConfigLen):
            return False

        if self._dimMode == 0:
            return True

        self.configureDimLevels(dimConfigLen, dimConfig)

        if not self.configureDimDirection(dimConfigLen, dimConfig):
            return False

        if not self.configureDimHoldtime(dimConfigLen, dimConfig):
            return False

        return True

    def createAndConfigureButton(self):
        """Create GPIO Zero button object and configure its event handlers."""
        # -------- create button object --------
        try:
            self._log.debug(self._buttonPin, self._pud, self._active, self._bouncetime)
            self._button = gpiozero.Button(
                self._buttonPin,
                pull_up=self._pud,
                active_state=self._active,
                bounce_time=0.001 * self._bouncetime,
            )
        except Exception as e:
            self._log.error(f"Error while setting up GPIO input for button! ({e})")
            return False

        # -------- set button event handlers --------
        try:
            self._button.when_released = self.handleWhenReleased
            self._button.when_pressed = self.handleWhenPressed
            if self._dimMode == 2:
                self._button.when_held = self.handleWhenHeld
                self._button.hold_time = self._dimHoldSec
                self._button.hold_repeat = True
        except Exception as e:
            self._log.error(f"Failed to allocate button events! ({e})")
            return False

        return True

    def createAndConfigureLight(self, lightConfig):
        """Create GPIO Zero LED object and configure dim brightness correction."""
        try:
            lightPin = int(lightConfig[0])

            if len(lightConfig) == 2:
                self._linExp = float(lightConfig[1])
                if self._linExp < 1:
                    raise ValueError("Exponent must be >1!")
            elif len(lightConfig) > 2:
                raise ValueError(
                    "Too many parameters for light configuration! (max. 2)"
                )
            else:
                self._linExp = 1.0

            if self._dimMode == 0:
                self._light = gpiozero.LED(lightPin)
            else:
                self._light = gpiozero.PWMLED(lightPin, frequency=400)
            return True
        except Exception as e:
            self._log.error(f"Error while setting up GPIO output for light! ({e})")
            return False

    def initGPIO(self):
        """Evaluate the data read from the config file to
        set the GPIO input and output.
        """
        self._log.info("Init GPIO configuration.")
        configGPIO = self.config["GPIO"]

        # -------- get button configuration --------
        self._log.info("Button configuration = '{0}'".format(configGPIO["Button"]))

        buttonConfig = configGPIO["Button"].lower().split(",")

        if not self.getButtonConfig(buttonConfig):
            return False

        # -------- define dim options --------
        self._dimMode = 0
        self._dimIndex = 1
        self._dimLevels = 1
        self._dimStep = 1.0

        if self.config.has_option("GPIO", "Dim"):
            self._log.info("Dimming configuration = '{0}'".format(configGPIO["Dim"]))

            dimConfig = configGPIO["Dim"].lower().split(",")

            if not self.getDimmingConfig(dimConfig):
                return False

        # -------- create button object and set its event handlers --------
        if not self.createAndConfigureButton():
            return False

        # -------- create and configure light object --------
        self._log.info("Light configuration = '{0}'".format(configGPIO["Light"]))

        lightConfig = configGPIO["Light"].split(",")

        if not self.createAndConfigureLight(lightConfig):
            return False

        self.isValidGPIO = True
        return True

    def readStateFile(self):
        """Read the last set dim index from file if dimMode is 2."""
        if self._dimMode < 2:
            return

        try:
            if pathlib.Path(self.STATEFILE).exists():
                self._log.info(f"Reading state file... '{self.STATEFILE}'")
                with open(self.STATEFILE, "r") as sf:
                    stored_value = float(sf.read())
                if stored_value > self._dimLevels:
                    stored_value = self._dimLevels
                self._dimIndex = stored_value
                self._log.info(
                    f"Restored dim level {100.0*self._dimIndex/self._dimLevels}%."
                )
            else:
                self._log.info("No state file found, setting default value 100%.")
                self._dimIndex = self._dimLevels
                self._log.debug(f"-> dimIndex {self._dimIndex}")
        except Exception as e:
            self._log.error(f"Reading state file '{self.STATEFILE}' failed! ({e})")

    def setupStateMachine(self):
        """Set up the internal state machine records, together with action methods."""
        try:
            self._log.info(
                f"Setting up state machine... (d={self._dimMode},e={self._eventMode})"
            )

            self._stateMachine = (
                self.STATES[self._dimMode][self._eventMode],
                self.ACTIONS[self._dimMode][self._eventMode],
            )
            self._actions = [self.actionOff, self.actionOn, self.actionDim]
            self._current_state = 0
            # print(self._stateMachine)
        except Exception as e:
            self._log.error(f"Error in state machine set-up! ({e})")

    def getNextStateNumber(self, event, current):
        """Return the next state number based on the button event
        and the current state."""
        try:
            self._log.debug(
                f"Get next state for event {event} and current state {current}:"
            )
            next_temp = self._stateMachine[0][event][current]
            self._log.debug(f"Temporary next: {next_temp}")
            if next_temp == 9:
                self._log.debug(
                    f"- Special case 9... {self._dimIndex}/{self._dimLevels} -"
                )
                if self._dimIndex < self._dimLevels:
                    # dim up/down
                    self._log.debug("-- dim up/down --")
                    next_temp = 2 if self._eventMode == 1 else 1
                else:
                    # off
                    self._log.debug("-- light off --")
                    next_temp = {0: 3, 1: 0, 2: 4, 3: 5}[self._eventMode]
                    self._dimIndex = 0
            return next_temp
        except Exception as e:
            self._log.error(f"Error while getting next state number! ({e})")
            return -1

    def setNextState(self, next_state):
        """Determine and perform the allocated action for the requested next state,
        and finally set this state."""
        try:
            action = self._stateMachine[1][next_state]
            self._log.debug(f"Select action for next state '{next_state}' --> {action}")
            if action is not None:
                self._log.debug(f"Next state '{next_state}' --> action '{action}'")
                if action >= 0:
                    action_call = self._actions[action]
                    action_call()
                self._current_state = next_state
            else:
                raise ValueError("Action was None!?")
        except Exception as e:
            self._log.error(f"Setting next state '{next_state}' failed! ({e})")
            self._current_state = 0

    def handleButtonEvent(self, event):
        """General handling method for one of the button events."""
        self._log.debug(f"Handle button event {event}...")
        next_state = self.getNextStateNumber(event, self._current_state)
        self._log.debug(
            f"Current: {self._current_state} event {event} --> Next: {next_state}"
        )
        if next_state >= 0:
            self.setNextState(next_state)
        else:
            self._log.error("Try resetting current state to 0...")
            self._current_state = 0

    def handleWhenReleased(self):
        """Event handler for when_released."""
        self._log.debug("- when_released event -")
        self.handleButtonEvent(self.EVENT_RELEASE)

    def handleWhenPressed(self):
        """Event handler for when_pressed."""
        self._log.debug("- when_pressed event -")
        self.handleButtonEvent(self.EVENT_PRESS)

    def handleWhenHeld(self):
        """Event handler for when_held."""
        self._log.debug("- when_held event -")
        self.handleButtonEvent(self.EVENT_HOLD)

    def setLightToLevel(self, new_value):
        """Set the light to a new value (0...1) and then log its new state."""
        try:
            if self._linExp == 1.0:
                self._light.value = new_value
            else:
                self._light.value = pow(new_value, self._linExp)

            if self._light.is_lit:
                self._log.info(f"Light is on now at {100 * self._light.value}%.")
            else:
                self._log.info("Light is off now.")
        except Exception:
            self._log.error(f"Could not set new light value {100 * new_value}%!")

    def writeStateFile(self):
        """Write the current dim level index to the state file."""
        try:
            self._log.debug(f"Writing state file... '{self.STATEFILE}'")
            with open(self.STATEFILE, "w") as sf:
                sf.write(str(self._dimIndex))
        except Exception as e:
            self._log.error(f"Writing state file '{self.STATEFILE}' failed! ({e})")

    def actionOff(self):
        """Action function to switch the light off."""
        self._log.info("Action: light off")
        self.setLightToLevel(0.0)

    def actionOn(self):
        """Action function to switch the light on and restore its previous dim level."""
        self._log.info("Action: light on (restore previous dim level)")
        self._log.debug(
            f"dimStep {self._dimStep}  dimIndex {self._dimIndex}  dimMode {self._dimMode}"
        )
        if self._dimStep > 0:
            next_value = self._dimIndex * self._dimStep
        else:
            next_value = 1.0 + (self._dimIndex - 1) * self._dimStep

        self.setLightToLevel(next_value)

    def actionDim(self):
        """Action function to dim the light one step up or down."""
        self._log.info("Action: dim light one step up/dn")
        self._dimIndex += 1
        if self._dimIndex > self._dimLevels:
            self._dimIndex = 1

        if self._dimStep > 0:
            next_value = self._dimIndex * self._dimStep
        else:
            next_value = 1.0 + (self._dimIndex - 1) * self._dimStep

        self._log.debug(f"next_value {next_value}  dimIndex {self._dimIndex}")
        self.setLightToLevel(next_value)

        if self._dimMode == 2:
            self.writeStateFile()

    def switchLightOff(self):
        """Switch the output pin off."""
        self._light.off()
        self._log.info("Light is off now.")


def sigterm_handler(_signo, _stack_frame):
    """Clean exit on SIGTERM signal (when systemd stops the process)."""
    sys.exit(0)


# install handler
signal.signal(signal.SIGTERM, sigterm_handler)

log = None
lightswitch = None

try:
    log = logging.getLogger(__name__)

    lightswitch = RaspiGPIOLightSwitch()
    lightswitch.initLogging(log)

    if not lightswitch.readConfigFile():
        sys.exit(-2)

    if not lightswitch.config["GPIO"]:
        log.error("Invalid configuration file! (No [GPIO] section)")
        sys.exit(-3)

    if not lightswitch.initGPIO():
        log.error("Init GPIO failed!")
        sys.exit(-3)

    lightswitch.readStateFile()

    lightswitch.setupStateMachine()

    log.info("Enter raspi-gpio-lightswitch service loop...")
    while True:
        time.sleep(1)

except Exception as e:
    if log:
        log.exception(f"Unhandled exception: {e}")
    sys.exit(-1)
finally:
    if lightswitch and lightswitch.isValidGPIO:
        if log:
            log.info("Finally setting output to off state.")
        lightswitch.switchLightOff()
