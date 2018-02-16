import random
import time
import datetime


class Fake1WireSensor(object):
    """Generic fake 1-Wire sensor"""
    def __init__(self, seller_id='00-00000', sensor_id=None):
        """Generate a unique id from an hexadecimal timestamp"""
        self.sensor_id = sensor_id
        self.__seller_id = seller_id
        if self.sensor_id is None:
            self.generate_sensor_id()

    @property
    def sensor_id(self):
        """ Gets sensor_id
        """
        return self.__sensor_id

    @sensor_id.setter
    def sensor_id(self, val):
        self.__sensor_id = val

    def generate_sensor_id(self):
        self.sensor_id = self.__seller_id + hex(int((datetime.datetime.utcnow().timestamp() * 1000000) % 16 ** 7))


class FakeTempSensor(Fake1WireSensor):
    """Fake 1-Wire temperature sensor default is DS18B20"""
    def __init__(self):
        Fake1WireSensor.__init__(self, seller_id='28-00000', sensor_id=None)
        self.temperature = 0

    def get_temperature(self):
        self.temperature = random.uniform(20, 28)
        time.sleep(random.uniform(0.2, 0.5))
        return self.temperature
