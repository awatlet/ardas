Describe your sensors
=====================

Sensors are described in special files named `sensorXXXX.ssr` where XXXX stands for the sensor that contain `raspardas.py`.

``CALIBRATE THE SENSORS``
-------------------------
Uncalibrated FM sensors produce readings that are a frequency. You may want to calibrate your FM sensors to produce
meaningful readings in units such as °C or µm and not just Hz.

``CREATE THE .SSR FILES``
-------------------------
In the example below, four sensors are created and saved to `.ssr` files.
::

    from ardas import sensor_tools as st
    # Saves a set of sensors including its calibration in a binary '.ssr' file
    sensors = (st.FMSensor(sensor_id='0001', processing_parameters=(-16.9224032438, 0.0041525221, -1.31475837290789E-07,
                                                                2.39122208189129E-012, -1.72530800355418E-017),
                       quantity='temp.', units='°C', output_format='%6.3f', log_output=True),
           st.UncalibratedFMSensor(sensor_id='0002', log_output=False),
           st.UncalibratedFMSensor(sensor_id='0003', log_output=True),
           st.UncalibratedFMSensor(sensor_id='0004', log_output=True),
           )

    if __name__ == '__main__':
        for s in sensors:
            print(s.sensor_id + ' - ' + s.quantity + ' : ' + s.output_repr(10000))
            s.save()
        print('reload sensor...')
        s = st.load_sensor('1401')
        print(s.sensor_id + ' - ' + s.quantity + ' : ' + s.output_repr(10000) + ' Log:' + str(s.log))

