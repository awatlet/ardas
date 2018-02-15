from threading import Thread, Event
#from w1thermsensor import W1ThermSensor
import datetime
from time import sleep, time
from ardas.fake_sensor import FakeTempSensor, generate_temp_sensor


def pause_until(next):
    """ Pauses until next

    :param next: datetime.datetime.timestamp
    """

    while True:
        now = datetime.datetime.utcnow().timestamp()
        diff = next - now
        if diff <= 0:
            break
        if diff <= 0.1:
            sleep(0.001)
        elif diff <= 0.5:
            sleep(0.01)
        elif diff <= 1.5:
            sleep(0.1)
        else:
            sleep(1)

class Sampler(Thread):
    def __init__(self, stop_event, interval, sensors):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__measure_interval = interval
        self.sensors = sensors

    @property
    def measure_interval(self):
        """ Gets measure_interval
        """
        return self.__measure_interval

    @measure_interval.setter
    def measure_interval(self, val):
        self.__measure_interval = val

    def run(self):
        while not self.stop_event.isSet():
            pass


class W1Sampler(Sampler, FakeTempSensor):  # TODO: use W1ThermSensor instead of FakeTempSensor
    def run(self):
        while not self.stop_event.isSet():
            next_measurement = datetime.datetime.utcnow().timestamp() + self.measure_interval
            for i in self.sensors:
                print('%s - %s: %f' %(datetime.datetime.utcnow().isoformat(), i.name, i.get_temperature()))
            print('__________________________________________')
            pause_until(next_measurement)


if __name__ == '__main__':
    fake_sensors = generate_temp_sensor(7)
    stop = Event()
    s = W1Sampler(stop, 5, fake_sensors)
    s.start()
    sleep(15)
    stop.set()
    s.join()
