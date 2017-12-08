"""
Support for the Hive devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/hive/
"""
import logging

from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_COLOR_TEMP,
                                            SUPPORT_BRIGHTNESS,
                                            SUPPORT_COLOR_TEMP,
                                            SUPPORT_RGB_COLOR, Light)

DEPENDENCIES = ['hive']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, hivedevice, discovery_info=None):
    """Set up Hive light devices."""
    session = hass.data.get('DATA_HIVE')

    add_devices([HiveDeviceLight(hass, session, hivedevice)])


class HiveDeviceLight(Light):
    """Hive Active Light Device."""

    def __init__(self, hass, Session, HiveDevice):
        """Initialize the Light device."""
        self.node_id = HiveDevice["Hive_NodeID"]
        self.node_name = HiveDevice["Hive_NodeName"]
        self.device_type = HiveDevice["HA_DeviceType"]
        self.node_device_type = HiveDevice["Hive_DeviceType"]
        self.hass = hass
        self.session = Session
        self.session.switch = self.session.core.Switch()

        self.hass.bus.listen('Event_Hive_NewNodeData', self.handle_event)

    def handle_event(self, event):
        """Handle the new event."""
        if self.device_type + "." + self.node_id not in str(event):
            self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the display name of this light."""
        return self.node_name

    @property
    def min_mireds(self):
        """Return the coldest color_temp that this light supports."""
        if self.node_device_type == "tuneablelight" \
                or self.node_device_type == "colourtuneablelight":
            return self.session.light.get_min_colour_temp(self.node_id)

    @property
    def max_mireds(self):
        """Return the warmest color_temp that this light supports."""
        if self.node_device_type == "tuneablelight" \
                or self.node_device_type == "colourtuneablelight":
            return self.session.light.get_max_colour_temp(self.node_id)

    @property
    def color_temp(self):
        """Return the CT color value in mireds."""
        if self.node_device_type == "tuneablelight" \
                or self.node_device_type == "colourtuneablelight":
            return self.session.light.get_color_temp(self.node_id)

    @property
    def brightness(self):
        """Brightness of the light (an integer in the range 1-255)."""
        return self.session.light.get_brightness(self.node_id)

    @property
    def is_on(self):
        """Return true if light is on."""
        return self.session.light.get_state(self.node_id)

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        new_brightness = None
        new_color_temp = None
        if ATTR_BRIGHTNESS in kwargs:
            tmp_new_brightness = kwargs.get(ATTR_BRIGHTNESS)
            percentage_brightness = ((tmp_new_brightness / 255) * 100)
            new_brightness = int(round(percentage_brightness / 5.0) * 5.0)
            if new_brightness == 0:
                new_brightness = 5
        if ATTR_COLOR_TEMP in kwargs:
            tmp_new_color_temp = kwargs.get(ATTR_COLOR_TEMP)
            new_color_temp = round(1000000 / tmp_new_color_temp)

        if new_brightness is not None:
            self.session.light.set_brightness(self.node_id, new_brightness)
        elif new_color_temp is not None:
            self.session.light.set_colour_temp(self.node_id, new_color_temp)
        else:
            self.session.light.turn_on(self.node_id)

        eventsource = self.device_type + "." + self.node_id
        self.hass.bus.fire('Event_Hive_NewNodeData',
                           {"EventSource": eventsource})

    def turn_off(self):
        """Instruct the light to turn off."""
        self.session.light.turn_off(self.node_id)
        eventsource = self.device_type + "." + self.node_id
        self.hass.bus.fire('Event_Hive_NewNodeData',
                           {"EventSource": eventsource})

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = None
        if self.node_device_type == "warmwhitelight":
            supported_features = SUPPORT_BRIGHTNESS
        elif self.node_device_type == "tuneablelight":
            supported_features = (SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP)
        elif self.node_device_type == "colourtuneablelight":
            supported_features = (
                SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP | SUPPORT_RGB_COLOR)

        return supported_features
