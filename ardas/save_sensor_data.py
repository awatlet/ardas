import logging
import csv
from time import time, gmtime, sleep
from datetime import datetime
import requests.exceptions
from influxdb import InfluxDBClient, exceptions
from os import path, makedirs
from threading import Thread, RLock

from ardas.settings import PIDAS_DIR, DATA_FILE, CSV_HEADER, DATABASE, NB_SENSOR, MEASURE_INTERVAL, SIMULATION_MODE

lock = RLock()



if SIMULATION_MODE == 1:
    from ardas.fake_sensor import FakeTempSensor, generate_temp_sensor
else:
    from w1thermsensor import W1ThermSensor


class ThreadLocalSave(Thread):
    """Thread that save data locally"""
    def __init__(self, file_path, sensors, sleep_time=MEASURE_INTERVAL):
        Thread.__init__(self)
        self.csv_path = file_path
        self.sensors = sensors
        self.sleep_time = sleep_time

    def run(self):
        while 1:
            try:
                if SIMULATION_MODE == 1:
                    for sensor in self.sensors:
                        timestamp = int(time())
                        lock.acquire()
                        with open(self.csv_path, "a") as output_file:
                            writer = csv.writer(output_file)
                            row = sensor.id, sensor.name, sensor.get_temperature(), timestamp
                            writer.writerow(row)
                            lock.release()
                else:
                    for sensor in W1ThermSensor.get_available_sensors():
                        # TODO: set a sensor name
                        timestamp = int(time())
                        lock.acquire()
                        with open(self.csv_path, "a") as output_file:
                            writer = csv.writer(output_file)
                            row = sensor.id, 'T', sensor.get_temperature(), timestamp
                            writer.writerow(row)
                            lock.release()
                sleep(self.sleep_time)

            finally:
                pass


class ThreadRemoteSave(Thread):
    """Thread sending data to remote database"""
    def __init__(self, client, file_path, sleep_time=MEASURE_INTERVAL):
        Thread.__init__(self)
        self.client = client
        self.csv_path = file_path
        self.sleep_time = sleep_time

    def run(self):

        while 1:

            try:
                result_set = self.client.query('select "timestamp" from temperatures order by desc limit 1;')
                results = list(result_set.get_points(measurement='temperatures'))
                if not results:
                    last_timestamp = datetime.utcfromtimestamp(0)
                else:
                    last_timestamp = float(results[0]['timestamp'])
                    last_timestamp = datetime.utcfromtimestamp(last_timestamp)
                new_data = []
                lock.acquire()

                with open(self.csv_path, newline='') as csvfile:
                    csv_data = csv.reader(csvfile, delimiter=',')
                    header = csv_data.__next__()
                    for row in csv_data:

                        row_date = datetime.utcfromtimestamp(int(row[3]))
                        if  row_date > last_timestamp:
                            new_data.append(row)
                lock.release()
                row_count = len(new_data)
                if row_count > 0:
                    try:
                        logging.info("Sending data to remote database…")
                        data = []
                        for i in range(row_count):
                            time_value = datetime.utcfromtimestamp(float(new_data[i][3]))
                            value = float(new_data[i][2])
                            data.append({'measurement': 'temperatures', 'tags': {'sensorID': '%s' % new_data[i][0]},
                                         'time': time_value.strftime('%Y-%m-%d %H:%M:%S %Z'),
                                         'fields': {'value': value, 'timestamp': '%s' % new_data[i][3]}})
                        self.client.write_points(data)  # tag data with sensorID
                    except requests.exceptions.ConnectionError:
                        logging.error("Database connection lost !")

                    except exceptions.InfluxDBClientError as e:
                        logging.error("{}".format(e.content))
            except requests.exceptions.ConnectionError:
                logging.error("Database connection lost !")
            except exceptions.InfluxDBClientError as e:
                logging.error("{}".format(e.content))
            sleep(self.sleep_time)


def main():
    log_path = path.join(PIDAS_DIR, 'logs')
    file_path = path.join(PIDAS_DIR, DATA_FILE)
    if not path.exists(log_path):
        makedirs(log_path)
    logging_level = logging.DEBUG
    logging.Formatter.converter = gmtime
    log_format = '%(asctime)-15s %(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, datefmt='%Y/%m/%d %H:%M:%S UTC', level=logging_level,
                        handlers=[logging.FileHandler(path.join(log_path, 'save_sensor_data.log')),
                                  logging.StreamHandler()])
    logging.info('_____ Started _____')
    logging.info('saving in' + file_path)
    if not path.exists(file_path):
        with open(file_path, "w") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(CSV_HEADER)
    client = InfluxDBClient(DATABASE['HOST'], DATABASE['PORT'], DATABASE['USER'], DATABASE['PASSWORD'],
                             DATABASE['NAME'])
    sensors = []
    if SIMULATION_MODE == 1:
        try:
            last_timestamp = client.query('select "timestamp" from temperatures order by desc limit 1;')
            if not last_timestamp:
                logging.info("Serie is empty, creating new sensors…")
                sensors = generate_temp_sensor(NB_SENSOR)
                logging.info("Sensors generated")
            else:
                try:
                    logging.info("Getting sensors from database…")
                    result_set = client.query('select distinct(sensorID) as sensorID from temperatures ')
                    results = list(result_set.get_points(measurement='temperatures'))
                    for result in results:
                        s = FakeTempSensor()
                        s.id = result['sensorID']
                        sensors.append(s)
                except requests.exceptions.ConnectionError:
                    logging.error("Database connection lost !")
        except requests.exceptions.ConnectionError:
            logging.error("Database connection lost !")
        except exceptions.InfluxDBClientError as e:
            logging.error("{}".format(e.content))
    else:
        sensors = W1ThermSensor.get_available_sensors()

    thread_local_save = ThreadLocalSave(file_path=file_path, sensors=sensors)
    thread_remote_save = ThreadRemoteSave(client, file_path=file_path)
    thread_local_save.start()
    thread_remote_save.start()
    # wait until threads terminates
    thread_local_save.join()
    thread_remote_save.join()


if __name__ == "__main__":
    main()
