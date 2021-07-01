raspi-gpio-lightswitch
======================
This is a configurable Python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_ and evaluate one GPIO-in to control one GPIO-out as a light switch.

**raspi-gpio-lightswitch** runs a Python script as a service on Raspberry Pi. It uses the `GPIO Zero <https://github.com/gpiozero/gpiozero>`_ package which allows 
selecting among various underlying pin factories. Tested with `pigpio <http://abyz.me.uk/rpi/pigpio/index.html>`_ library only (e.g. supports using hardware PWM).

Installation
------------
Automated installation is not yet supported. Follow the manual steps below instead.

1. Install pigpio (or any other of the supported `pin-factories <https://gpiozero.readthedocs.io/en/stable/api_pins.html#changing-the-pin-factory>`_):

   | ``sudo apt update``
   | ``sudo apt install python3-pigpio``
  
#. To set pigpio as the default pin factory, add the following line to the end of your **~/bash.rc** file:
   
   ``export GPIOZERO_PIN_FACTORY=pigpio``

#. Reboot

#. Install GPIO Zero (if not included as a default in your OS distribution)
   
   ``sudo apt install python3-gpiozero``
   
#. Install python-systemd package

   ``sudo apt install python3-systemd``

#. Download raspi-gpio-lightswitch (you most likely did this already)

   | ``wget https://github.com/mikiair/raspi-gpio-lightswitch/archive/main.zip``
   | ``unzip main.zip -d ~/raspi-gpio-lightswitch``

#. Configure the service according to your external circuit set-up (see Configuration_).

#. Copy the service file to **/lib/systemd/system** folder
   
   ``sudo cp ~/raspi-gpio-lightswitch/raspi-gpio-lightswitch.service /lib/systemd/system``
   
#. If not already included, add the *pi* user to the *gpio* group (check with ``groups pi`` command)

   ``sudo usermod -a -G gpio mopidy``
   
#. Enable the service to persist after reboot

   ``sudo systemctl enable raspi-gpio-lightswitch``
 
Configuration
-------------

The configuration is defined in the file ``raspi-gpio-lightswitch.conf``. It requires a section ``[GPIO]`` with mandatory keys ``Button`` and ``Light``.
All pin numbers must be given in BCM format, not physical pin numbering!

The ``Button`` key must be created based on this pattern:

``Button = input_pin_number,up|dn|upex|dnex,press|release[,bouncetime_ms]``

* ``input_pin_number``
  The GPIO pin to which the button is connected.
* ``up|dn|upex|dnex``
  Selects the pull-up or pull-down resistor for the pin which can use Raspi internal ones, or *ex*ternal resistor provided by your circuit.
* ``press|release``
  Determines the event for toggling the light status from on to off and back, namely when button is *pressed* or *released*.
* ``bouncetime_ms``
  (*optional*) Defines the time in milliseconds during which subsequent button events will be ignored.

e.g.

``Button = 9,upex,press,100``

configures pin GPIO9 as input expecting an external pull-up resistor, and acting when button is pressed with a bounce time of 100ms.

The ``Light`` key only contains the GPIO output pin where your LED (or MOSFET etc.) is connected:

``Light = output_pin_number``

* ``output_pin_number``
  The GPIO pin the light is connected to.
   
e.g.

``Light = 12``
   
configures pin GPIO12 as output.
