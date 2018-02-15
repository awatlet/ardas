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
        sample_before = {}
        sample_after = {}
        sample = {}
        for i in self.sensors:
            sample_before[i.name] = (datetime.datetime.utcnow().timestamp(), self.get_temperature())
            sample_after[i.name] = sample_before[i.name]
            sample[i.name] = sample_before[i.name]
        next_sample_time = datetime.datetime.utcnow().timestamp()
        while not self.stop_event.isSet():
            print('Next measure: %s' %datetime.datetime.fromtimestamp(next_sample_time).isoformat())
            for i in self.sensors:
                print('__________________________________________')
                sample_after[i.name] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
                print('before %s - %s: %f' % (
                datetime.datetime.fromtimestamp(sample_before[i.name][0]).isoformat(), i.name, sample_before[i.name][1]))
                print('after %s - %s: %f' % (
                datetime.datetime.fromtimestamp(sample_after[i.name][0]).isoformat(), i.name, sample_after[i.name][1]))

                value = sample_before[i.name][1] + (next_sample_time - sample_before[i.name][0]) \
                        / (sample_after[i.name][0] - sample_before[i.name][0]) \
                        * (sample_after[i.name][1] - sample_before[i.name][1])
                sample[i.name] = (next_sample_time, value)
                print('interpolated %s - %s : %.3f' % (datetime.datetime.fromtimestamp(int(next_sample_time)).isoformat(), i.name, sample[i.name][1]))
                print('__________________________________________')
                sample_before[i.name] = sample_after[i.name]
            print('\n\n')
            next_sample_time = next_sample_time + self.measure_interval
            pause_until(next_sample_time)


if __name__ == '__main__':
    fake_sensors = generate_temp_sensor(7)
    stop = Event()
    s = W1Sampler(stop, 5, fake_sensors)
    s.start()
    sleep(10)
    stop.set()
    s.join()
