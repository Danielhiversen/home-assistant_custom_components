"""

REboot netgear router when nobody is home


"""
import logging

import datetime

from homeassistant.helpers.event import track_time_change
from homeassistant.util import dt as dt_util

from pynetgear import Netgear

# The domain of your component. Should be equal to the name of your component.
DOMAIN = "netgear_reboot"

# List of component names (string) your component depends upon.
# We depend on group because group will be loaded after all the components that
# initialize devices have been setup.
DEPENDENCIES = ['group', ]

# Shortcut for the logger
_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Setup component."""
    last_trigger = dt_util.now()
    netgear = Netgear(password='PSW')

    def check_netgear(_=None):
        now = dt_util.now()

        if hass.states.get('group.tracker').state == 'home' or (now - hass.states.get('group.tracker').last_updated) < datetime.timedelta(hours=1):
            _LOGGER.error("Netgear reboot home")
            return

        nonlocal last_trigger
        if now - last_trigger < datetime.timedelta(hours=30):
            _LOGGER.error("Netgear reboot %s", now - last_trigger)
            return

        res = netgear.reboot()
        _LOGGER.error("Netgear reboot %s", res)
        last_trigger = dt_util.now()

    track_time_change(hass, check_netgear, second=22, minute=6, hour=[2, 4, 9, 13])
    return True
