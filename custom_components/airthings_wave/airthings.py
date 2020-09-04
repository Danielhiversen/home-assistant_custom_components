import struct
import time

import logging
from datetime import datetime

USE_BLUEPY = True
if USE_BLUEPY:
    import bluepy
else:
    import pygatt
    from pygatt.exceptions import (
        BLEError, NotConnectedError, NotificationTimeout)

from uuid import UUID


_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(0)

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = .5


class Sensor:
    def __init__(self, name, uuid, format_type, unit, scale, indx=None):
        self.name = name
        self.uuid = uuid
        self.format_type = format_type
        self.unit = unit
        self.scale = scale
        self.indx = indx


class AirthingsWave:
    def __init__(self, mac, scan_interval, retry_count=DEFAULT_RETRY_COUNT, is_plus=False) -> None:
        self._mac = mac
        self._is_plus = is_plus
        self._device = None
        self._retry_count = retry_count
        self.sensors = []
        # self.sensors.append(Sensor("date_time", bluepy.btle.UUID(0x2A08), 'HBBBBB', "\t", 0))

        if is_plus:
            self.sensors.append(Sensor("humidity", None, None, "%", 1.0/2, indx=1))
            self.sensors.append(Sensor("radon_1day_avg", None, None, "Bq/m3", 1.0, indx=4))
            self.sensors.append(Sensor("radon_longterm_avg", None, None, "Bq/m3", 1.0, indx=5))
            self.sensors.append(Sensor("temperature", None, None, "ºC", 1.0/100, indx=6))
            self.sensors.append(Sensor("pressure", None, None, "hPa", 1.0/50, indx=7))
            self.sensors.append(Sensor("co2", None, None, "ppm", 1.0, indx=8))
            self.sensors.append(Sensor("voc", None, None, "ppb", 1.0, indx=9))
        else:
            self.sensors.append(Sensor("temperature", "00002a6e-0000-1000-8000-00805f9b34fb", 'h', "ºC", 1.0 / 100.0))
            self.sensors.append(Sensor("humidity", "00002a6f-0000-1000-8000-00805f9b34fb", 'H', "%", 1.0 / 100.0))
            self.sensors.append(Sensor("radon_1day_avg", "b42e01aa-ade7-11e4-89d3-123b93f75cba", 'H', "Bq/m3", 1.0))
            self.sensors.append(Sensor("radon_longterm_avg", "b42e0a4c-ade7-11e4-89d3-123b93f75cba", 'H', "Bq/m3", 1.0))

        self.readings = {}
        self.scan_interval = scan_interval
        self.last_scan = -1

    @property
    def mac(self):
        return self._mac

    def is_connected(self):
        if USE_BLUEPY:
            try:
                return self._device.getState() == "conn"
            except Exception:
                return False
        else:
            return self._device is not None

    def _connect(self) -> None:
        if self.is_connected():
            return
        if USE_BLUEPY:
            try:
                _LOGGER.debug("Connecting to Airthings...")
                self._device = bluepy.btle.Peripheral(self._mac)
                _LOGGER.debug("Connected to Airthings.")
            except bluepy.btle.BTLEException:
                _LOGGER.debug("Failed connecting to Airthings.", exc_info=True)
                self._device = None
                raise
        else:
            _LOGGER.debug("Connecting to Airthings...")
            self._device = pygatt.backends.GATTToolBackend()
            _LOGGER.debug("Connected to Airthings.")

    def _disconnect(self) -> None:
        if not self.is_connected or self._device is None:
            return
        _LOGGER.debug("Disconnecting")
        if USE_BLUEPY:
            try:
                self._device.disconnect()
            except bluepy.btle.BTLEException:
                _LOGGER.warning("Error disconnecting from Airthings.", exc_info=True)
            finally:
                self._device = None
        else:
            try:
                self._device.disconnect()
            except bluepy.btle.BTLEException:
                _LOGGER.warning("Error disconnecting from Airthings.", exc_info=True)
            finally:
                self._device = None

    def get_readings(self):
        if time.monotonic() - self.last_scan < self.scan_interval:
            return self.readings
        self.last_scan = time.monotonic()
        if USE_BLUEPY:
            if self._is_plus:
                return self._get_readings_plus(self._retry_count)
            return self._get_readings(self._retry_count)
        else:
            if self._is_plus:
                return self._get_readings_plus_pygatt(self._retry_count)
            return self._get_readings_pygatt(self._retry_count)

    def _get_readings(self, retry):
        _LOGGER.debug("Reading from Airthings")
        readings = dict()

        try:
            self._connect()
            for sensor in self.sensors:
                char = self._device.getCharacteristics(uuid=sensor.uuid)[0]
                if char.supportsRead():
                    val = char.read()
                    if val is None:
                        continue
                    val = struct.unpack(sensor.format_type, val)
                    if sensor.name == "date_time":
                        readings[sensor.name] = str(datetime(val[0], val[1], val[2], val[3], val[4], val[5]))
                    else:
                        readings[sensor.name] = round(val[0] * sensor.scale, 2)
            self.readings = readings
            return readings
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error talking to Airthings.", exc_info=True)
        finally:
            self._disconnect()
        if retry < 1:
            _LOGGER.error("Airthings communication failed. Stopping trying.", exc_info=True)
            return readings
        _LOGGER.warning("Cannot connect to Airthings. Retrying (remaining: %d)...", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._get_readings(retry - 1)

    def _get_readings_plus(self, retry):
        _LOGGER.debug("Reading from Airthings")
        readings = dict()

        try:
            self._connect()
            char = self._device.getCharacteristics(uuid="b42e2a68-ade7-11e4-89d3-123b93f75cba")[0]
            rawdata = char.read()
            rawdata = struct.unpack('BBBBHHHHHHHH', rawdata)
            if rawdata[0] != 1:
                _LOGGER.error("Invalid version, %s", rawdata)
            k = 1
            for sensor in self.sensors:
                readings[sensor.name] = round(rawdata[sensor.indx] * sensor.scale, 2)
                k += 1
            self.readings = readings
            return readings
        except bluepy.btle.BTLEException:
            _LOGGER.warning("Error talking to Airthings.", exc_info=True)
        finally:
            self._disconnect()
        if retry < 1:
            _LOGGER.error("Airthings communication failed. Stopping trying.", exc_info=True)
            return readings
        _LOGGER.warning("Cannot connect to Airthings. Retrying (remaining: %d)...", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._get_readings_plus(retry - 1)

    def _get_readings_pygatt(self, retry):
        _LOGGER.debug("Reading from Airthings")
        readings = dict()

        try:
            self._connect()
            self._device.start(reset_on_start=False)
            dev = self._device.connect(self._mac, 60)
            _LOGGER.debug("Connected")
            try:
                for sensor in self.sensors:
                    data = dev.char_read(sensor.uuid)
                    val = struct.unpack(sensor.format_type, data)
                    if sensor.name == "date_time":
                        readings[sensor.name] = str(datetime(val[0], val[1], val[2], val[3], val[4], val[5]))
                    else:
                        readings[sensor.name] = round(val[0] * sensor.scale, 2)
                self.readings = readings
                return readings
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.error("connection to {} failed".format(self._mac),  exc_info=True)
            finally:
                dev.disconnect()
        except (BLEError, NotConnectedError, NotificationTimeout):
            _LOGGER.error("Failed to connect",  exc_info=True)
        finally:
            self._device.stop()

        if retry < 1:
            _LOGGER.error("Airthings communication failed. Stopping trying.", exc_info=True)
            return readings
        _LOGGER.warning("Cannot connect to Airthings. Retrying (remaining: %d)...", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._get_readings_pygatt(retry - 1)

    def _get_readings_plus_pygatt(self, retry):
        _LOGGER.debug("Reading from Airthings")
        readings = dict()

        try:
            self._connect()
            self._device.start(reset_on_start=False)
            dev = self._device.connect(self._mac, 60)
            _LOGGER.debug("Connected")
            try:
                data = dev.char_read("b42e2a68-ade7-11e4-89d3-123b93f75cba")
                rawdata = struct.unpack('BBBBHHHHHHHH', data)
                if rawdata[0] != 1:
                    _LOGGER.error("Invalid version, %s", rawdata)
                k = 1
                for sensor in self.sensors:
                    readings[sensor.name] = round(rawdata[sensor.indx] * sensor.scale, 2)
                    k += 1
                self.readings = readings
                return readings
            except (BLEError, NotConnectedError, NotificationTimeout):
                _LOGGER.error("connection to {} failed".format(self._mac),  exc_info=True)
            finally:
                dev.disconnect()
        except (BLEError, NotConnectedError, NotificationTimeout):
            _LOGGER.error("Failed to connect",  exc_info=True)
        finally:
            self._device.stop()

        if retry < 1:
            _LOGGER.error("Airthings communication failed. Stopping trying.", exc_info=True)
            return readings
        _LOGGER.warning("Cannot connect to Airthings. Retrying (remaining: %d)...", retry)
        time.sleep(DEFAULT_RETRY_TIMEOUT)
        return self._get_readings_plus_pygatt(retry - 1)
