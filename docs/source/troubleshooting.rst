Troubleshooting
===============

* Is raspardas.py running?
Check if rapsardas.py is running ::

    ps -aux | grep python3

Note processes ids (e.g. xxx)

For the low-level troubleshooting, it is necessary to kill the running instances or rapspardas.py and inter
Kill the running instances of raspardas.py ::

    kill -KILL xxx

* Does the I2C communication with RTC work?

Upload I2Cscanner in arduino ::

    cd ~/ardas/examples/i2cscanner
    mkdir build
    cd build
    cmake ..
    make
    make upload

Check output


* Does the RTC oscillate?

Upload XXX in arduino ::

    cd ~/ardas/examples/XXX
    mkdir build
    cd build
    cmake ..
    make
    make upload

