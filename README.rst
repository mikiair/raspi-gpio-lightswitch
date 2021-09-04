raspi-gpio-lightswitch
======================
This is a configurable Python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_ and evaluate one GPIO-in to control one GPIO-out as a light switch.

**raspi-gpio-lightswitch** runs a Python script as a service on Raspberry Pi. It uses the `GPIO Zero <https://github.com/gpiozero/gpiozero>`_ package which allows 
selecting among various underlying pin factories. Tested with `pigpio <http://abyz.me.uk/rpi/pigpio/index.html>`_ library only (e.g. supports using hardware PWM). The configuration allows setting the button events to act on, and supports two different dimming modes via PWM outputs.

Installation
------------
Automated installation is not yet supported. Follow the manual steps below instead.

1. Install pigpio (or any other of the supported `pin-factories <https://gpiozero.readthedocs.io/en/stable/api_pins.html#changing-the-pin-factory>`_):

   | ``sudo apt update``
   | ``sudo apt install python3-pigpio``
  
#. Install GPIO Zero (if not included as a default in your OS distribution)
   
   ``sudo apt install python3-gpiozero``
   
#. Install python-systemd package

   ``sudo apt install python3-systemd``

#. If not already included, add the *pi* user to the *gpio* group (check with ``groups pi`` command)

   ``sudo usermod -a -G gpio mopidy``
   
#. Download raspi-gpio-lightswitch via **Code** button or from `Releases <https://github.com/mikiair/raspi-gpio-lightswitch/releases>`_ page (you most likely did this already):

#. Unzip the received file:

   ``unzip raspi-gpio-lightswitch-main.zip -d ~/raspi-gpio-lightswitch``

#. Configure the service according to your external hardware circuit set-up (see Configuration_).

#. Copy the two configuration files to **/etc** folder

   | ``sudo cp ~/raspi-gpio-lightswitch/gpiozero_pin_factory.conf /etc``
   | ``sudo cp ~/raspi-gpio-lightswitch/raspi-gpio-lightswitch.conf /etc``
   
   The first one is an environment file for the service and defines the default pin-factory for GPIO Zero. The second one holds the actual configuration for the lightswitch service.

#. Copy the Python file to **/usr/local/bin** folder

   ``sudo cp ~/raspi-gpio-lightswitch/raspi-gpio-lightswitch.py /usr/local/bin``
   
#. Copy the service file to **/lib/systemd/system** folder
   
   ``sudo cp ~/raspi-gpio-lightswitch/raspi-gpio-lightswitch.service /lib/systemd/system``
   
#. Enable the service to persist after reboot

   ``sudo systemctl enable raspi-gpio-lightswitch``
   
#. Reboot
 
Configuration
-------------

The configuration is defined in the file ``raspi-gpio-lightswitch.conf``. It requires a section ``[GPIO]`` with mandatory keys ``Button`` and ``Light``, 
and optional key ``Dim``. All pin numbers must be given in BCM format, not physical pin numbering!

The ``Button`` key must be created based on this pattern::

  Button = input_pin_number,up|dn|upex|dnex,press|release|press_release|release_press[,bouncetime_ms]

``input_pin_number``
  The GPIO pin the button is connected to.
``up|dn|upex|dnex``
  Select the pull-up or pull-down resistor for the pin which can use Raspi internal ones, or *ex*ternal resistor provided by your circuit.
``press|release|press_release|release_press``
  Determines the event(s) for toggling the light status from on to off and back, namely when button is *pressed* or *released*.
``bouncetime_ms``
  (*optional*) Defines the time in milliseconds during which subsequent button events will be ignored.

e.g.

``Button = 9,upex,press,100``

configures pin GPIO9 as input expecting an external pull-up resistor, and acting when button is pressed with a bounce time of 100ms.

The ``Light`` key contains the GPIO output pin and an optional brightness correction parameter::

  Light = output_pin_number[,brightness_exp]

``output_pin_number``
  The GPIO pin where your LED (or MOSFET etc.) is connected to.
  
``brightness_exp``
  (*optional*) float number used for brightness linearisation (when dimming); default is 1.0; 
  useful values depend on the type of LED, typically something in the range of 2...3 should fit
   
e.g.

``Light = 12,2``
   
configures pin GPIO12 as output and uses 2.0 as an exponent for brightness linearisation.

The ``Dim`` key uses the following parameters::

  Dim = dim_mode[,dim_level_num,up|dn[,long_press_sec]]

``dim_mode``
    A number defining the dim function:
    
      * 0 - no dimming, just on/off (default, also if no ``Dim`` key specified)
      * 1 - cycle through dim levels up/down + off per button event
      * 2 - start dimming up/down on long press, with each dim-step after a defined time; switch on/off on button short press; remember last dim level by state file
``dim_level_num``
  (*optional*) The number of dimming levels, 'off' state excluded; default is 3; minimum intensity and step size = 100% / dim_level_num, 
  e.g. dim_level_num=4 results in 100% / 4 = 25% step size
``up|dn``
  (*optional*) Cycle through dim-levels with increasing (up) or decreasing (dn) intensity; default is ``up``
``long_press_sec``
  (*optional*) Number of seconds to hold the button until dimming is started; default is 2 seconds
  
e.g.
  
``Dim = 1,5,dn``
  
configures dimming by cycling through 5 dim levels with decreasing intensity (ie. 100% --> 80% --> 60% --> 40% --> 20% --> 0% --> 100%...)
