# Domoticz MELCloud Home Plugin

Domoticz Python plugin for Mitsubishi Electric air conditioners using the **new MELCloud Home platform**.

> This plugin is intended for **MELCloud Home** and is separate from the older MELCloud Classic integration.

## Features

The plugin automatically discovers compatible Air-to-Air units registered in your MELCloud Home account.

Currently supported:

- Power On / Off
- Operating mode
  - Heat
  - Cool
  - Fan
  - Dry
  - Auto
- Set temperature
- 0.5 °C temperature increments
- Fan speed
  - Level 1–5
  - Auto
  - Silent, if supported
- Horizontal vane control
- Vertical vane control
- Room temperature
- Standby status
- Error status
- Wi-Fi RSSI
- Automatic synchronization with MELCloud Home
- Multiple Air-to-Air units in one MELCloud Home account

The available functions depend on the capabilities of the Mitsubishi Electric unit.

## Requirements

- Domoticz with Python plugin support
- Python 3.11
- MELCloud Home account
- Mitsubishi Electric unit registered in MELCloud Home
- Internet connection
- `aiomelcloudhome==0.1.2`

## Installation

Change to your Domoticz plugins directory:

```bash
cd ~/domoticz/plugins
```

Clone the repository:

```bash
git clone https://github.com/schurgan/domoticz-melcloud-home.git MELCloudHome
```

Install the required Python dependencies locally inside the plugin directory:

```bash
python3 -m pip install --target ~/domoticz/plugins/MELCloudHome/lib -r ~/domoticz/plugins/MELCloudHome/requirements.txt
```

Using a local `lib` directory avoids modifying the system Python installation and also works on systems using PEP 668 externally managed Python environments.

Restart Domoticz:

```bash
sudo systemctl restart domoticz
```

## Domoticz Configuration

Open:

**Setup → Hardware**

Add a new hardware device of type:

**MELCloud Home**

Enter:

- MELCloud Home email address
- MELCloud Home password
- desired refresh interval
- debug level

After adding the hardware, compatible air conditioners should be discovered automatically.

The plugin creates a separate set of Domoticz devices for every discovered air conditioner.

## Created Domoticz Devices

For each air conditioner the plugin currently creates:

| Device | Function |
|---|---|
| Mode | Power and operating mode |
| Fan | Fan speed |
| Temp | Target temperature |
| Vane Horizontal | Horizontal air direction |
| Vane Vertical | Vertical air direction |
| Room Temp | Current room temperature |
| Unit Infos | RSSI, standby, error and current fan information |

## Updating

Change to the plugin directory:

```bash
cd ~/domoticz/plugins/MELCloudHome
```

Pull the latest version:

```bash
git pull
```

If `requirements.txt` has changed, update the local dependencies:

```bash
python3 -m pip install --upgrade --target ~/domoticz/plugins/MELCloudHome/lib -r ~/domoticz/plugins/MELCloudHome/requirements.txt
```

Restart Domoticz:

```bash
sudo systemctl restart domoticz
```

## MELCloud Classic

This plugin does **not** use the old MELCloud Classic API.

For the older MELCloud platform, see the separate Domoticz MELCloud Classic plugin:

https://github.com/schurgan/domoticz-python-melcloud

## Security

MELCloud Home credentials are stored in the Domoticz hardware configuration.

Do not put credentials into `plugin.py` or commit test scripts containing usernames or passwords.

The repository `.gitignore` excludes:

- local test files
- Python caches
- the locally installed `lib/` directory
- `.env` files

## Status

This plugin is currently under active development and testing.

It has been tested with:

- Domoticz on Raspberry Pi
- Python 3.11
- `aiomelcloudhome==0.1.2`
- Mitsubishi Electric Air-to-Air units

## Disclaimer

This is an unofficial community plugin and is not affiliated with or endorsed by Mitsubishi Electric.

MELCloud and MELCloud Home are trademarks of their respective owners.