Getting started
===============

Deployment
----------

Use `ardas-tools <https://github.com/UMONS-GFA/ardas-tools>`_ scripts for easy deployment

Or deploy manually

Get the code::

    git clone https://github.com/UMONS-GFA/ardas.git


Install the requirements::

    sudo pip3 install -r requirements.txt


**Note**: numpy<=1.14 will fail to install (Original error was: **libf77blas.so.3**: cannot open shared object file: No such file or directory)

To fix this::

    sudo apt install libatlas-base-dev


Configure your settings
-----------------------

Edit the **settings_example.py** file according to your configuration and rename it settings.py.

See the `settings list parameters <settings.html>`_ for more information.

Create your sensors, you can use the script **frequency_sensor_generator.py** to generate 4 frequency sensors.

See the `sensors <sensors.html>`_ for more information.

Don't forget: for using ardas tty, the user must be in **dialout** group !

Prepare the arduino
-------------------

see `how to build arduino sketch <build_arduino_sketch.html>`_

Don't forget to set it in raspardas_mode (#RD)or with arduino_reset sketch.

Start the process
-----------------
::

    python3 raspardas.py

Stop the process
----------------

Stop the process correctly::

    telnet REMOTE_IP REMOTE_PORT

then::

    #KL

Don't forget to replace *REMOTE_PORT* by your local_port set in your settings file
