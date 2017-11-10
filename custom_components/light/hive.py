"""
Hive Integration - light

"""
import logging, json
# import voluptuous as vol
from datetime import datetime
from datetime import timedelta

# Import the device class from the component that you want to support
from homeassistant.components.light import (ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import load_platform
#import custom_components.hive as hive
from homeassistant.loader import get_component

# Home Assistant depends on 3rd party packages for API specific code.
DEPENDENCIES = ['hive']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, DeviceList, discovery_info=None):
    """Setup Hive climate devices"""
    HiveComponent = get_component('hive')

    if len(DeviceList) > 0:
        if "Hive_Device_Light" in DeviceList:
            add_devices([Hive_Device_Light(HiveComponent.HiveObjects_Global)])


class Hive_Device_Light(Light):
    """Hive Active Light Device"""

    def __init__(self, HiveComponent_HiveObjects):
        """Initialize the Light device."""
        self.HiveObjects = HiveComponent_HiveObjects

    @property
    def name(self):
        """Return the display name of this light."""
        return "Hive Active Light"

    @property
    def brightness(self):
        """Brightness of the light (an integer in the range 1-255).

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self.HiveObjects.Get_Light_Brightness()

    @property
    def is_on(self):
        """Return true if light is on."""
        return self.HiveObjects.Get_Light_State()

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        if ATTR_BRIGHTNESS in kwargs:
            TmpNewBrightness = kwargs.get(ATTR_BRIGHTNESS)
        else:
            TmpNewBrightness = 255

        PercentageBrightness = ((TmpNewBrightness / 255) * 100)
        NewBrightness = int(round(PercentageBrightness / 5.0) * 5.0)

        if NewBrightness != 0:
            self.HiveObjects.Set_Light_TurnON(NewBrightness)

    def turn_off(self):
        """Instruct the light to turn off."""
        self.HiveObjects.Set_Light_TurnOFF()

    def update(self):
        """Update all Node data frome Hive"""
        self.HiveObjects.UpdateData()

    @property
    def supported_features(self):
        """Flag supported features."""
        SUPPORTFEATURES = (SUPPORT_BRIGHTNESS)
        return SUPPORTFEATURES