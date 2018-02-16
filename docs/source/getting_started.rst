Getting started
===============


Get the code::

    git clone https://github.com/UMONS-GFA/ardas.git


Install the requirements::

    sudo pip3 install -r requirements.txt


**Note**: numpy<=1.14 will fail to install (Original error was: **libf77blas.so.3**: cannot open shared object file: No such file or directory)

To fix this::

    sudo apt install libatlas-base-dev


Edit the **settings_example.py** file according to your configuration and rename it settings.py.

See the `settings list parameters <settings.html>`_ for more information.

Create your sensors

See the `sensors <sensors.html>`_ for more information.

Don't forget: for using ardas tty, the user must be in **dialout** group !