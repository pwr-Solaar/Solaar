---
title: List of HID++ 2.0 features
layout: page
---

# Feature status
See functions in hidpp20.py and settings_templates.py

Feature                                | ID       | Status             | Notes
---------------------------------------|----------|:------------------:|------
`ROOT`                                 | `0x0000` | :heavy_check_mark: | System
`FEATURE_SET`                          | `0x0001` | :heavy_check_mark: | System
`FEATURE_INFO`                         | `0x0002` | :heavy_check_mark: | System
`DEVICE_FW_VERSION`                    | `0x0003` | :heavy_check_mark: | `get_firmware`, read only
`DEVICE_UNIT_ID`                       | `0x0004` | :x:                |
`DEVICE_NAME`                          | `0x0005` | :heavy_check_mark: | `get_kind`, `get_name`, read only
`DEVICE_GROUPS`                        | `0x0006` | :x:                |
`DEVICE_FRIENDLY_NAME`                 | `0x0007` | :x:                |
`KEEP_ALIVE`                           | `0x0008` | :x:                |
`RESET`                                | `0x0020` | :x:                | aka "Config Change"
`CRYPTO_ID`                            | `0x0021` | :x:                |
`TARGET_SOFTWARE`                      | `0x0030` | :x:                |
`WIRELESS_SIGNAL_STRENGTH`             | `0x0080` | :x:                |
`DFUCONTROL_LEGACY`                    | `0x00C0` | :x:                |
`DFUCONTROL_UNSIGNED`                  | `0x00C1` | :x:                |
`DFUCONTROL_SIGNED`                    | `0x00C2` | :x:                |
`DFU`                                  | `0x00D0` | :x:                |
`BATTERY_STATUS`                       | `0x1000` | :heavy_check_mark: | `get_battery`, read only
`BATTERY_VOLTAGE`                      | `0x1001` | :heavy_check_mark: | `get_voltage`, read only
`CHARGING_CONTROL`                     | `0x1010` | :x:                |
`LED_CONTROL`                          | `0x1300` | :x:                |
`GENERIC_TEST`                         | `0x1800` | :x:                |
`DEVICE_RESET`                         | `0x1802` | :x:                |
`OOBSTATE`                             | `0x1805` | :x:                |
`CONFIG_DEVICE_PROPS`                  | `0x1806` | :x:                |
`CHANGE_HOST`                          | `0x1814` | :x:                | :wrench:
`HOSTS_INFO`                           | `0x1815` | :heavy_plus_sign:  | `get_host_names`, partial listing only
`BACKLIGHT`                            | `0x1981` | :x:                |
`BACKLIGHT2`                           | `0x1982` | :heavy_check_mark: | `_feature_backlight2`
`BACKLIGHT3`                           | `0x1983` | :x:                |
`PRESENTER_CONTROL`                    | `0x1A00` | :x:                |
`SENSOR_3D`                            | `0x1A01` | :x:                |
`REPROG_CONTROLS`                      | `0x1B00` | :heavy_plus_sign:  | `get_keys`, only listing
`REPROG_CONTROLS_V2`                   | `0x1B01` | :x:                |
`REPROG_CONTROLS_V2_2`                 | `0x1B02` | :x:                |
`REPROG_CONTROLS_V3`                   | `0x1B03` | :x:                |
`REPROG_CONTROLS_V4`                   | `0x1B04` | :heavy_plus_sign:  | `get_keys`, _feature_reprogrammable_keys
`REPORT_HID_USAGE`                     | `0x1BC0` | :x:                |
`PERSISTENT_REMAPPABLE_ACTION`         | `0x1C00` | :x:                | :wrench:
`WIRELESS_DEVICE_STATUS`               | `0x1D4B` | :x:                | status reporting from device
`REMAINING_PAIRING`                    | `0x1DF0` | :x:                |
`FIRMWARE_PROPERTIES`                  | `0x1F1F` | :x:                |
`ADC_MEASUREMENT`                      | `0x1F20` | :x:                |
`LEFT_RIGHT_SWAP`                      | `0x2001` | :x:                |
`SWAP_BUTTON_CANCEL`                   | `0x2005` | :x:                |
`POINTER_AXIS_ORIENTATION`             | `0x2006` | :x:                |
`VERTICAL_SCROLLING`                   | `0x2100` | :heavy_check_mark: | `get_vertical_scrolling_info`, read only
`SMART_SHIFT`                          | `0x2110` | :heavy_check_mark: | `_feature_smart_shift`
`HI_RES_SCROLLING`                     | `0x2120` | :heavy_check_mark: | `get_hi_res_scrolling_info`, `_feature_hi_res_scroll`
`HIRES_WHEEL`                          | `0x2121` | :heavy_check_mark: | `get_hires_wheel`, `_feature_hires_smooth_invert`, `_feature_hires_smooth_resolution`
`LOWRES_WHEEL`                         | `0x2130` | :heavy_check_mark: | `get_lowres_wheel_status`, `_feature_lowres_smooth_scroll`
`THUMB_WHEEL`                          | `0x2150` | :x:                |
`MOUSE_POINTER`                        | `0x2200` | :heavy_check_mark: | `get_mouse_pointer_info`, read only
`ADJUSTABLE_DPI`                       | `0x2201` | :heavy_check_mark: | `_feature_adjustable_dpi`
`POINTER_SPEED`                        | `0x2205` | :heavy_check_mark: | `get_pointer_speed_info`, `_feature_pointer_speed`
`ANGLE_SNAPPING`                       | `0x2230` | :x:                |
`SURFACE_TUNING`                       | `0x2240` | :x:                |
`HYBRID_TRACKING`                      | `0x2400` | :x:                |
`FN_INVERSION`                         | `0x40A0` | :heavy_check_mark: | `_feature_fn_swap`
`NEW_FN_INVERSION`                     | `0x40A2` | :heavy_check_mark: | `get_new_fn_inversion`, `_feature_new_fn_swap`
`K375S_FN_INVERSION`                   | `0x40A3` | :heavy_check_mark: | `_feature_k375s_fn_swap`
`ENCRYPTION`                           | `0x4100` | :x:                |
`LOCK_KEY_STATE`                       | `0x4220` | :x:                |
`SOLAR_DASHBOARD`                      | `0x4301` | :x:                |
`KEYBOARD_LAYOUT`                      | `0x4520` | :x:                | read only
`KEYBOARD_DISABLE_KEYS`                | `0x4521` | :heavy_check_mark: | `_feature_disable_keyboard_keys`
`KEYBOARD_DISABLE_BY_USAGE`            | `0x4522` | :x:                |
`DUALPLATFORM`                         | `0x4530` | :x:                | :wrench:
`MULTIPLATFORM`                        | `0x4531` | :x:                | :wrench:
`KEYBOARD_LAYOUT_2`                    | `0x4540` | :x:                | read only
`CROWN`                                | `0x4600` | :x:                |
`TOUCHPAD_FW_ITEMS`                    | `0x6010` | :x:                |
`TOUCHPAD_SW_ITEMS`                    | `0x6011` | :x:                |
`TOUCHPAD_WIN8_FW_ITEMS`               | `0x6012` | :x:                |
`TAP_ENABLE`                           | `0x6020` | :x:                |
`TAP_ENABLE_EXTENDED`                  | `0x6021` | :x:                |
`CURSOR_BALLISTIC`                     | `0x6030` | :x:                |
`TOUCHPAD_RESOLUTION`                  | `0x6040` | :x:                |
`TOUCHPAD_RAW_XY`                      | `0x6100` | :x:                |
`TOUCHMOUSE_RAW_POINTS`                | `0x6110` | :x:                |
`TOUCHMOUSE_6120`                      | `0x6120` | :x:                |
`GESTURE`                              | `0x6500` | :x:                |
`GESTURE_2`                            | `0x6501` | :x:                |
`GKEY`                                 | `0x8010` | :x:                |
`MKEYS`                                | `0x8020` | :x:                |
`MR`                                   | `0x8030` | :x:                |
`BRIGHTNESS_CONTROL`                   | `0x8040` | :x:                |
`REPORT_RATE`                          | `0x8060` | :x:                | in progress
`COLOR_LED_EFFECTS`                    | `0x8070` | :x:                |
`RGB_EFFECTS`                          | `0X8071` | :x:                |
`PER_KEY_LIGHTING`                     | `0x8080` | :x:                |
`PER_KEY_LIGHTING_V2`                  | `0x8081` | :x:                |
`MODE_STATUS`                          | `0x8090` | :x:                |
`ONBOARD_PROFILES`                     | `0x8100` | :x:                |
`MOUSE_BUTTON_SPY`                     | `0x8110` | :x:                |
`LATENCY_MONITORING`                   | `0x8111` | :x:                |
`GAMING_ATTACHMENTS`                   | `0x8120` | :x:                |
`FORCE_FEEDBACK`                       | `0x8123` | :x:                |
`SIDETONE`                             | `0x8300` | :x:                |
`EQUALIZER`                            | `0x8310` | :x:                |
`HEADSET_OUT`                          | `0x8320` | :x:                |

"read only" in the notes column means that the feature is a read-only feature and cannot be changed.

# Implementing a feature

Features are implemented as settable features in
lib/logitech_receiver/settings_templates.py
Some features also have direct implementation in
lib/logitech_receiver/hidpp20.py

In most cases it should suffice to only implement the settable feature
interface for each setting in the feature.  That will add one or more
widgets in the Solaar main window to show and change the setting,
will permit storing and restoring changed settings, and
will output the feature settings in `solaar show`.

Adding a setting implementation involves several steps, described here and
illustrated by the pointer speed setting implementation.

First add a name, a label, and a description for the setting in the common strings section.
The name is used in the persistent settings structure to store and restore changed settings and
should be a valid Python identifier.  (Some older settings have dashes.)
The label is displayed in the Solaar main window and the description is used as a tooltip there.
The label and description should be specified as translatable strings.

```
_POINTER_SPEED = ('pointer_speed', _("Sensitivity (Pointer Speed)"), _("How fast the pointer moves"))
```

Implement a register interface for the setting (if you are very brave and
some devices have a register interface for the setting).
Register interfaces cannot be auto-discovered and need to be stated in descriptors.py
for each device with the register interface.

Implement a feature interface for the setting.  There are several possible kinds of
feature interfaces, ranging from simple toggles, to ranges, to fixed lists, to
dynamic choices, to maps of dynamic choices, each created by a macro function.
Pointer speed is a setting
whose values are integers in a range so `feature_range` is used.
The arguments to this macro are
the name of the setting (use the name from the common strings tuple),
the HID++ 2.0 feature ID for the setting (from the FEATURE structure in hidpp20.py),
the minimum and maximum values for the setting,
the HID++ 2.0 function IDs to read and write the setting (left-shifted four bits),
the byte size of the setting value,
a label and description for the setting (from the common strings tuple),
and which kinds of devices can have this setting.
(This last is no longer used because keyboards with integrated pointers only
report that they are keyboards.)
The values to be used need to be determined from documentation of the
feature or from reverse-engineering behaviour of Logitech software under
Windows or MacOS.

```
def _feature_pointer_speed():
	"""Pointer Speed feature"""
	return feature_range(_POINTER_SPEED[0], _F.POINTER_SPEED, 0x002e, 0x01ff,
					read_function_id=0x0,
					write_function_id=0x10,
					bytes_count=2,
					label=_POINTER_SPEED[1], description=_POINTER_SPEED[2],
					device_kind=(_DK.mouse, _DK.trackball))
```

Settings that are toggles or choices work very similarly.
Settings where the choices are determined from the device
need an auxiliary function to receive and decipher the permissable choices.
See `_feature_adjustable_dpi_choices` for an example.

Add an element to _SETTINGS_TABLE with
the setting name (from the common strings),
the feature ID (if any),
the feature implementation (if any),
the register implementation (if any).
and
the identifier for the setting implementation if different from the setting name.
The identifier is used in descriptors.py to say that a device has the register or feature implementation.
The identifier can be the same as the setting name if there is only one implementation for the setting.
This table is used to generate the data structures for describing devices in descriptors.py
and is also used to auto-discover feature implementations.
```
_S( _POINTER_SPEED[0], _F.POINTER_SPEED, _feature_pointer_speed ),
```
