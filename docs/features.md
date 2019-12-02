---
title: List of HID++ 2.0 features
layout: page
---

# Features status
See functions in hidpp20.py and settings_templates.py

| Feature              | ID     | Status    | Notes                                   |
|----------------------|--------|-----------|-----------------------------------------|
| ROOT                 | 0x0000 | Supported | System                                  |
| FEATURE_SET          | 0x0001 | Supported | System                                  |
| FEATURE_INFO         | 0x0002 | Supported | System                                  |
| DEVICE_FW_VERSION    | 0x0003 | Supported | get_firmware()                          |
| DEVICE_UNIT_ID       | 0x0004 |           |                                         |
| DEVICE_NAME          | 0x0005 | Supported | get_kind(), get_name()                  |
| DEVICE_GROUPS        | 0x0006 |           |                                         |
| DEVICE_FRIENDLY_NAME | 0x0007 |           |                                         |
| KEEP_ALIVE           | 0x0008 |           |                                         |
| RESET                | 0x0020 |           | aka "Config Change"                     |
| CRYPTO_ID            | 0x0021 |           |                                         |
| TARGET_SOFTWARE      | 0x0030 |           |                                         |
| WIRELESS_SIGNAL_STRENGTH | 0x0080 |         |                                         |
| DFUCONTROL_LEGACY    | 0x00C0 |           |                                         |
| DFUCONTROL_UNSIGNED  | 0x00C1 |           |                                         |
| DFUCONTROL_SIGNED    | 0x00C2 |           |                                         |
| DFU                  | 0x00D0 |           |                                         |
| BATTERY_STATUS       | 0x1000 | Supported |  get_battery()                          |
| BATTERY_VOLTAGE      | 0x1001 |           | Used in G series mouse?                 |
| CHARGING_CONTROL     | 0x1010 |           |                                         |
| LED_CONTROL          | 0x1300 |           |                                         |
| GENERIC_TEST         | 0x1800 |           |                                         |
| DEVICE_RESET         | 0x1802 |           |                                         |
| OOBSTATE             | 0x1805 |           |                                         |
| CONFIG_DEVICE_PROPS  | 0x1806 |           |                                         |
| CHANGE_HOST          | 0x1814 |           |                                         |
| HOSTS_INFO           | 0x1815 |           |                                         |
| BACKLIGHT            | 0x1981 |           |                                         |
| BACKLIGHT2           | 0x1982 |           |                                         |
| BACKLIGHT3           | 0x1983 |           |                                         |
| PRESENTER_CONTROL    | 0x1A00 |           |                                         |
| SENSOR_3D            | 0x1A01 |           |                                         |
| REPROG_CONTROLS      | 0x1B00 | Supported | Partially, only listing. get_keys()     |
| REPROG_CONTROLS_V2   | 0x1B01 |           |                                         |
| REPROG_CONTROLS_V2_2 | 0x1B02 |           |                                         | 
| REPROG_CONTROLS_V3   | 0x1B03 |           |                                         |
| REPROG_CONTROLS_V4   | 0x1B04 | Supported | Partially, only listing. get_keys()     |
| REPORT_HID_USAGE     | 0x1BC0 |           |                                         |
| PERSISTENT_REMAPPABLE_ACTION | 0x1C00 |         |                                         |
| WIRELESS_DEVICE_STATUS | 0x1D4B |         |                                         |
| REMAINING_PAIRING    | 0x1DF0 |           |                                         |
| ENABLE_HIDDEN_FEATURES | 0x1E00 |         |                                         |
| FIRMWARE_PROPERTIES  | 0x1F1F |           |                                         |
| ADC_MEASUREMENT      | 0x1F20 |           |                                         |
| LEFT_RIGHT_SWAP      | 0x2001 |           |                                         |
| SWAP_BUTTON_CANCEL   | 0x2005 |           |                                         |
| POINTER_AXIS_ORIENTATION | 0x2006 |         |                                         |
| VERTICAL_SCROLLING   | 0x2100 | Supported | get_vertical_scrolling_info()           |
| SMART_SHIFT          | 0x2110 | Supported | _feature_smart_shift()                  |
| HI_RES_SCROLLING     | 0x2120 | Supported | get_hi_res_scrolling_info(), _feature_hi_res_scroll() |
| HIRES_WHEEL          | 0x2121 | Supported | get_hires_wheel(), _feature_hires_smooth_invert(), _feature_hires_smooth_resolution() |
| LOWRES_WHEEL         | 0x2130 | Supported | get_lowres_wheel_status(), _feature_lowres_smooth_scroll() |
| THUMB_WHEEL          | 0x2150 |           |                                         |
| MOUSE_POINTER        | 0x2200 | Supported | get_mouse_pointer_info()                |
| ADJUSTABLE_DPI       | 0x2201 | Supported | _feature_adjustable_dpi()               |
| POINTER_SPEED        | 0x2205 | Supported | get_pointer_speed_info(), _feature_pointer_speed() |
| ANGLE_SNAPPING       | 0x2230 |           |                                         |
| SURFACE_TUNING       | 0x2240 |           |                                         |
| HYBRID_TRACKING      | 0x2400 |           |                                         |
| FN_INVERSION         | 0x40A0 | Supported | _feature_fn_swap()                      |
| NEW_FN_INVERSION     | 0x40A2 | Supported | _feature_new_fn_swap()                  |
| K375S_FN_INVERSION   | 0x40A3 | Supported | _feature_k375s_fn_swap()                |
| ENCRYPTION | 0x4100|         |                                         |
| LOCK_KEY_STATE | 0x4220|         |                                         |
| SOLAR_DASHBOARD | 0x4301|         |                                         |
| KEYBOARD_LAYOUT | 0x4520|         |                                         |
| KEYBOARD_DISABLE | 0x4521|         |                                         |
| KEYBOARD_DISABLE_BY_USAGE | 0x4522|         |                                         |
| DUALPLATFORM | 0x4530|         |                                         |
| MULTIPLATFORM | 0x4531|         |                                         |
| KEYBOARD_LAYOUT_2 | 0x4540|         |                                         |
| CROWN | 0x4600|         |                                         |
| TOUCHPAD_FW_ITEMS | 0x6010|         |                                         |
| TOUCHPAD_SW_ITEMS | 0x6011|         |                                         |
| TOUCHPAD_WIN8_FW_ITEMS | 0x6012|         |                                         |
| TAP_ENABLE | 0x6020|         |                                         |
| TAP_ENABLE_EXTENDED | 0x6021|         |                                         |
| CURSOR_BALLISTIC | 0x6030|         |                                         |
| TOUCHPAD_RESOLUTION | 0x6040|         |                                         |
| TOUCHPAD_RAW_XY | 0x6100|         |                                         |
| TOUCHMOUSE_RAW_POINTS | 0x6110|         |                                         |
| TOUCHMOUSE_6120 | 0x6120|         |                                         |
| GESTURE | 0x6500|         |                                         |
| GESTURE_2 | 0x6501|         |                                         |
| GKEY | 0x8010|         |                                         |
| MKEYS | 0x8020|         |                                         |
| MR | 0x8030|         |                                         |
| BRIGHTNESS_CONTROL | 0x8040|         |                                         |
| REPORT_RATE | 0x8060|         |                                         |
| COLOR_LED_EFFECTS | 0x8070|         |                                         |
| RGB_EFFECTS | 0X8071|         |                                         |
| PER_KEY_LIGHTING | 0x8080|         |                                         |
| PER_KEY_LIGHTING_V2 | 0x8081|         |                                         |
| MODE_STATUS | 0x8090|         |                                         |
| ONBOARD_PROFILES | 0x8100|         |                                         |
| MOUSE_BUTTON_SPY | 0x8110|         |                                         |
| LATENCY_MONITORING | 0x8111|         |                                         |
| GAMING_ATTACHMENTS | 0x8120|         |                                         |
| FORCE_FEEDBACK | 0x8123|         |                                         |
| SIDETONE | 0x8300|         |                                         |
| EQUALIZER | 0x8310|         |                                         |
| HEADSET_OUT | 0x8320|         |                                         |

