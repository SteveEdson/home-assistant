"""
Hive Integration - climate

"""
import logging, json
import voluptuous as vol
from datetime import datetime
from datetime import timedelta


from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import load_platform
import custom_components.hive as hive
from homeassistant.loader import get_component

DEPENDENCIES = ['hive']

_LOGGER = logging.getLogger(__name__)

        
def setup_platform(hass, config, add_devices, DeviceList, discovery_info=None):
    """Setup Hive climate devices"""
    HiveComponent = get_component('hive')
    
    if len(DeviceList) > 0:
        if "Hive_Device_Heating" in DeviceList:
            add_devices([Hive_Device_Heating(HiveComponent.HiveObjects_Global)])
        if "Hive_Device_HotWater" in DeviceList:    
            add_devices([Hive_Device_HotWater(HiveComponent.HiveObjects_Global)])

class Hive_Device_Heating(ClimateDevice):
    """Hive Heating Device"""
    def __init__(self, HiveComponent_HiveObjects):
        """Initialize the Heating device."""
        self.HiveObjects = HiveComponent_HiveObjects

    @property
    def name(self):
        """Return the name of the heating device"""
        return "Hive Heating"

    @property
    def force_update(self):
        """Return True if state updates should be forced."""
        return False
    
    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement which this heating device uses."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.HiveObjects.Get_Heating_CurrentTemp()

    @property
    def target_temperature(self):
        """Return the target temperature"""
        return self.HiveObjects.Get_Heating_TargetTemp()

    @property
    def min_temp(self):
        """Return minimum temperature."""
        minTemperature = 5
        return minTemperature

    @property
    def max_temp(self):
        """Return the maximum temperature"""
        maxTemperature = 32
        return maxTemperature

    @property
    def operation_list(self):
        """List of the operation modes"""
        return self.HiveObjects.Get_Heating_Operation_Mode_List()

    @property
    def current_operation(self):
        """Return current mode"""
        return self.HiveObjects.Get_Heating_Mode()

    def set_operation_mode(self, operation_mode):
        """Set new Heating mode"""
        self.HiveObjects.Set_Heating_Mode(operation_mode)
        
    def set_temperature(self, **kwargs):
        """Set new target temperature"""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            NewTemperature = kwargs.get(ATTR_TEMPERATURE)
            self.HiveObjects.Set_Heating_TargetTemp(NewTemperature)

    def update(self):
        """Update all Node data frome Hive"""
        self.HiveObjects.UpdateData()

        
class Hive_Device_HotWater(ClimateDevice):
    """Hive HotWater Device"""
    def __init__(self, HiveComponent_HiveObjects):
        """Initialize the HotWater device."""
        self.HiveObjects = HiveComponent_HiveObjects

    @property
    def name(self):
        """Return the name of the HotWater device"""
        return "Hive HotWater"

    @property
    def force_update(self):
        """Return True if state updates should be forced."""
        return False
    
    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement which this HotWater device uses."""
        return TEMP_CELSIUS

    @property
    def operation_list(self):
        """List of the operation modes"""
        return self.HiveObjects.Get_HotWater_Operation_Mode_List()

    @property
    def current_operation(self):
        """Return current mode"""
        return self.HiveObjects.Get_HotWater_Mode()

    def set_operation_mode(self, operation_mode):
        """Set new HotWater mode"""
        self.HiveObjects.Set_HotWater_Mode(operation_mode)
        
    def update(self):
        """Update all Node data frome Hive"""
        self.HiveObjects.UpdateData()
