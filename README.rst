raspi-gpio-lightswitch
======================
This is a configurable Python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_ and evaluate one GPIO-in to control one GPIO-out as a light switch.

**raspi-gpio-lightswitch** runs a Python script as a service on Raspberry Pi. It uses the `GPIO Zero <https://github.com/gpiozero/gpiozero>`_ package which allows 
selecting among various underlying pin factories. Tested with `pigpio <http://abyz.me.uk/rpi/pigpio/index.html>`_ library only (e.g. supports using hardware PWM). The configuration allows setting the button events to act on, and supports two different dimming modes via PWM outputs.

Required packages
-----------------
* pigpiod (or any other supported pin factory library)
* GPIO Zero
* python3-systemd

Installation
------------
Download raspi-gpio-lightswitch via **Code** button or from `Releases <https://github.com/mikiair/raspi-gpio-lightswitch/releases>`_ page (you most likely did already).
Unzip the received file:

   ``unzip raspi-gpio-lightswitch-main.zip -d ~/raspi-gpio-lightswitch``

Configure the service by editing the file ``raspi-gpio-lightswitch.conf`` according to your external hardware circuit set-up (see Configuration_). 
Then simply run the script ``install`` in the **script** sub-folder. It will download and install the required packages, 
copy the files to their destinations, will register the service, and finally start it.

If you need to change the configuration after installation, you might use the script ``reconfigure`` after editing the source configuration file.
This will stop the service, copy the changed configuration file to **/etc** folder (overwrites previous version!), and then start the service again.

If you downloaded a newer version of the service the script ``update`` will handle stop and start of the service, and will copy the new Python and service files.
However, this will not update any underlying packages or services.

For uninstall, use the provided script ``uninstall``.

Configuration
-------------
The configuration is defined in the file ``raspi-gpio-lightswitch.conf``. Before installation, you will find the source file in the folder where you unzipped the package files. 
After installation, the active version is in **/etc** folder.

It requires a section ``[GPIO]`` with mandatory keys ``Button`` and ``Light``, and optional key ``Dim``. 
All pin numbers must be given in BCM format, not physical pin numbering!

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
