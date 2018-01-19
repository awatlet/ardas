Parse and push to db
====================

Automation
----------

Add a cron job

In the example below we assume that the user name is `pi`
::

   PYTHONPATH=/home/pi/ardas

   # m h  dom mon dow   command
   @reboot /usr/bin/python3 /home/pi/ardas/ardas/raspardas.py > /home/pi/ardas/cronlog.log 2>&1

::
