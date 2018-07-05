# Generate 4 sensors to check frequencies stabilities
# log_output is useful to log ouptut to influxdb

from ardas import sensor_tools as st

# Saves a set of sensors including its calibration in a binary '.ssr' file

sensors = (
    st.UncalibratedFMSensor(sensor_id='0001', log_output=True),
    st.UncalibratedFMSensor(sensor_id='0002', log_output=True),
    st.UncalibratedFMSensor(sensor_id='0003', log_output=True),
    st.UncalibratedFMSensor(sensor_id='0004', log_output=True)
           )

if __name__ == '__main__':
    for s in sensors:
        print(s.sensor_id + ' - ' + s.quantity + ' : ' + s.output_repr(10000))
        s.save()