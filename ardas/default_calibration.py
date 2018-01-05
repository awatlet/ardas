from ardas import calibration_tools as cal


# sensor_calibration should be a tuple
# each element of the tuple is itself a tuple describing a sensor in the order of the channels present on the ardas
# the first element is the sensor number, the second is a dictionary describing how the ardas counts should be
# converted
sensor_calibration = (('0001', {'method': cal.polynomial,
                                'parameters': (0., 1., 0., 0., 0.),
                                'quantity': 'freq.',
                                'units': 'Hz',
                                'format': '%11.4f',
                                'log': True}
                       ),

                      ('0002', {'method': cal.polynomial,
                                'parameters': (0., 1., 0., 0., 0.),
                                'quantity': 'freq.',
                                'units': 'Hz',
                                'format': '%11.4f',
                                'log': True}
                       ),

                      ('0003', {'method': cal.polynomial,
                                'parameters': (0., 1., 0., 0., 0.),
                                'quantity': 'freq.',
                                'units': 'Hz',
                                'format': '%11.4f',
                                'log': True}
                       ),

                      ('0004', {'method': cal.polynomial,
                                'parameters': (0., 1., 0., 0., 0.),
                                'quantity': 'freq.',
                                'units': 'Hz',
                                'format': '%11.4f',
                                'log': True}
                       ),


                      )

if __name__ == '__main__':
    print(sensor_calibration[0][0], '-', sensor_calibration[0][1]['quantity'],
          ': ' + sensor_calibration[0][1]['format'] % sensor_calibration[0][1]['method'](10000, sensor_calibration[0][1]['parameters']),
          sensor_calibration[0][1]['units'])
    print(sensor_calibration[3][0], '-', sensor_calibration[3][1]['quantity'],
          ': ' + sensor_calibration[3][1]['format'] % sensor_calibration[3][1]['method'](10000, sensor_calibration[3][1]['parameters']),
          sensor_calibration[3][1]['units'])

