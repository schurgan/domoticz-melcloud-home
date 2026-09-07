# MELCloud Home Plugin for Domoticz
# Based on the previous MELCloud Classic plugin
# Version: 0.1.0
#
# MELCloud Home API via aiomelcloudhome 0.1.2
# Python 3.11 compatible

"""
<plugin key="MELCloudHome"
        version="0.1.0"
        name="MELCloud Home"
        author="schurgan / ChatGPT"
        description="Mitsubishi Electric MELCloud Home integration">
    <params>
        <param field="Username"
               label="Email"
               width="250px"
               required="true" />

        <param field="Password"
               label="Password"
               width="250px"
               required="true"
               password="true" />

        <param field="Mode1"
               label="Refresh interval"
               width="150px">
            <options>
                <option label="30 Sekunden" value="30"/>
                <option label="1 Minute" value="60"/>
                <option label="2 Minuten" value="120" default="true"/>
                <option label="5 Minuten" value="300"/>
                <option label="10 Minuten" value="600"/>
            </options>
        </param>

        <param field="Mode6"
               label="Debug"
               width="150px">
            <options>
                <option label="None" value="0" default="true"/>
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import os
import sys
import asyncio
import traceback


# ============================================================
# Lokale Python-Bibliotheken
# ============================================================

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(PLUGIN_DIR, "lib")

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)


import Domoticz

from aiohttp import ClientSession
from aiomelcloudhome import MELCloudHome


# ============================================================
# Plugin
# ============================================================

class BasePlugin:

    def __init__(self):

        self.units = []

        self.heartbeat_interval = 10
        self.refresh_seconds = 120
        self.counter = 0

        self.busy = False

        # ----------------------------------------------------
        # Domoticz-Geräte pro Klimagerät
        # ----------------------------------------------------

        self.switches = [
            {
                "id": 1,
                "name": "Mode",
                "type": "selector",
                "image": 16,
                "levels": "Off|Warm|Cold|Vent|Dry|Auto",
            },
            {
                "id": 2,
                "name": "Fan",
                "type": "selector",
                "image": 7,
                "levels": "Level1|Level2|Level3|Level4|Level5|Auto|Silence",
            },
            {
                "id": 3,
                "name": "Temp",
                "type": "selector",
                "image": 15,
                "levels": (
                    "16|16.5|17|17.5|18|18.5|19|19.5|20|20.5|"
                    "21|21.5|22|22.5|23|23.5|24|24.5|25|25.5|"
                    "26|26.5|27|27.5|28|28.5|29|29.5|30|30.5|31"
                ),
            },
            {
                "id": 4,
                "name": "Vane Horizontal",
                "type": "selector",
                "image": 7,
                "levels": "Left|Left Centre|Centre|Right Centre|Right|Swing|Auto",
            },
            {
                "id": 5,
                "name": "Vane Vertical",
                "type": "selector",
                "image": 7,
                "levels": "1|2|3|4|5|Swing|Auto",
            },
            {
                "id": 6,
                "name": "Room Temp",
                "type": "temperature",
            },
            {
                "id": 7,
                "name": "Unit Infos",
                "type": "text",
            },
        ]

        # ----------------------------------------------------
        # MELCloud Home <-> Domoticz Mapping
        # ----------------------------------------------------

        self.mode_from_level = {
            10: "Heat",
            20: "Cool",
            30: "Fan",
            40: "Dry",
            50: "Automatic",
        }

        self.mode_to_level = {
            "Heat": "10",
            "Cool": "20",
            "Fan": "30",
            "Dry": "40",
            "Automatic": "50",
        }

        self.mode_images = {
            "0": 9,
            "10": 15,
            "20": 16,
            "30": 7,
            "40": 11,
            "50": 9,
        }

        self.fan_from_level = {
            0: "Level1",
            10: "Level2",
            20: "Level3",
            30: "Level4",
            40: "Level5",
            50: "Auto",
            60: "Silent",
        }

        self.fan_to_level = {
            "Level1": "0",
            "Level2": "10",
            "Level3": "20",
            "Level4": "30",
            "Level5": "40",
            "Auto": "50",
            "Silent": "60",
            "Silence": "60",
        }

        self.vane_h_from_level = {
            0: "Left",
            10: "LeftCentre",
            20: "Centre",
            30: "RightCentre",
            40: "Right",
            50: "Swing",
            60: "Auto",
        }

        self.vane_h_to_level = {
            "Left": "0",
            "LeftCentre": "10",
            "Left Centre": "10",
            "Centre": "20",
            "RightCentre": "30",
            "Right Centre": "30",
            "Right": "40",
            "Swing": "50",
            "Auto": "60",
        }

        self.vane_v_from_level = {
            0: "Position1",
            10: "Position2",
            20: "Position3",
            30: "Position4",
            40: "Position5",
            50: "Swing",
            60: "Auto",
        }

        self.vane_v_to_level = {
            "Position1": "0",
            "Position2": "10",
            "Position3": "20",
            "Position4": "30",
            "Position5": "40",
            "Swing": "50",
            "Auto": "60",
        }


    # ========================================================
    # Domoticz Start
    # ========================================================

    def onStart(self):

        try:
            Domoticz.Debugging(int(Parameters["Mode6"]))
        except Exception:
            Domoticz.Debugging(0)

        Domoticz.Heartbeat(self.heartbeat_interval)

        try:
            self.refresh_seconds = int(Parameters["Mode1"])
        except Exception:
            self.refresh_seconds = 120

        self.counter = 0

        Domoticz.Log("MELCloud Home Plugin 0.1.0 started.")
        Domoticz.Log(
            "Refresh interval: {} seconds".format(
                self.refresh_seconds
            )
        )

        self.refresh()


    # ========================================================
    # Stop
    # ========================================================

    def onStop(self):

        try:
            loop = getattr(self, "_async_loop", None)

            if loop is not None and not loop.is_closed():
                loop.stop()
                loop.close()

            self._async_loop = None

        except Exception as error:
            Domoticz.Error(
                "MELCloud Home event loop cleanup failed: {}".format(error)
            )

        Domoticz.Log("MELCloud Home Plugin stopped.")


    # ========================================================
    # Heartbeat
    # ========================================================

    def onHeartbeat(self):

        self.counter -= self.heartbeat_interval

        if self.counter <= 0:

            self.counter = self.refresh_seconds

            self.refresh()


    # ========================================================
    # Async aus synchronem Domoticz aufrufen
    # ========================================================

    def run_async(self, coroutine):
        """
        Führt Async-Code innerhalb des Domoticz-Plugin-Threads
        über eine eigene persistente Event-Loop aus.
        """

        try:
            loop = getattr(self, "_async_loop", None)

            if loop is None or loop.is_closed():
                loop = asyncio.new_event_loop()
                self._async_loop = loop

            asyncio.set_event_loop(loop)

            return loop.run_until_complete(coroutine)

        except Exception:
            # Event-Loop im Fehlerfall nicht zerstören,
            # damit der Plugin-Thread weiterlaufen kann.
            raise

    # ========================================================
    # MELCloud Home Status holen
    # ========================================================

    def refresh(self):

        if self.busy:
            Domoticz.Debug(
                "MELCloud Home request already running - skip refresh."
            )
            return

        self.busy = True

        try:

            self.run_async(
                self.async_refresh()
            )

        except Exception as error:

            Domoticz.Error(
                "MELCloud Home refresh failed: {}".format(error)
            )

            Domoticz.Debug(
                traceback.format_exc()
            )

        finally:

            self.busy = False


    async def async_refresh(self):

        username = Parameters["Username"]
        password = Parameters["Password"]

        async with ClientSession() as session:

            async with MELCloudHome(
                username=username,
                password=password,
                session=session,
            ) as client:

                context = await client.get_context()

                found_units = []

                for building in context.buildings:

                    Domoticz.Debug(
                        "Building: {}".format(building.name)
                    )

                    for device in building.air_to_air_units:

                        found_units.append(
                            {
                                "id": device.id,
                                "name": device.name,
                                "object": device,
                            }
                        )

        self.update_unit_list(found_units)

        self.create_domoticz_devices()

        for unit in self.units:

            self.sync_unit(unit)


    # ========================================================
    # Unit-Liste aktualisieren
    # ========================================================

    def update_unit_list(self, found_units):

        old_offsets = {}

        for unit in self.units:
            old_offsets[unit["id"]] = unit["idoffset"]

        new_units = []

        for index, found in enumerate(found_units):

            if found["id"] in old_offsets:
                offset = old_offsets[found["id"]]
            else:
                offset = index * len(self.switches)

            device = found["object"]

            unit = {
                "id": found["id"],
                "name": found["name"],
                "idoffset": offset,

                "power": device.power,
                "operation_mode": self.enum_value(
                    device.operation_mode
                ),

                "set_temperature": device.set_temperature,
                "room_temperature": device.room_temperature,

                "set_fan_speed": self.enum_value(
                    device.set_fan_speed
                ),

                "actual_fan_speed": self.enum_value(
                    device.actual_fan_speed
                ),

                "vane_horizontal": self.enum_value(
                    device.vane_horizontal_direction
                ),

                "vane_vertical": self.enum_value(
                    device.vane_vertical_direction
                ),

                "standby": device.in_standby_mode,
                "error": device.is_in_error,
                "rssi": device.rssi,

                "object": device,
            }

            new_units.append(unit)

        self.units = new_units

        Domoticz.Log(
            "MELCloud Home: {} Air-to-Air device(s) found.".format(
                len(self.units)
            )
        )

        for unit in self.units:

            Domoticz.Log(
                "Found device: {} ({})".format(
                    unit["name"],
                    unit["id"],
                )
            )


    # ========================================================
    # Enum -> Text
    # ========================================================

    def enum_value(self, value):

        if value is None:
            return None

        try:
            return value.value
        except Exception:
            return str(value)


    # ========================================================
    # Domoticz-Geräte erzeugen
    # ========================================================

    def create_domoticz_devices(self):

        for unit in self.units:

            offset = unit["idoffset"]

            for switch in self.switches:

                domoticz_unit = offset + switch["id"]

                if domoticz_unit in Devices:
                    continue

                name = "{} - {}".format(
                    unit["name"],
                    switch["name"],
                )

                if switch["type"] == "selector":

                    options = {
                        "LevelNames": switch["levels"],
                        "LevelOffHidden": "false",
                        "SelectorStyle": "1",
                    }

                    Domoticz.Device(
                        Name=name,
                        Unit=domoticz_unit,
                        TypeName="Selector Switch",
                        Image=switch["image"],
                        Options=options,
                        Used=1,
                    ).Create()

                elif switch["type"] == "temperature":

                    Domoticz.Device(
                        Name=name,
                        Unit=domoticz_unit,
                        TypeName="Temperature",
                        Used=1,
                    ).Create()

                elif switch["type"] == "text":

                    Domoticz.Device(
                        Name=name,
                        Unit=domoticz_unit,
                        TypeName="Text",
                        Used=1,
                    ).Create()


    # ========================================================
    # Status -> Domoticz
    # ========================================================

    def sync_unit(self, unit):

        offset = unit["idoffset"]

        power = bool(unit["power"])

        if power:
            nvalue = 1
            mode_level = self.mode_to_level.get(
                unit["operation_mode"],
                "0"
            )
        else:
            nvalue = 0
            mode_level = "0"

        image = self.mode_images.get(
            mode_level,
            9
        )

        # Mode
        self.update_device(
            offset + 1,
            nvalue,
            mode_level,
            image=image,
        )

        # Fan
        fan_level = self.fan_to_level.get(
            unit["set_fan_speed"],
            "50"
        )

        self.update_device(
            offset + 2,
            nvalue,
            fan_level,
        )

        # Solltemperatur
        temp_level = self.temperature_to_level(
            unit["set_temperature"]
        )

        self.update_device(
            offset + 3,
            nvalue,
            temp_level,
        )

        # Horizontal
        vane_h_level = self.vane_h_to_level.get(
            unit["vane_horizontal"],
            "60"
        )

        self.update_device(
            offset + 4,
            nvalue,
            vane_h_level,
        )

        # Vertikal
        vane_v_level = self.vane_v_to_level.get(
            unit["vane_vertical"],
            "60"
        )

        self.update_device(
            offset + 5,
            nvalue,
            vane_v_level,
        )

        # Raumtemperatur
        if unit["room_temperature"] is not None:

            self.update_device(
                offset + 6,
                0,
                str(unit["room_temperature"]),
            )

        # Informationen
        info = self.make_unit_info(unit)

        self.update_device(
            offset + 7,
            0,
            info,
        )


    # ========================================================
    # Temperatur Mapping
    # ========================================================

    def temperature_to_level(self, temperature):

        if temperature is None:
            return "0"

        try:

            temp = float(temperature)

            level = round(
                (temp - 16.0) * 20
            )

            level = max(
                0,
                min(300, level)
            )

            return str(level)

        except Exception:

            return "0"


    def level_to_temperature(self, level):

        return 16.0 + (float(level) / 20.0)


    # ========================================================
    # Unit Info
    # ========================================================

    def make_unit_info(self, unit):

        values = []

        if unit["rssi"] is not None:
            values.append(
                "RSSI: {} dBm".format(unit["rssi"])
            )

        values.append(
            "Standby: {}".format(
                "Ja" if unit["standby"] else "Nein"
            )
        )

        values.append(
            "Fehler: {}".format(
                "Ja" if unit["error"] else "Nein"
            )
        )

        if unit["actual_fan_speed"] is not None:

            values.append(
                "Fan aktuell: {}".format(
                    unit["actual_fan_speed"]
                )
            )

        return " | ".join(values)


    # ========================================================
    # Domoticz Device Update
    # ========================================================

    def update_device(
        self,
        unit,
        nvalue,
        svalue,
        image=None,
    ):

        if unit not in Devices:
            return

        kwargs = {
            "nValue": nvalue,
            "sValue": str(svalue),
        }

        if image is not None:
            kwargs["Image"] = image

        Devices[unit].Update(**kwargs)


    # ========================================================
    # Domoticz Command
    # ========================================================

    def onCommand(
        self,
        Unit,
        Command,
        Level,
        Hue,
    ):

        Domoticz.Log(
            "MELCloud Home command: Unit={} Command={} Level={}".format(
                Unit,
                Command,
                Level,
            )
        )

        current_unit = None
        switch_id = None

        for unit in self.units:

            offset = unit["idoffset"]

            if offset < Unit <= offset + len(self.switches):

                current_unit = unit
                switch_id = Unit - offset
                break

        if current_unit is None:

            Domoticz.Error(
                "MELCloud Home: device for Domoticz Unit {} not found.".format(
                    Unit
                )
            )

            return

        if switch_id in (6, 7):

            Domoticz.Log(
                "This device is read-only."
            )
            return

        try:

            self.run_async(
                self.async_command(
                    current_unit,
                    switch_id,
                    int(Level),
                )
            )

            # Direkt danach neu einlesen
            self.refresh()

        except Exception as error:

            Domoticz.Error(
                "MELCloud Home command failed: {}".format(
                    error
                )
            )

            Domoticz.Debug(
                traceback.format_exc()
            )


    # ========================================================
    # MELCloud Home Command
    # ========================================================

    async def async_command(
        self,
        unit,
        switch_id,
        level,
    ):

        username = Parameters["Username"]
        password = Parameters["Password"]

        async with ClientSession() as session:

            async with MELCloudHome(
                username=username,
                password=password,
                session=session,
            ) as client:

                # Aktuelles Gerät erneut holen.
                context = await client.get_context()

                device = None

                for building in context.buildings:

                    for item in building.air_to_air_units:

                        if item.id == unit["id"]:
                            device = item
                            break

                    if device is not None:
                        break

                if device is None:

                    raise RuntimeError(
                        "MELCloud Home device not found."
                    )

                # --------------------------------------------
                # Mode / Power
                # --------------------------------------------

                if switch_id == 1:

                    if level == 0:

                        Domoticz.Log(
                            "Switch OFF {}".format(unit["name"])
                        )

                        await client.control_ata_unit(
                            device.id,
                            power=False,
                        )

                    else:

                        mode_name = self.mode_from_level.get(
                            level
                        )

                        if mode_name is None:

                            raise RuntimeError(
                                "Unknown mode level: {}".format(
                                    level
                                )
                            )

                        current_mode = device.operation_mode

                        if current_mode is None:

                            raise RuntimeError(
                                "No operation mode enum available."
                            )

                        enum_class = type(current_mode)

                        mode_value = enum_class(
                            mode_name
                        )

                        Domoticz.Log(
                            "Set {} to mode {}".format(
                                unit["name"],
                                mode_name,
                            )
                        )

                        await client.control_ata_unit(
                            device.id,
                            power=True,
                            operation_mode=mode_value,
                        )

                # --------------------------------------------
                # Fan
                # --------------------------------------------

                elif switch_id == 2:

                    fan_name = self.fan_from_level.get(
                        level
                    )

                    if fan_name is None:

                        raise RuntimeError(
                            "Unknown fan level: {}".format(
                                level
                            )
                        )

                    current_fan = device.set_fan_speed

                    if current_fan is None:

                        raise RuntimeError(
                            "No fan-speed enum available."
                        )

                    enum_class = type(current_fan)

                    fan_value = enum_class(
                        fan_name
                    )

                    Domoticz.Log(
                        "Set {} fan to {}".format(
                            unit["name"],
                            fan_name,
                        )
                    )

                    await client.control_ata_unit(
                        device.id,
                        set_fan_speed=fan_value,
                    )

                # --------------------------------------------
                # Solltemperatur
                # --------------------------------------------

                elif switch_id == 3:

                    temperature = self.level_to_temperature(
                        level
                    )

                    Domoticz.Log(
                        "Set {} temperature to {:.1f}".format(
                            unit["name"],
                            temperature,
                        )
                    )

                    await client.control_ata_unit(
                        device.id,
                        set_temperature=temperature,
                    )

                # --------------------------------------------
                # Horizontal vane
                # --------------------------------------------

                elif switch_id == 4:

                    vane_name = self.vane_h_from_level.get(
                        level
                    )

                    if vane_name is None:

                        raise RuntimeError(
                            "Unknown horizontal vane level."
                        )

                    current_vane = (
                        device.vane_horizontal_direction
                    )

                    if current_vane is None:

                        raise RuntimeError(
                            "Horizontal vane not supported."
                        )

                    enum_class = type(current_vane)

                    vane_value = enum_class(
                        vane_name
                    )

                    Domoticz.Log(
                        "Set {} horizontal vane to {}".format(
                            unit["name"],
                            vane_name,
                        )
                    )

                    await client.control_ata_unit(
                        device.id,
                        vane_horizontal_direction=vane_value,
                    )

                # --------------------------------------------
                # Vertical vane
                # --------------------------------------------

                elif switch_id == 5:

                    vane_name = self.vane_v_from_level.get(
                        level
                    )

                    if vane_name is None:

                        raise RuntimeError(
                            "Unknown vertical vane level."
                        )

                    current_vane = (
                        device.vane_vertical_direction
                    )

                    if current_vane is None:

                        raise RuntimeError(
                            "Vertical vane not supported."
                        )

                    enum_class = type(current_vane)

                    vane_value = enum_class(
                        vane_name
                    )

                    Domoticz.Log(
                        "Set {} vertical vane to {}".format(
                            unit["name"],
                            vane_name,
                        )
                    )

                    await client.control_ata_unit(
                        device.id,
                        vane_vertical_direction=vane_value,
                    )


# ============================================================
# Domoticz Callbacks
# ============================================================

global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(
        Unit,
        Command,
        Level,
        Hue,
    )
