import random
import time
import datetime


class Fake1WireSensor(object):
    """Generic fake 1-Wire sensor"""
    def __init__(self, seller_id='00-00000', id=None):
        """Generate a unique id from an hexadecimal timestamp"""
        self.__id = id
        self.seller_id = seller_id
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
        self.id = self.seller_id + hex(int((datetime.datetime.utcnow().timestamp() * 1000000) % 16 ** 7))


class FakeTempSensor(Fake1WireSensor):
    """Fake 1-Wire temperature sensor default is DS18B20"""
    def __init__(self):
        Fake1WireSensor.__init__(self, seller_id='28-00000', id=None)
        self.temperature = 0.

    def get_temperature(self):
        self.temperature = random.uniform(20, 28)
        time.sleep(random.uniform(0.2, 0.5))
        return self.temperature
