import random
from time import sleep
from pathlib import Path
from pickle import dump, load
import datetime

cur_dir = Path(__file__).resolve().parent  # os.path.dirname(os.path.realpath(__file__))


class Fake1WireSensor(object):
    """Generic fake 1-Wire sensor"""
    def __init__(self, slave_prefix='00-', id=None, name=None):
        """Generate a unique id from an hexadecimal timestamp"""
        self.__id = id
        self.__name = name
        self.slave_prefix = slave_prefix
        if self.id is None:
            self.generate_id()

    @property
    def id(self):
        """ Gets id
        """
        return self.__id

    @id.setter
    def id(self, val):
        self.__id = val

    def generate_id(self):
        self.id = '00000' + hex(int((datetime.datetime.utcnow().timestamp() * 1000000) % 16 ** 7))

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


class FakeTempSensor(Fake1WireSensor):
    """Fake 1-Wire temperature sensor default is DS18B20"""
    def __init__(self, name=None):
        super(FakeTempSensor, self).__init__(slave_prefix='28-', id=None)
        self.temperature = 0.
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
            self.__name = '%s%s' % ('28-', self.id)

    def get_temperature(self):
        self.temperature = random.uniform(20, 28)
        sleep(random.uniform(0.2, 0.5))
        return self.temperature

