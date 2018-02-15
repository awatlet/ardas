from threading import Thread, Event
try:
    from w1thermsensor import W1ThermSensor, errors
except:
    pass
import datetime
from time import sleep
from ardas.fake_sensor import FakeTempSensor, generate_temp_sensor
import queue


class Conditioner(Thread):
    def __init__(self, stop_event, interval, sensors, sampler_queue=None):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.process
        self.pa
        self.queue = sampler_queue

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


class SensorConditioner(Thread):
    def __init__(self, stop_event, sensor_ids=None, processing_method=None, processing_parameters=None,
                 quantity='?', units='?', output_format='%11.4f', log_output=True):
        Thread.__init__(self)
        self.sensor_id = sensor_id
        self.processing_method = processing_method
        self.processing_parameters = processing_parameters
        self.quantity = quantity
        self.units = units
        self.output_format = output_format
        self.log = log_output

    @property
    def sensor_id(self):
        """ Gets and sets sensor id
        """
        return self.__sensor_id

    @sensor_id.setter
    def sensor_id(self, val):
        self.__sensor_id = str(val[:4])

    @property
    def units(self):
        """ Gets and sets sensor units
        """
        return self.__units

    @units.setter
    def units(self, val):
        self.__units = val

    def output(self, value):
        """Outputs an output computed using the processing method and parameters

        :return: processed quantity
        :rtype: float
        """

        output = self.processing_method(value, self.processing_parameters)
        return output

    def output_repr(self, value):
        """Gets a representation of the output

        :return: representation of the processed quantity
        :rtype: string
        """

        try:
            s = self.output_format + ' ' + self.units
            calibrated_output = s % self.output(value)
        except Exception as e:
            calibrated_output = '*** error : %s ***' % e
        assert isinstance(calibrated_output, str)
        return calibrated_output

    def save(self):
        """Save the sensor as a serialized object to a file """
        f_name = cur_dir + '/sensor_' + self.sensor_id + '.ssr'
        if Path(f_name).exists():
            logging.warning('Sensor file ' + f_name + ' already exists, unable to save sensor')
        else:
            with open(f_name, 'wb') as sensor_file:
                dump(self, sensor_file)

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
            # print('Next measure: %s' %datetime.datetime.fromtimestamp(next_sample_time).isoformat())
            for i in self.sensors:
                # print('__________________________________________')
                sample_after[i.name] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
                # print('before %s - %s: %f' % (
                # datetime.datetime.fromtimestamp(sample_before[i.name][0]).isoformat(), i.name, sample_before[i.name][1]))
                # print('after %s - %s: %f' % (
                # datetime.datetime.fromtimestamp(sample_after[i.name][0]).isoformat(), i.name, sample_after[i.name][1]))

                value = sample_before[i.name][1] + (next_sample_time - sample_before[i.name][0]) \
                        / (sample_after[i.name][0] - sample_before[i.name][0]) \
                        * (sample_after[i.name][1] - sample_before[i.name][1])
                sample[i.name] = (next_sample_time, value)
                # print('interpolated %s - %s : %.3f' % (datetime.datetime.fromtimestamp(int(next_sample_time)).isoformat(), i.name, sample[i.name][1]))
                # print('__________________________________________')
                sample_before[i.name] = sample_after[i.name]
                data=({'tags': {'sensor': '%s' % i.name},
                       'time': datetime.datetime.fromtimestamp(sample[i.name][0]).strftime('%Y-%m-%d %H:%M:%S %Z'),
                       'fields': {'value': sample[i.name][1]}})
                self.queue.put(data)
            # print('\n\n')
            next_sample_time = next_sample_time + self.measure_interval
            pause_until(next_sample_time)


if __name__ == '__main__':
    w1temp_queue = queue.Queue()
    fake_sensors = generate_temp_sensor(7)
    stop = Event()
    s = W1Sampler(stop_event=stop, interval=5, sensors=fake_sensors, queue=w1temp_queue)
    s.start()
    k = 0
    kmax = 20
    while k < 20:
        try:
            print(w1temp_queue.get(timeout=0.1))
        except queue.Empty:
            pass
        k +=1
        sleep(1)
    stop.set()
    s.join()
    empty_queue = False
    while not empty_queue:
        try:
            print(w1temp_queue.get(timeout=0.1))
        except queue.Empty:
            empty_queue = True