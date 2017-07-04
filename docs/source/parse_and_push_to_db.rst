Parse and push to db
====================

Automatisation
--------------

Add a cron job::

   PYTHONPATH=/home/pi/ardas

   # m h  dom mon dow   command
   @reboot /usr/bin/python3 /home/pi/ardas/ardas/raspardas.py debug on calibration /home/pi/ardas/ardas/calibrations/cal_0002.dat > /home/pi/ardas/cronlog.log 2>&1

