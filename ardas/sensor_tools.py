import numpy as np
from pathlib import Path
from pickle import dump, load
import logging
from time import sleep
try:
    from w1thermsensor import W1ThermSensor

    class TempSensor(W1ThermSensor):
        def __init__(self, sensor_type=None, sensor_id=None, name=None):
            super(TempSensor, self).__init__(sensor_type=sensor_type, sensor_id=sensor_id)  # TODO: check this use of super...
            self.__name = name

        @property
        def name(self):
            """Gets and sets sensor name
            """
            return self.__name

        @name.setter
        def name(self, val):
            if val is not None:
                self.__name = str(val)
            else:
                self.name = '%s%s' % ('28-', self.id)

        def save(self):
            """Save the sensor as a serialized object to a file """
            f_name = cur_dir / 'sensor_' + self.name + '.ssr'
            if Path(f_name).exists():
                logging.warning('Sensor file ' + f_name + ' already exists, unable to save sensor')
            else:
                with open(f_name, 'wb') as sensor_file:
                    dump(self, sensor_file)

except:
    from ardas.fake_sensor import FakeTempSensor

    class TempSensor(FakeTempSensor):
        def __init__(self):
            super(TempSensor, self).__init__()   # TODO: check this use of super...

cur_dir = Path(__file__).resolve().parent  # os.path.dirname(os.path.realpath(__file__))


def load_sensor(id):
    """Loads a sensor object from a sensor '.ssr' file

    :param id: a unique identification number of the sensor
    :return: a sensor object
    :rtype: sensor"""
    f_name = cur_dir / 'sensor_' + id + '.ssr'
    with open(f_name, 'rb') as sensor_file:
        sensor = load(sensor_file)
    return sensor


def generate_w1temp_sensors(nb_sensor=2):
    sensors = []
    for i in range(nb_sensor):
        s = TempSensor()
        sensors.append(s)
        sleep(0.00001)  # mandatory otherwise each sensor could have the same name
    return sensors


if __name__ == '__main__':
    pass
