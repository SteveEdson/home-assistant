"""
Hive Integration - Platform

"""
import logging, json
import voluptuous as vol
from datetime import datetime
from datetime import timedelta
import requests

from homeassistant.util import Throttle
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import load_platform

REQUIREMENTS = ['requests==2.11.1']

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'hive'
HiveComponent = None


HIVE_NODE_UPDATE_INTERVAL_DEFAULT = 120
HIVE_NODE_UPDATE_INTERVAL = timedelta(seconds=HIVE_NODE_UPDATE_INTERVAL_DEFAULT)
MINUTES_BETWEEN_LOGONS = 15

Current_Node_Attribute_Values = {"Header" : "HeaderText"}

class Hive_Nodes:
    Hub = []
    Receiver = []
    Thermostat = []
    Heating = []
    HotWater = []
    Light = []
    
class Hive_Session:
    SessionID = ""
    Session_Logon_DateTime = datetime(2017,3,16,21,0,0)
    AccountDetails = ""
    UserName = ""
    Password = ""
    Nodes = Hive_Nodes()

class Hive_API_URLS:
    Base = ""
    Login = ""
    Users = ""
    Nodes = ""

class Hive_API_Headers:
    Accept_Key = ""
    Accept_Value = ""
    Client_Key = ""
    Client_Value = ""
    ContentType_Key = ""
    ContentType_Value = ""
    SessionID_Key = ""
    SessionID_Value = ""

class Hive_API_Details:
    URLs = Hive_API_URLS()
    Headers = Hive_API_Headers()
    Caller = ""
    CurrentTemperature = 0

    
HiveAPI_Details = Hive_API_Details()
HiveSession_Current = Hive_Session()

def Initialise_App():
    HiveAPI_Details.Caller = "Hive Web Dashboard"

    HiveAPI_Details.URLs.Base = "https://api-prod.bgchprod.info:443/omnia"
    HiveAPI_Details.URLs.Login = "/auth/sessions"
    HiveAPI_Details.URLs.Users = "/users"
    HiveAPI_Details.URLs.Nodes = "/nodes"

    HiveAPI_Details.Headers.Accept_Key = "Accept"
    HiveAPI_Details.Headers.Accept_Value = "application/vnd.alertme.zoo-6.1+json"
    HiveAPI_Details.Headers.Client_Key = "X-Omnia-Client"
    HiveAPI_Details.Headers.Client_Value = "Hive Web Dashboard"
    HiveAPI_Details.Headers.ContentType_Key = "content-type"
    HiveAPI_Details.Headers.ContentType_Value = "application/vnd.alertme.zoo-6.1+json"
    HiveAPI_Details.Headers.SessionID_Key = "X-Omnia-Access-Token"
    HiveAPI_Details.Headers.SessionID_Value = None

def Hive_API_JsonCall (RequestType, RequestURL, JsonStringContent):
    API_Headers = {HiveAPI_Details.Headers.ContentType_Key:HiveAPI_Details.Headers.ContentType_Value,HiveAPI_Details.Headers.Accept_Key:HiveAPI_Details.Headers.Accept_Value,HiveAPI_Details.Headers.Client_Key:HiveAPI_Details.Headers.Client_Value,HiveAPI_Details.Headers.SessionID_Key:HiveAPI_Details.Headers.SessionID_Value}
    JSON_Response = ""

    try:
        if RequestType == "POST":
            JSON_Response = requests.post(HiveAPI_Details.URLs.Base + RequestURL, data=JsonStringContent, headers=API_Headers)
        elif RequestType == "GET":
            JSON_Response = requests.get(HiveAPI_Details.URLs.Base + RequestURL, data=JsonStringContent, headers=API_Headers)
        elif RequestType == "PUT":
            JSON_Response = requests.put(HiveAPI_Details.URLs.Base + RequestURL, data=JsonStringContent, headers=API_Headers)
        else:
            _LOGGER.error("Unknown RequestType : %s", RequestType)
    except:
        JSON_Response = "No response to JSON Hive API request"
        _LOGGER.error("Error making JSON call to Hive API : %s", JSON_Response)

    return JSON_Response


def Hive_API_Logon():
    HiveSession_Current.SessionID = None

    JsonStringContent = '{"sessions":[{"username":"' + HiveSession_Current.UserName + '","password":"' + HiveSession_Current.Password + '","caller":"' + HiveAPI_Details.Caller + '"}]}'
    API_Response_Login = Hive_API_JsonCall ("POST", HiveAPI_Details.URLs.Login, JsonStringContent)
    API_Response_Login_Parsed = json.loads(API_Response_Login.text)
    
    #API_Response_Login = 400 = logon failure
    #API_Response_Login = 200 = Login success

    if 'sessions' in API_Response_Login.text:
        HiveAPI_Details.Headers.SessionID_Value = API_Response_Login_Parsed["sessions"][0]["sessionId"]
        HiveSession_Current.SessionID = HiveAPI_Details.Headers.SessionID_Value
        HiveSession_Current.Session_Logon_DateTime = datetime.now()
    else:
        HiveSession_Current.SessionID = None
        _LOGGER.error("Hive API login failed with error : %s", API_Response_Login)

    
def Private_Get_Heating_CurrentTemp():
    Heating_CurrentTemp_Return = 0
    Heating_CurrentTemp_tmp = 0
    Heating_CurrentTemp_Found = False
        
    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "temperature" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["temperature"]:
            Heating_CurrentTemp_tmp = HiveSession_Current.Nodes.Heating[0]["attributes"]["temperature"]["displayValue"]
            Heating_CurrentTemp_Found = True
            
    if Heating_CurrentTemp_Found == True:
        Current_Node_Attribute_Values["Heating_CurrentTemp"] = Heating_CurrentTemp_tmp
        Heating_CurrentTemp_Return = Heating_CurrentTemp_tmp
    else:
        if "Heating_CurrentTemp" in Current_Node_Attribute_Values:
            Heating_CurrentTemp_Return = Current_Node_Attribute_Values.get("Heating_CurrentTemp")
        else:
            Heating_CurrentTemp_Return = 0
        
    return Heating_CurrentTemp_Return
    
def Private_Get_Heating_CurrentTemp_State_Attributes():
    State_Attibutes = {}
    Temperature_Current = 0
    Temperature_Target = 0
    Temperature_Difference = 0
    
    if len(HiveSession_Current.Nodes.Heating) > 0:
        Temperature_Current = Private_Get_Heating_CurrentTemp()
        Temperature_Target = Private_Get_Heating_TargetTemp()
        
        if Temperature_Target > Temperature_Current:
            Temperature_Difference = Temperature_Target - Temperature_Current
        
            State_Attibutes.update({"Current Temperature": Temperature_Current})
            State_Attibutes.update({"Target Temperature": Temperature_Target})
            State_Attibutes.update({"Temperature Difference": Temperature_Difference})
    return State_Attibutes

def Private_Get_Heating_TargetTemp():
    Heating_TargetTemp_Return = 0
    Heating_TargetTemp_tmp = 0
    Heating_TargetTemp_Found = False
   
    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "targetHeatTemperature" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["targetHeatTemperature"]:
            Heating_TargetTemp_tmp = HiveSession_Current.Nodes.Heating[0]["attributes"]["targetHeatTemperature"]["displayValue"]
            Heating_TargetTemp_Found = True
        
        if Heating_TargetTemp_tmp == 1:
            if "attributes" in HiveSession_Current.Nodes.Heating[0] and "frostProtectTemperature" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["frostProtectTemperature"]:
                Heating_TargetTemp_tmp = HiveSession_Current.Nodes.Heating[0]["attributes"]["frostProtectTemperature"]["displayValue"]
                Heating_TargetTemp_Found = True
        
    if Heating_TargetTemp_Found == True:
        Current_Node_Attribute_Values["Heating_TargetTemp"] = Heating_TargetTemp_tmp
        Heating_TargetTemp_Return = Heating_TargetTemp_tmp
    else:
        if "Heating_TargetTemp" in Current_Node_Attribute_Values:
            Heating_TargetTemp_Return = Current_Node_Attribute_Values.get("Heating_TargetTemp")
        else:
            Heating_TargetTemp_Return = 0

    return Heating_TargetTemp_Return
    
def Private_Get_Heating_TargetTemperature_State_Attributes():
    State_Attibutes = {}
    
    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "targetHeatTemperature" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "reportChangedTime" in HiveSession_Current.Nodes.Heating[0]["attributes"]["targetHeatTemperature"]:
            Heating_TargetTempChanged_tmp = HiveSession_Current.Nodes.Heating[0]["attributes"]["targetHeatTemperature"]["reportChangedTime"]
            Heating_TargetTempChanged_tmp_UTC_DT = Private_Epoch_TimeMilliseconds_To_datetime(Heating_TargetTempChanged_tmp)

            State_Attibutes.update({"Target Temperature changed": Private_Convert_DateTime_StateDisplayString(Heating_TargetTempChanged_tmp_UTC_DT)})
    return State_Attibutes

def Private_Convert_DateTime_StateDisplayString(DateTimeToConvert):
    ReturnString = ""
    SecondsDifference = (datetime.now() - DateTimeToConvert).total_seconds()
        
    if SecondsDifference < 60:
        ReturnString = str(round(SecondsDifference)) + " seconds ago"
    elif SecondsDifference >= 60 and SecondsDifference <= (60 * 60):
        ReturnString = str(round(SecondsDifference / 60)) + " minutes ago"
    elif SecondsDifference > (60 * 60) and SecondsDifference <= (60 * 60 * 24):
        ReturnString = DateTimeToConvert.strftime('%H:%M')
    else:
        ReturnString = DateTimeToConvert.strftime('%H:%M %d-%b-%Y')
    
    return ReturnString

def Private_Epoch_TimeMilliseconds_To_datetime(EpochStringMilliseconds):
    EpochStringseconds = EpochStringMilliseconds / 1000
    DateTimeUTC = datetime.fromtimestamp(EpochStringseconds)
    return DateTimeUTC

def Private_Get_Heating_State():
    Heating_State_Return = "OFF"
    Heating_State_tmp = "OFF"
    Heating_State_Found = False

    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "stateHeatingRelay" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["stateHeatingRelay"]:
            Heating_State_tmp = HiveSession_Current.Nodes.Heating[0]["attributes"]["stateHeatingRelay"]["displayValue"]
            Heating_State_Found = True
    
    if Heating_State_Found == True:
        Current_Node_Attribute_Values["Heating_State"] = Heating_State_tmp
        Heating_State_Return = Heating_State_tmp
    else:
        if "Heating_State" in Current_Node_Attribute_Values:
            Heating_State_Return = Current_Node_Attribute_Values.get("Heating_State")
        else:
            Heating_State_Return = "UNKNOWN"
                
    return Heating_State_Return
    
def Private_Get_Heating_State_State_Attributes():
    State_Attibutes = {}
    CurrentHeatingState = Private_Get_Heating_State()

    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "stateHeatingRelay" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "reportChangedTime" in HiveSession_Current.Nodes.Heating[0]["attributes"]["stateHeatingRelay"]:
            Heating_Heating_State_Changed_tmp = HiveSession_Current.Nodes.Heating[0]["attributes"]["stateHeatingRelay"]["reportChangedTime"]
            Heating_Heating_State_Changed_tmp_UTC_DT = Private_Epoch_TimeMilliseconds_To_datetime(Heating_Heating_State_Changed_tmp)
            
            StateAttributeString = ""
            if CurrentHeatingState == "ON":
                StateAttributeString = "Heating State ON since"
            elif CurrentHeatingState == "OFF":
                StateAttributeString = "Heating State OFF since"
            else:
                StateAttributeString = "Current Heating State since"
            
            State_Attibutes.update({StateAttributeString: Private_Convert_DateTime_StateDisplayString(Heating_Heating_State_Changed_tmp_UTC_DT)})

    return State_Attibutes

def Private_Get_Heating_Mode():
    Heating_Mode_Return = "UNKNOWN"
    Heating_Mode_tmp = "UNKNOWN"
    Heating_Mode_Found = False

    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "activeHeatCoolMode" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]:
            if "attributes" in HiveSession_Current.Nodes.Heating[0] and "activeScheduleLock" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]:
                if "attributes" in HiveSession_Current.Nodes.Heating[0] and "activeOverrides" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]:
                    if "attributes" in HiveSession_Current.Nodes.Heating[0] and "previousConfiguration" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"] and "mode" in HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]:
                    
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == False and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            Heating_Mode_tmp = "SCHEDULE"
                            Heating_Mode_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            Heating_Mode_tmp = "MANUAL"
                            Heating_Mode_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "OFF" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == False and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            Heating_Mode_tmp = "OFF"
                            Heating_Mode_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1:
                            Heating_Mode_tmp = "SCHEDULE"
                            Heating_Mode_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "AUTO":
                            Heating_Mode_tmp = "SCHEDULE"
                            Heating_Mode_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "MANUAL":
                            Heating_Mode_tmp = "MANUAL"
                            Heating_Mode_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "OFF":
                            Heating_Mode_tmp = "OFF"
                            Heating_Mode_Found = True

    if Heating_Mode_Found == True:
        Current_Node_Attribute_Values["Heating_Mode"] = Heating_Mode_tmp
        Heating_Mode_Return = Heating_Mode_tmp
    else:
        if "Heating_Mode" in Current_Node_Attribute_Values:
            Heating_Mode_Return = Current_Node_Attribute_Values.get("Heating_Mode")
        else:
            Heating_Mode_Return = "UNKNOWN"
                
    return Heating_Mode_Return
    
def Private_Get_Heating_Mode_State_Attributes():
    State_Attibutes = {}

    return State_Attibutes

    
def Private_Get_Heating_Operation_Mode_List():
    HiveHeating_operation_list = ["SCHEDULE", "MANUAL", "OFF"]
    return HiveHeating_operation_list
    
def Private_Get_Heating_Boost():
    Heating_Boost_Return = "UNKNOWN"
    Heating_Boost_tmp = "UNKNOWN"
    Heating_Boost_Found = False

    if len(HiveSession_Current.Nodes.Heating) > 0:
        if "attributes" in HiveSession_Current.Nodes.Heating[0] and "activeHeatCoolMode" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]:
            if "attributes" in HiveSession_Current.Nodes.Heating[0] and "activeScheduleLock" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]:
                if "attributes" in HiveSession_Current.Nodes.Heating[0] and "activeOverrides" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]:
                    if "attributes" in HiveSession_Current.Nodes.Heating[0] and "previousConfiguration" in HiveSession_Current.Nodes.Heating[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"] and "mode" in HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]:
                    
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == False and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            Heating_Boost_tmp = "OFF"
                            Heating_Boost_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            Heating_Boost_tmp = "OFF"
                            Heating_Boost_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "OFF" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == False and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            Heating_Boost_tmp = "OFF"
                            Heating_Boost_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1:
                            Heating_Boost_tmp = "OFF"
                            Heating_Boost_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "AUTO":
                            Heating_Boost_tmp = "ON"
                            Heating_Boost_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "MANUAL":
                            Heating_Boost_tmp = "ON"
                            Heating_Boost_Found = True
                        if HiveSession_Current.Nodes.Heating[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.Heating[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.Heating[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.Heating[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "OFF":
                            Heating_Boost_tmp = "ON"
                            Heating_Boost_Found = True
                            
    if Heating_Boost_Found == True:
        Current_Node_Attribute_Values["Heating_Boost"] = Heating_Boost_tmp
        Heating_Boost_Return = Heating_Boost_tmp
    else:
        if "Heating_Boost" in Current_Node_Attribute_Values:
            Heating_Boost_Return = Current_Node_Attribute_Values.get("Heating_Boost")
        else:
            Heating_Boost_Return = "UNKNOWN"
            
    return Heating_Boost_Return

def Private_Get_Heating_Boost_State_Attributes():
    State_Attibutes = {}

    return State_Attibutes    
    
def Private_Get_HotWater_Mode():
    HotWater_Mode_Return = "UNKNOWN"
    HotWater_Mode_tmp = "UNKNOWN"
    HotWater_Mode_Found = False

    if len(HiveSession_Current.Nodes.HotWater) > 0:
        if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "activeHeatCoolMode" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]:
            if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "activeScheduleLock" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]:
                if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "activeOverrides" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]:
                    if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "previousConfiguration" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"] and "mode" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["displayValue"]:
                    
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["displayValue"] == False and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            HotWater_Mode_tmp = "SCHEDULE"
                            HotWater_Mode_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "HEAT" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            HotWater_Mode_tmp = "ON"
                            HotWater_Mode_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "OFF" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["displayValue"] == False and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["displayValue"]) == 0:
                            HotWater_Mode_tmp = "OFF"
                            HotWater_Mode_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "AUTO":
                            HotWater_Mode_tmp = "SCHEDULE"
                            HotWater_Mode_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "MANUAL":
                            HotWater_Mode_tmp = "ON"
                            HotWater_Mode_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["displayValue"] == "BOOST" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["displayValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["displayValue"]) == 1 and HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["displayValue"]["mode"] == "OFF":
                            HotWater_Mode_tmp = "OFF"
                            HotWater_Mode_Found = True
                            
    if HotWater_Mode_Found == True:
        Current_Node_Attribute_Values["HotWater_Mode"] = HotWater_Mode_tmp
        HotWater_Mode_Return = HotWater_Mode_tmp
    else:
        if "HotWater_Mode" in Current_Node_Attribute_Values:
            HotWater_Mode_Return = Current_Node_Attribute_Values.get("HotWater_Mode")
        else:
            HotWater_Mode_Return = "UNKNOWN"

    return HotWater_Mode_Return
    
def Private_Get_HotWater_Mode_State_Attributes():
    State_Attibutes = {}

    return State_Attibutes
 
def Private_Get_HotWater_Operation_Mode_List():
    HiveHotWater_operation_list = ["SCHEDULE", "ON", "OFF"]
    return HiveHotWater_operation_list
    
def Private_Get_HotWater_Boost():
    HotWater_Boost_Return = "UNKNOWN"
    HotWater_Boost_tmp = "UNKNOWN"
    HotWater_Boost_Found = False

    if len(HiveSession_Current.Nodes.HotWater) > 0:
        if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "activeHeatCoolMode" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "reportedValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]:
            if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "activeScheduleLock" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "reportedValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]:
                if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "activeOverrides" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "reportedValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]:
                    if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "previousConfiguration" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "reportedValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"] and "mode" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["reportedValue"]:
                    
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["reportedValue"] == "HEAT" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["reportedValue"] == False and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["reportedValue"]) == 0:
                            HotWater_Boost_tmp = "OFF"
                            HotWater_Boost_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["reportedValue"] == "HEAT" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["reportedValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["reportedValue"]) == 0:
                            HotWater_Boost_tmp = "OFF"
                            HotWater_Boost_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["reportedValue"] == "OFF" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["reportedValue"] == False and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["reportedValue"]) == 0:
                            HotWater_Boost_tmp = "OFF"
                            HotWater_Boost_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["reportedValue"] == "BOOST" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["reportedValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["reportedValue"]) == 1 and HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["reportedValue"]["mode"] == "AUTO":
                            HotWater_Boost_tmp = "ON"
                            HotWater_Boost_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["reportedValue"] == "BOOST" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["reportedValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["reportedValue"]) == 1 and HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["reportedValue"]["mode"] == "MANUAL":
                            HotWater_Boost_tmp = "ON"
                            HotWater_Boost_Found = True
                        if HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeHeatCoolMode"]["reportedValue"] == "BOOST" and HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeScheduleLock"]["reportedValue"] == True and len(HiveSession_Current.Nodes.HotWater[0]["attributes"]["activeOverrides"]["reportedValue"]) == 1 and HiveSession_Current.Nodes.HotWater[0]["attributes"]["previousConfiguration"]["reportedValue"]["mode"] == "OFF":
                            HotWater_Boost_tmp = "ON"
                            HotWater_Boost_Found = True
                            
    if HotWater_Boost_Found == True:
        Current_Node_Attribute_Values["HotWater_Boost"] = HotWater_Boost_tmp
        HotWater_Boost_Return = HotWater_Boost_tmp
    else:
        if "HotWater_Boost" in Current_Node_Attribute_Values:
            HotWater_Boost_Return = Current_Node_Attribute_Values.get("HotWater_Boost")
        else:
            HotWater_Boost_Return = "UNKNOWN"

    return HotWater_Boost_Return
    
def Private_Get_HotWater_Boost_State_Attributes():
    State_Attibutes = {}

    return State_Attibutes   
    
def Private_Get_HotWater_State():
    HotWater_State_Return = "OFF"
    HotWater_State_tmp = "OFF"
    HotWater_State_Found = False

    if len(HiveSession_Current.Nodes.HotWater) > 0:
        if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "stateHotWaterRelay" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["stateHotWaterRelay"]:
            HotWater_State_tmp = HiveSession_Current.Nodes.HotWater[0]["attributes"]["stateHotWaterRelay"]["displayValue"]
            HotWater_State_Found = True
            
    if HotWater_State_Found == True:
        Current_Node_Attribute_Values["HotWater_State"] = HotWater_State_tmp
        HotWater_State_Return = HotWater_State_tmp
    else:
        if "HotWater_State" in Current_Node_Attribute_Values:
            HotWater_State_Return = Current_Node_Attribute_Values.get("HotWater_State")
        else:
            HotWater_State_Return = "UNKNOWN"
            
    return HotWater_State_Return
    
def Private_Get_HotWater_State_State_Attributes():
    State_Attibutes = {}
    CurrentHotWaterState = Private_Get_HotWater_State()

    if len(HiveSession_Current.Nodes.HotWater) > 0:
        if "attributes" in HiveSession_Current.Nodes.HotWater[0] and "stateHotWaterRelay" in HiveSession_Current.Nodes.HotWater[0]["attributes"] and "reportChangedTime" in HiveSession_Current.Nodes.HotWater[0]["attributes"]["stateHotWaterRelay"]:
            Heating_HotWater_State_Changed_tmp = HiveSession_Current.Nodes.HotWater[0]["attributes"]["stateHotWaterRelay"]["reportChangedTime"]
            Heating_HotWater_State_Changed_tmp_UTC_DT = Private_Epoch_TimeMilliseconds_To_datetime(Heating_HotWater_State_Changed_tmp)
            
            StateAttributeString = ""
            if CurrentHotWaterState == "ON":
                StateAttributeString = "HotWater State ON since"
            elif CurrentHotWaterState == "OFF":
                StateAttributeString = "HotWater State OFF since"
            else:
                StateAttributeString = "Current HotWater State since"
            
            State_Attibutes.update({StateAttributeString: Private_Convert_DateTime_StateDisplayString(Heating_HotWater_State_Changed_tmp_UTC_DT)})

    return State_Attibutes

def Private_Get_Thermostat_BatteryLevel():
    Thermostat_BatteryLevel_Return = 0
    Thermostat_BatteryLevel_tmp = 0
    Thermostat_BatteryLevel_Found = False

    if len(HiveSession_Current.Nodes.Thermostat) > 0:
        if "attributes" in HiveSession_Current.Nodes.Thermostat[0] and "batteryLevel" in HiveSession_Current.Nodes.Thermostat[0]["attributes"] and "displayValue" in HiveSession_Current.Nodes.Thermostat[0]["attributes"]["batteryLevel"]:
            Thermostat_BatteryLevel_tmp = HiveSession_Current.Nodes.Thermostat[0]["attributes"]["batteryLevel"]["displayValue"]
            Thermostat_BatteryLevel_Found = True
            
    if Thermostat_BatteryLevel_Found == True:
        Current_Node_Attribute_Values["Thermostat_BatteryLevel"] = Thermostat_BatteryLevel_tmp
        Thermostat_BatteryLevel_Return = Thermostat_BatteryLevel_tmp
    else:
        if "Thermostat_BatteryLevel" in Current_Node_Attribute_Values:
            Thermostat_BatteryLevel_Return = Current_Node_Attribute_Values.get("Thermostat_BatteryLevel")
        else:
            Thermostat_BatteryLevel_Return = 0
            
    return Thermostat_BatteryLevel_Return

def Private_Get_Light_State():
    Light_State_Return = 0
    Light_State_tmp = 0
    Light_State_Found = False

    if len(HiveSession_Current.Nodes.Light) > 0:
        if "attributes" in HiveSession_Current.Nodes.Light[0] and "state" in \
                HiveSession_Current.Nodes.Light[0]["attributes"] and "displayValue" in \
                HiveSession_Current.Nodes.Light[0]["attributes"]["state"]:
            Light_State_tmp = HiveSession_Current.Nodes.Light[0]["attributes"]["state"]["displayValue"]
            Light_State_Found = True

    if Light_State_Found == True:
        Current_Node_Attribute_Values["Light_State"] = Light_State_tmp
        Light_State_Return = Light_State_tmp
    else:
        if "Light_State" in Current_Node_Attribute_Values:
            Light_State_Return = Current_Node_Attribute_Values.get("Light_State")
        else:
            Light_State_Return = "UNKNOWN"
    if Light_State_Return == "ON":
        return True
    else:
        return False

def Private_Get_Light_Brightness():
    Tmp_Brightness_Return = 0
    Light_Brightness_Return = 0
    Light_Brightness_tmp = 0
    Light_Brightness_Found = False

    if len(HiveSession_Current.Nodes.Light) > 0:
        if "attributes" in HiveSession_Current.Nodes.Light[0] and "brightness" in \
                HiveSession_Current.Nodes.Light[0]["attributes"] and "displayValue" in \
                HiveSession_Current.Nodes.Light[0]["attributes"]["brightness"]:
            Light_Brightness_tmp = HiveSession_Current.Nodes.Light[0]["attributes"]["brightness"]["displayValue"]
            Light_Brightness_Found = True

    if Light_Brightness_Found == True:
        Current_Node_Attribute_Values["Light_Brightness"] = Light_Brightness_tmp
        Tmp_Brightness_Return = Light_Brightness_tmp
        Light_Brightness_Return = ((Tmp_Brightness_Return / 100) * 255)
    else:
        if "Light_Brightness" in Current_Node_Attribute_Values:
            Tmp_Brightness_Return = Current_Node_Attribute_Values.get("Light_Brightness")
            Light_Brightness_Return = ((Tmp_Brightness_Return / 100) * 255)
        else:
            Light_Brightness_Return = 0

    return Light_Brightness_Return

@Throttle(HIVE_NODE_UPDATE_INTERVAL)
def Hive_API_Get_Nodes_RL():
    Hive_API_Get_Nodes()

def Hive_API_Get_Nodes_NL():
    Hive_API_Get_Nodes()
    
def Hive_API_Get_Nodes():
    CurrentTime = datetime.now()
    SecondsSinceLastLogon = (HiveSession_Current.Session_Logon_DateTime - CurrentTime).total_seconds()
    MinutesSinceLastLogon = int(round(SecondsSinceLastLogon / 60))

    if MinutesSinceLastLogon >= MINUTES_BETWEEN_LOGONS:
        Hive_API_Logon()
    elif HiveSession_Current.SessionID == None:
        Hive_API_Logon()

    if HiveSession_Current.SessionID != None:
        tmp_Hub = []
        tmp_Receiver = []
        tmp_Thermostat = []
        tmp_Heating = []
        tmp_HotWater = []
        tmp_Light = []
        
        API_Response_Nodes = Hive_API_JsonCall ("GET", HiveAPI_Details.URLs.Nodes, "")

        if hasattr(API_Response_Nodes, 'text'):
            if '"nodes"' in API_Response_Nodes.text:
                HiveNodes_Parsed = json.loads(API_Response_Nodes.text)["nodes"]

                for aNode in HiveNodes_Parsed:
                    if "nodeType" in aNode:
                        if aNode["nodeType"] == "http://alertme.com/schema/json/node.class.hub.json#":
                            tmp_Hub.append(aNode)
                        elif aNode["nodeType"] == "http://alertme.com/schema/json/node.class.thermostatui.json#":
                            if "stateHeatingRelay" not in aNode["attributes"] and "stateHotWaterRelay" not in aNode["attributes"] and "supportsHotWater" not in aNode["attributes"]:
                                tmp_Thermostat.append(aNode)
                        elif aNode["nodeType"] == "http://alertme.com/schema/json/node.class.thermostat.json#":
                            if "stateHeatingRelay" not in aNode["attributes"] and "stateHotWaterRelay" not in aNode["attributes"] and "supportsHotWater" not in aNode["attributes"]:
                                tmp_Receiver.append(aNode)
                            elif "stateHeatingRelay" in aNode["attributes"] and "stateHotWaterRelay" not in aNode["attributes"] and "supportsHotWater" in aNode["attributes"]:
                                tmp_Heating.append(aNode)
                            elif "stateHeatingRelay" not in aNode["attributes"] and "stateHotWaterRelay" in aNode["attributes"] and "supportsHotWater" in aNode["attributes"]:
                                tmp_HotWater.append(aNode)
                        elif aNode["nodeType"] == "http://alertme.com/schema/json/node.class.light.json#":
                            tmp_Light.append(aNode)

                if len(tmp_Hub) > 0:
                    HiveSession_Current.Nodes.Hub = tmp_Hub
                if len(tmp_Receiver) > 0:
                    HiveSession_Current.Nodes.Receiver = tmp_Receiver
                if len(tmp_Thermostat) > 0:
                    HiveSession_Current.Nodes.Thermostat = tmp_Thermostat
                if len(tmp_Heating) > 0:
                    HiveSession_Current.Nodes.Heating = tmp_Heating
                if len(tmp_HotWater) > 0:
                    HiveSession_Current.Nodes.HotWater = tmp_HotWater
                if len(tmp_Light) > 0:
                    HiveSession_Current.Nodes.Light = tmp_Light
    else:
        _LOGGER.error("No Session ID")

        
def Private_Hive_API_Set_Temperature(NewTemperature):
    CurrentTime = datetime.now()
    SecondsSinceLastLogon = (HiveSession_Current.Session_Logon_DateTime - CurrentTime).total_seconds()
    MinutesSinceLastLogon = int(round(SecondsSinceLastLogon / 60))

    if MinutesSinceLastLogon >= MINUTES_BETWEEN_LOGONS:
        Hive_API_Logon()
    elif HiveSession_Current.SessionID == None:
        Hive_API_Logon()

    API_Response_SetTemperature = ""
    
    API_Response_SetTemperature_Parsed = None
    
    if HiveSession_Current.SessionID != None:
        if len(HiveSession_Current.Nodes.Heating) > 0:
            if "id" in HiveSession_Current.Nodes.Heating[0]:
                JsonStringContent = '{"nodes": [{"attributes": {"targetHeatTemperature": {"targetValue": ' + str(NewTemperature) + '}}}]}'
                HiveAPI_URL = HiveAPI_Details.URLs.Nodes + "/" + HiveSession_Current.Nodes.Heating[0]["id"]
                API_Response_SetTemperature = Hive_API_JsonCall ("PUT", HiveAPI_URL, JsonStringContent)
                API_Response_SetTemperature_Parsed = json.loads(API_Response_SetTemperature.text)["nodes"]
                    
    tmp_API_Response_SetTemperature = str(API_Response_SetTemperature)
     
    if tmp_API_Response_SetTemperature == "<Response [200]>":
        if len(HiveSession_Current.Nodes.Heating) > 0:
            HiveSession_Current.Nodes.Heating[0] = API_Response_SetTemperature_Parsed[0]
        return True
    else:
        return False

def Private_Hive_API_Set_Heating_Mode(NewMode):
    CurrentTime = datetime.now()
    SecondsSinceLastLogon = (HiveSession_Current.Session_Logon_DateTime - CurrentTime).total_seconds()
    MinutesSinceLastLogon = int(round(SecondsSinceLastLogon / 60))

    if MinutesSinceLastLogon >= MINUTES_BETWEEN_LOGONS:
        Hive_API_Logon()
    elif HiveSession_Current.SessionID == None:
        Hive_API_Logon()

    API_Response_SetMode_Parsed = None
    API_Response_SetMode = ""

    if HiveSession_Current.SessionID != None:
        if len(HiveSession_Current.Nodes.Heating) > 0:
            if "id" in HiveSession_Current.Nodes.Heating[0]:
                if NewMode == "SCHEDULE":
                    JsonStringContent = '{"nodes": [{"attributes": {"activeHeatCoolMode": {"targetValue": "HEAT"},"activeScheduleLock": {"targetValue": false}}}]}'
                elif NewMode == "MANUAL":
                    JsonStringContent = '{"nodes": [{"attributes": {"activeHeatCoolMode": {"targetValue": "HEAT"},"activeScheduleLock": {"targetValue": true}}}]}'
                elif NewMode == "OFF":
                    JsonStringContent = '{"nodes": [{"attributes": {"activeHeatCoolMode": {"targetValue": "OFF"},"activeScheduleLock": {"targetValue": false}}}]}'
                
                if NewMode == "SCHEDULE" or NewMode == "MANUAL" or NewMode == "OFF":
                    HiveAPI_URL = HiveAPI_Details.URLs.Nodes + "/" + HiveSession_Current.Nodes.Heating[0]["id"]
                    API_Response_SetMode = Hive_API_JsonCall ("PUT", HiveAPI_URL, JsonStringContent)
                    API_Response_SetMode_Parsed = json.loads(API_Response_SetMode.text)["nodes"]
     
    tmp_API_Response_SetMode = str(API_Response_SetMode)
     
    if tmp_API_Response_SetMode == "<Response [200]>":
        if len(HiveSession_Current.Nodes.Heating) > 0:
            HiveSession_Current.Nodes.Heating[0] = API_Response_SetMode_Parsed[0]
            
        return True
    else:
        return False

def Private_Hive_API_Set_HotWater_Mode(NewMode):
    CurrentTime = datetime.now()
    SecondsSinceLastLogon = (HiveSession_Current.Session_Logon_DateTime - CurrentTime).total_seconds()
    MinutesSinceLastLogon = int(round(SecondsSinceLastLogon / 60))

    if MinutesSinceLastLogon >= MINUTES_BETWEEN_LOGONS:
        Hive_API_Logon()
    elif HiveSession_Current.SessionID == None:
        Hive_API_Logon()

    API_Response_SetMode_Parsed = None
    API_Response_SetMode = ""

    if HiveSession_Current.SessionID != None:
        if len(HiveSession_Current.Nodes.HotWater) > 0:
            if "id" in HiveSession_Current.Nodes.HotWater[0]:
                if NewMode == "SCHEDULE":
                    JsonStringContent = '{"nodes": [{"attributes": {"activeHeatCoolMode": {"targetValue": "HEAT"},"activeScheduleLock": {"targetValue": false}}}]}'
                elif NewMode == "ON":
                    JsonStringContent = '{"nodes": [{"attributes": {"activeHeatCoolMode": {"targetValue": "HEAT"},"activeScheduleLock": {"targetValue": true}}}]}'
                elif NewMode == "OFF":
                    JsonStringContent = '{"nodes": [{"attributes": {"activeHeatCoolMode": {"targetValue": "OFF"},"activeScheduleLock": {"targetValue": false}}}]}'
                
                if NewMode == "SCHEDULE" or NewMode == "ON" or NewMode == "OFF":
                    HiveAPI_URL = HiveAPI_Details.URLs.Nodes + "/" + HiveSession_Current.Nodes.HotWater[0]["id"]
                    API_Response_SetMode = Hive_API_JsonCall ("PUT", HiveAPI_URL, JsonStringContent)
                    API_Response_SetMode_Parsed = json.loads(API_Response_SetMode.text)["nodes"]
     
    tmp_API_Response_SetMode = str(API_Response_SetMode)
     
    if tmp_API_Response_SetMode == "<Response [200]>":
        if len(HiveSession_Current.Nodes.HotWater) > 0:
            HiveSession_Current.Nodes.HotWater[0] = API_Response_SetMode_Parsed[0]

        return True
    else:
        return False
        
def Private_Hive_API_Set_Light_TurnON(NewBrightness):
    CurrentTime = datetime.now()
    SecondsSinceLastLogon = (HiveSession_Current.Session_Logon_DateTime - CurrentTime).total_seconds()
    MinutesSinceLastLogon = int(round(SecondsSinceLastLogon / 60))

    if MinutesSinceLastLogon >= MINUTES_BETWEEN_LOGONS:
        Hive_API_Logon()
    elif HiveSession_Current.SessionID == None:
        Hive_API_Logon()

    API_Response_SetMode_Parsed = None
    API_Response_SetMode = ""

    if HiveSession_Current.SessionID != None:
        if len(HiveSession_Current.Nodes.Light) > 0:
            if "id" in HiveSession_Current.Nodes.Light[0]:
                JsonStringContent = '{"nodes": [{"attributes": {"state": {"targetValue": "ON"}, "brightness": {"targetValue": ' + str(
                    NewBrightness) + '}}}]}'
                HiveAPI_URL = HiveAPI_Details.URLs.Nodes + "/" + HiveSession_Current.Nodes.Light[0]["id"]
                API_Response_SetMode = Hive_API_JsonCall("PUT", HiveAPI_URL, JsonStringContent)
                API_Response_SetMode_Parsed = json.loads(API_Response_SetMode.text)["nodes"]

    tmp_API_Response_SetMode = str(API_Response_SetMode)

    if tmp_API_Response_SetMode == "<Response [200]>":
        if len(HiveSession_Current.Nodes.Light) > 0:
            HiveSession_Current.Nodes.Light[0] = API_Response_SetMode_Parsed[0]

        return True
    else:
        return False

def Private_Hive_API_Set_Light_TurnOFF():
    CurrentTime = datetime.now()
    SecondsSinceLastLogon = (HiveSession_Current.Session_Logon_DateTime - CurrentTime).total_seconds()
    MinutesSinceLastLogon = int(round(SecondsSinceLastLogon / 60))

    if MinutesSinceLastLogon >= MINUTES_BETWEEN_LOGONS:
        Hive_API_Logon()
    elif HiveSession_Current.SessionID == None:
        Hive_API_Logon()

    API_Response_SetMode_Parsed = None
    API_Response_SetMode = ""

    if HiveSession_Current.SessionID != None:
        if len(HiveSession_Current.Nodes.Light) > 0:
            if "id" in HiveSession_Current.Nodes.Light[0]:
                JsonStringContent = '{"nodes": [{"attributes": {"state": {"targetValue": "OFF"}}}]}'
                HiveAPI_URL = HiveAPI_Details.URLs.Nodes + "/" + HiveSession_Current.Nodes.Light[0]["id"]
                API_Response_SetMode = Hive_API_JsonCall("PUT", HiveAPI_URL, JsonStringContent)
                API_Response_SetMode_Parsed = json.loads(API_Response_SetMode.text)["nodes"]

    tmp_API_Response_SetMode = str(API_Response_SetMode)

    if tmp_API_Response_SetMode == "<Response [200]>":
        if len(HiveSession_Current.Nodes.Light) > 0:
            HiveSession_Current.Nodes.Light[0] = API_Response_SetMode_Parsed[0]

        return True
    else:
        return False
        
def setup(hass, config):
    """Setup the Hive platform"""
    HiveSession_Current.UserName = None
    HiveSession_Current.Password = None
    
    hive_config = config[DOMAIN]

    if "username" in hive_config and "password" in hive_config:
        HiveSession_Current.UserName = config[DOMAIN]['username']
        HiveSession_Current.Password = config[DOMAIN]['password']
    else:
        _LOGGER.error("Missing UserName or Password in config")
    
    if "minutes_between_updates" in hive_config:
        tmp_MINUTES_BETWEEN_UPDATES = config[DOMAIN]['minutes_between_updates']
    else:
        tmp_MINUTES_BETWEEN_UPDATES = 5
        
    tmp_SECONDS_BETWEEN_UPDATES = tmp_MINUTES_BETWEEN_UPDATES * 60
    HIVE_NODE_UPDATE_INTERVAL = timedelta(seconds=tmp_SECONDS_BETWEEN_UPDATES)

    if HiveSession_Current.UserName is None or HiveSession_Current.Password is None:
        _LOGGER.error("Missing UserName or Password in Hive Session details")
    else:
        Initialise_App()
        Hive_API_Logon()
        if HiveSession_Current.SessionID != None:
            Hive_API_Get_Nodes_NL()

    ConfigDevices = []
    
    if "devices" in hive_config:
        ConfigDevices = config[DOMAIN]['devices']

    DEVICECOUNT = 0
        
    DeviceList_Sensor = []
    DeviceList_Climate = []
    DeviceList_Light = []
    
    if len(HiveSession_Current.Nodes.Heating) > 0:
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_heating" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Climate.append("Hive_Device_Heating")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_heating_currenttemperature" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_Heating_CurrentTemperature")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_heating_targettemperature" in ConfigDevices):    
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_Heating_TargetTemperature")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_heating_state" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_Heating_State")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_heating_mode" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_Heating_Mode")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_heating_boost" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_Heating_Boost")

    if len(HiveSession_Current.Nodes.HotWater) > 0:
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_hotwater" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Climate.append("Hive_Device_HotWater")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_hotwater_state" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_HotWater_State")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_hotwater_mode" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_HotWater_Mode")
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_hotwater_boost" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_HotWater_Boost")

    if len(HiveSession_Current.Nodes.Thermostat) > 0:
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_thermostat_batterylevel" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Sensor.append("Hive_Device_Thermostat_BatteryLevel")
            
    if len(HiveSession_Current.Nodes.Light) > 0:
        if len(ConfigDevices) == 0 or (len(ConfigDevices) > 0 and "hive_active_light" in ConfigDevices):
            DEVICECOUNT = DEVICECOUNT + 1
            DeviceList_Light.append("Hive_Device_Light")

    global HiveObjects_Global

    try:
        HiveObjects_Global = HiveObjects()
    except RuntimeError:
        return False
            
    if len(DeviceList_Sensor) > 0 or len(DeviceList_Climate) > 0 or len(DeviceList_Light) > 0:
        if len(DeviceList_Sensor) > 0:
            load_platform(hass, 'sensor', DOMAIN, DeviceList_Sensor)
        if len(DeviceList_Climate) > 0:
            load_platform(hass, 'climate', DOMAIN, DeviceList_Climate)
        if len(DeviceList_Light) > 0:
            load_platform(hass, 'light', DOMAIN, DeviceList_Light)
        return True

class HiveObjects():
    def __init__(self):
        """Initialize HiveObjects."""
        
    def UpdateData(self):
        Hive_API_Get_Nodes_RL()
        
    def Get_Heating_CurrentTemp(self):
        return Private_Get_Heating_CurrentTemp()
        
    def Get_Heating_CurrentTemp_State_Attributes(self):
        return Private_Get_Heating_CurrentTemp_State_Attributes()
        
    def Get_Heating_TargetTemp(self):
        return Private_Get_Heating_TargetTemp()
        
    def Get_Heating_TargetTemperature_State_Attributes(self):
        return Private_Get_Heating_TargetTemperature_State_Attributes()
        
    def Set_Heating_TargetTemp(self, NewTemperature):
        if NewTemperature is not None:
            SetTempResult = Private_Hive_API_Set_Temperature(NewTemperature)
        
    def Get_Heating_State(self):
        return Private_Get_Heating_State()
        
    def Get_Heating_State_State_Attributes(self):
        return Private_Get_Heating_State_State_Attributes()
        
    def Get_Heating_Mode(self):
        return Private_Get_Heating_Mode()
        
    def Set_Heating_Mode(self, NewOperationMode):
        SetModeResult = Private_Hive_API_Set_Heating_Mode(NewOperationMode)
        
    def Get_Heating_Mode_State_Attributes(self):
        return Private_Get_Heating_Mode_State_Attributes()
        
    def Get_Heating_Operation_Mode_List(self):
        return Private_Get_Heating_Operation_Mode_List()

    def Get_Heating_Boost(self):
        return Private_Get_Heating_Boost()
        
    def Get_Heating_Boost_State_Attributes(self):
        return Private_Get_Heating_Boost_State_Attributes()
        
    def Get_HotWater_State(self):
        return Private_Get_HotWater_State()
        
    def Get_HotWater_State_State_Attributes(self):
        return Private_Get_HotWater_State_State_Attributes()
        
    def Get_HotWater_Mode(self):
        return Private_Get_HotWater_Mode()
        
    def Get_HotWater_Mode_State_Attributes(self):
        return Private_Get_HotWater_Mode_State_Attributes()
        
    def Set_HotWater_Mode(self, NewOperationMode):
        SetModeResult = Private_Hive_API_Set_HotWater_Mode(NewOperationMode)
        
    def Get_HotWater_Operation_Mode_List(self):
        return Private_Get_HotWater_Operation_Mode_List()
        
    def Get_HotWater_Boost(self):
        return Private_Get_HotWater_Boost()
        
    def Get_HotWater_Boost_State_Attributes(self):
        return Private_Get_HotWater_Boost_State_Attributes()
        
    def Get_Thermostat_BatteryLevel(self):
        return Private_Get_Thermostat_BatteryLevel()
        
    def Get_Light_State(self):
        return Private_Get_Light_State()

    def Get_Light_Brightness(self):
        return Private_Get_Light_Brightness()

    def Set_Light_TurnON(self, NewBrightness):
        SetModeResult =  Private_Hive_API_Set_Light_TurnON(NewBrightness)

    def Set_Light_TurnOFF(self):
        return Private_Hive_API_Set_Light_TurnOFF()
        