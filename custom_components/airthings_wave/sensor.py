"""Support for Airthings Wave BLE environmental radon sensor."""
import logging
from datetime import timedelta

from .airthings import AirthingsWave

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (ATTR_DEVICE_CLASS, ATTR_ICON, CONF_MAC,
                                 CONF_NAME, CONF_SCAN_INTERVAL,
                                 CONF_UNIT_SYSTEM, CONF_UNIT_SYSTEM_IMPERIAL,
                                 CONF_UNIT_SYSTEM_METRIC, TEMPERATURE,
                                 TEMP_CELSIUS, DEVICE_CLASS_HUMIDITY,
                                 DEVICE_CLASS_ILLUMINANCE,
                                 DEVICE_CLASS_TEMPERATURE,
                                 DEVICE_CLASS_PRESSURE,
                                 DEVICE_CLASS_TIMESTAMP,
                                 EVENT_HOMEASSISTANT_STOP, ILLUMINANCE)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=300)

ATTR_DEVICE_DATE_TIME = 'device_date_time'
ATTR_RADON_LEVEL = 'radon_level'
DEVICE_CLASS_RADON = 'radon'
DEVICE_CLASS_ACCELEROMETER = 'accelerometer'
DEVICE_CLASS_CO2 = 'co2'
DEVICE_CLASS_VOC = 'voc'

ILLUMINANCE_LUX = 'lx'
PERCENT = '%'
SPEED_METRIC_UNITS = 'm/s2'
VOLUME_BECQUEREL = 'Bq/m3'
VOLUME_PICOCURIE = 'pCi/L'
ATM_METRIC_UNITS = 'mbar'
CO2_METRIC_UNITS = 'ppm'
VOC_METRIC_UNITS = 'ppb'

DOMAIN = 'airthings'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_MAC, default=''): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    vol.Optional('plus', default=False): cv.boolean,
})

DEVICE_SENSOR_SPECIFICS = {"date_time": ('time', None, None),
                           "temperature": (TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, None),
                           "humidity": (PERCENT, DEVICE_CLASS_HUMIDITY, None),
                           "pressure": (ATM_METRIC_UNITS, DEVICE_CLASS_PRESSURE, None),
                           "co2": (CO2_METRIC_UNITS, DEVICE_CLASS_CO2, 'mdi:periodic-table-co2'),
                           "voc": (VOC_METRIC_UNITS, DEVICE_CLASS_VOC, 'mdi:cloud'),
                           "illuminance": (ILLUMINANCE_LUX, DEVICE_CLASS_ILLUMINANCE, None),
                           "accelerometer": (SPEED_METRIC_UNITS, DEVICE_CLASS_ACCELEROMETER, 'mdi:vibrate'),
                           "radon_1day_avg": (VOLUME_BECQUEREL, DEVICE_CLASS_RADON, 'mdi:radioactive'),
                           "radon_longterm_avg": (VOLUME_BECQUEREL, DEVICE_CLASS_RADON, 'mdi:radioactive')
                           }


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Airthings sensor."""
    scan_interval = config.get(CONF_SCAN_INTERVAL).total_seconds()
    mac = config.get(CONF_MAC)
    ha_entities = []

    airthings = AirthingsWave(mac, scan_interval, is_plus=config.get('plus'))
    for sensor in airthings.sensors:
        ha_entities.append(AirthingsSensor(mac, sensor.name, airthings, DEVICE_SENSOR_SPECIFICS[sensor.name]))
    add_entities(ha_entities, True)


class AirthingsSensor(Entity):
    """General Representation of an Airthings sensor."""

    def __init__(self, mac, name, device, sensor_specifics):
        """Initialize a sensor."""
        self.device = device
        self._mac = mac
        self._name = name
        self._state = None
        self._sensor_specifics = sensor_specifics

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{}-{}'.format(self._mac, self._name)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._sensor_specifics[2]

    @property
    def device_class(self):
        """Return the icon of the sensor."""
        return self._sensor_specifics[1]

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._sensor_specifics[0]

    @property
    def unique_id(self):
        return '{}-{}'.format(self._mac, self._name)

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        readings = self.device.get_readings()
        if self._name not in readings:
            return
        self._state = readings[self._name]

    @property
    def force_update(self) -> bool:
        """Force updates."""
        return True