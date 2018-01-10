from ardas import sensor_tools as st

# Saves a set of sensors including its calibration in a binary '.ssr' file

sensors = (st.UncalibratedFMSensor(sensor_id='0001', log_output=False),
           st.UncalibratedFMSensor(sensor_id='0002', log_output=False),
           st.FMSensor(sensor_id='0003', processing_parameters=(-16.9224032438, 0.0041525221, -1.31475837290789E-07,
                                                                2.39122208189129E-012, -1.72530800355418E-017),
                       quantity='temp.', units='°C', output_format='%6.3f', log_output=True),
           st.FMSensor(sensor_id='0004', processing_parameters=(-16.9224032438, 0.0041525221, -1.31475837290789E-07,
                                                                2.39122208189129E-012, -1.72530800355418E-017),
                       quantity='temp.', units='°C', output_format='%6.3f', log_output=True)
           )

if __name__ == '__main__':
    for s in sensors:
        print(s.sensor_id + ' - ' + s.quantity + ' : ' + s.output_repr(10000))
        s.save()
    print('reload sensor...')
    s = st.load_sensor('0001')
    print(s.sensor_id + ' - ' + s.quantity + ' : ' + s.output_repr(10000) + ' Log:' + str(s.log))