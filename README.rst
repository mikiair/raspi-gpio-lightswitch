raspi-gpio-lightswitch
======================
Configurable python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_ and evaluate one GPIO-in to control one GPIO-out as a light switch.

**raspi-gpio-lightswitch** runs a Python script as a service on Raspberry Pi. It uses the `GPIO Zero <https://github.com/gpiozero/gpiozero>`_ package which allows for 
selecting among various underlying pin factories. Tested with `pigpio <http://abyz.me.uk/rpi/pigpio/index.html>`_ library only (which enables using hardware PWM).

Installation
------------
Automated installation is not yet supported. Follow the manual steps below instead.

1. Install pigpio:

   | ``sudo apt update``
   | ``sudo apt install python3-pigpio``
  
2. To set pigpio as the default pin factory, add the following line to the end of your **~/bash.rc** file:
   
   ``export GPIOZERO_PIN_FACTORY=pigpio``

3. Reboot

4. Install GPIO Zero
   
   ``sudo apt install python3-gpiozero``
   
5. Install python-systemd package

   ``sudo apt install python3-systemd``

6. Download raspi-gpio-lightswitch

   ``123...``

7. Copy the service file to **/lib/systemd/system** folder
   
   ``sudo cp ~/raspi-gpio-lightswitch/raspi-gpio-lightswitch.service /lib/systemd/system``
   
8. Configure the service according to your personal hardware set-up (see below).

9. Enable the service to persist after reboot

   ``sudo systemctl enable raspi-gpio-lightswitch``
 
Configuration
-------------

The configuration is done with the file ``raspi-gpio-lightswitch.conf``. It requires a section ``[GPIO]`` with mandatory keys ``Button`` and ``Light``.
All pin numbers must be given in BCM format, not physical pin numbering!

The ``Button`` key must be created based on this pattern:

  ``Button = input pin number,up|dn|upex|dnex,press|release[,bouncetime_ms]``

The ``Light`` key only contains the GPIO output pin where your LED (or MOSFET etc.) is connected:

   ``Light = output pin number``
   
e.g.

   ``Light = 12``
   
configures pin GPIO12 as output.
