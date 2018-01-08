from ardas import sensor_tools as st

# Saves a set of sensors including its calibration in a binary '.ssr' file

sensors = (st.UncalibratedFMSensor(sensor_id='0000', log_output=False),
           )

if __name__ == '__main__':
    for s in sensors:
        print(s.sensor_id + ' - ' + s.quantity + ' : ' + s.output_repr(10000))
        s.save()

