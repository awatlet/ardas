from threading import Thread, Event
#from w1thermsensor import W1ThermSensor
from time import sleep
from ardas.fake_sensor import FakeTempSensor


class Sampler(Thread):
    def __init__(self, stop_event, interval, sensor):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__measure_interval = interval
        self.sensor = sensor

    @property
    def measure_interval(self):
        """Gets measure_interval
        """
        return self.__measure_interval

    @measure_interval.setter
    def measure_interval(self, val):
        self.__measure_interval = val

    def run(self):
        while not self.stop_event.isSet():
            print(self.sensor.get_temperature())


# class W1Sampler(Sampler, W1ThermSensor):


if __name__ == '__main__':
    fake = FakeTempSensor()
    stop = Event()
    s = Sampler(stop, 1, fake)
    s.start()
    sleep(3)
    stop.set()
    s.join()