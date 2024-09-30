## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from .common import NamedInts

# <FeaturesSupported.xml sed '/LD_FID_/{s/.*LD_FID_/\t/;s/"[ \t]*Id="/=/;s/" \/>/,/p}' | sort -t= -k2
# additional features names taken from https://github.com/cvuchener/hidpp and
# https://github.com/Logitech/cpg-docs/tree/master/hidpp20
"""Possible features available on a Logitech device.

A particular device might not support all these features, and may support other
unknown features as well.
"""
FEATURE = NamedInts(
    ROOT=0x0000,
    FEATURE_SET=0x0001,
    FEATURE_INFO=0x0002,
    # Common
    DEVICE_FW_VERSION=0x0003,
    DEVICE_UNIT_ID=0x0004,
    DEVICE_NAME=0x0005,
    DEVICE_GROUPS=0x0006,
    DEVICE_FRIENDLY_NAME=0x0007,
    KEEP_ALIVE=0x0008,
    CONFIG_CHANGE=0x0020,
    CRYPTO_ID=0x0021,
    TARGET_SOFTWARE=0x0030,
    WIRELESS_SIGNAL_STRENGTH=0x0080,
    DFUCONTROL_LEGACY=0x00C0,
    DFUCONTROL_UNSIGNED=0x00C1,
    DFUCONTROL_SIGNED=0x00C2,
    DFUCONTROL=0x00C3,
    DFU=0x00D0,
    BATTERY_STATUS=0x1000,
    BATTERY_VOLTAGE=0x1001,
    UNIFIED_BATTERY=0x1004,
    CHARGING_CONTROL=0x1010,
    LED_CONTROL=0x1300,
    FORCE_PAIRING=0x1500,
    GENERIC_TEST=0x1800,
    DEVICE_RESET=0x1802,
    OOBSTATE=0x1805,
    CONFIG_DEVICE_PROPS=0x1806,
    CHANGE_HOST=0x1814,
    HOSTS_INFO=0x1815,
    BACKLIGHT=0x1981,
    BACKLIGHT2=0x1982,
    BACKLIGHT3=0x1983,
    ILLUMINATION=0x1990,
    PRESENTER_CONTROL=0x1A00,
    SENSOR_3D=0x1A01,
    REPROG_CONTROLS=0x1B00,
    REPROG_CONTROLS_V2=0x1B01,
    REPROG_CONTROLS_V2_2=0x1B02,  # LogiOptions 2.10.73 features.xml
    REPROG_CONTROLS_V3=0x1B03,
    REPROG_CONTROLS_V4=0x1B04,
    REPORT_HID_USAGE=0x1BC0,
    PERSISTENT_REMAPPABLE_ACTION=0x1C00,
    WIRELESS_DEVICE_STATUS=0x1D4B,
    REMAINING_PAIRING=0x1DF0,
    FIRMWARE_PROPERTIES=0x1F1F,
    ADC_MEASUREMENT=0x1F20,
    # Mouse
    LEFT_RIGHT_SWAP=0x2001,
    SWAP_BUTTON_CANCEL=0x2005,
    POINTER_AXIS_ORIENTATION=0x2006,
    VERTICAL_SCROLLING=0x2100,
    SMART_SHIFT=0x2110,
    SMART_SHIFT_ENHANCED=0x2111,
    HI_RES_SCROLLING=0x2120,
    HIRES_WHEEL=0x2121,
    LOWRES_WHEEL=0x2130,
    THUMB_WHEEL=0x2150,
    MOUSE_POINTER=0x2200,
    ADJUSTABLE_DPI=0x2201,
    EXTENDED_ADJUSTABLE_DPI=0x2202,
    POINTER_SPEED=0x2205,
    ANGLE_SNAPPING=0x2230,
    SURFACE_TUNING=0x2240,
    XY_STATS=0x2250,
    WHEEL_STATS=0x2251,
    HYBRID_TRACKING=0x2400,
    # Keyboard
    FN_INVERSION=0x40A0,
    NEW_FN_INVERSION=0x40A2,
    K375S_FN_INVERSION=0x40A3,
    ENCRYPTION=0x4100,
    LOCK_KEY_STATE=0x4220,
    SOLAR_DASHBOARD=0x4301,
    KEYBOARD_LAYOUT=0x4520,
    KEYBOARD_DISABLE_KEYS=0x4521,
    KEYBOARD_DISABLE_BY_USAGE=0x4522,
    DUALPLATFORM=0x4530,
    MULTIPLATFORM=0x4531,
    KEYBOARD_LAYOUT_2=0x4540,
    CROWN=0x4600,
    # Touchpad
    TOUCHPAD_FW_ITEMS=0x6010,
    TOUCHPAD_SW_ITEMS=0x6011,
    TOUCHPAD_WIN8_FW_ITEMS=0x6012,
    TAP_ENABLE=0x6020,
    TAP_ENABLE_EXTENDED=0x6021,
    CURSOR_BALLISTIC=0x6030,
    TOUCHPAD_RESOLUTION=0x6040,
    TOUCHPAD_RAW_XY=0x6100,
    TOUCHMOUSE_RAW_POINTS=0x6110,
    TOUCHMOUSE_6120=0x6120,
    GESTURE=0x6500,
    GESTURE_2=0x6501,
    # Gaming Devices
    GKEY=0x8010,
    MKEYS=0x8020,
    MR=0x8030,
    BRIGHTNESS_CONTROL=0x8040,
    REPORT_RATE=0x8060,
    EXTENDED_ADJUSTABLE_REPORT_RATE=0x8061,
    COLOR_LED_EFFECTS=0x8070,
    RGB_EFFECTS=0x8071,
    PER_KEY_LIGHTING=0x8080,
    PER_KEY_LIGHTING_V2=0x8081,
    MODE_STATUS=0x8090,
    ONBOARD_PROFILES=0x8100,
    MOUSE_BUTTON_SPY=0x8110,
    LATENCY_MONITORING=0x8111,
    GAMING_ATTACHMENTS=0x8120,
    FORCE_FEEDBACK=0x8123,
    # Headsets
    SIDETONE=0x8300,
    EQUALIZER=0x8310,
    HEADSET_OUT=0x8320,
    # Fake features for Solaar internal use
    MOUSE_GESTURE=0xFE00,
)
FEATURE._fallback = lambda x: f"unknown:{x:04X}"

FEATURE_FLAG = NamedInts(internal=0x20, hidden=0x40, obsolete=0x80)

DEVICE_KIND = NamedInts(
    keyboard=0x00,
    remote_control=0x01,
    numpad=0x02,
    mouse=0x03,
    touchpad=0x04,
    trackball=0x05,
    presenter=0x06,
    receiver=0x07,
)

FIRMWARE_KIND = NamedInts(Firmware=0x00, Bootloader=0x01, Hardware=0x02, Other=0x03)

ONBOARD_MODES = NamedInts(MODE_NO_CHANGE=0x00, MODE_ONBOARD=0x01, MODE_HOST=0x02)

CHARGE_STATUS = NamedInts(charging=0x00, full=0x01, not_charging=0x02, error=0x07)

CHARGE_LEVEL = NamedInts(average=50, full=90, critical=5)

CHARGE_TYPE = NamedInts(standard=0x00, fast=0x01, slow=0x02)

ERROR = NamedInts(
    unknown=0x01,
    invalid_argument=0x02,
    out_of_range=0x03,
    hardware_error=0x04,
    logitech_internal=0x05,
    invalid_feature_index=0x06,
    invalid_function=0x07,
    busy=0x08,
    unsupported=0x09,
)

# Gesture Ids for feature GESTURE_2
GESTURE = NamedInts(
    Tap1Finger=1,  # task Left_Click
    Tap2Finger=2,  # task Right_Click
    Tap3Finger=3,
    Click1Finger=4,  # task Left_Click
    Click2Finger=5,  # task Right_Click
    Click3Finger=6,
    DoubleTap1Finger=10,
    DoubleTap2Finger=11,
    DoubleTap3Finger=12,
    Track1Finger=20,  # action MovePointer
    TrackingAcceleration=21,
    TapDrag1Finger=30,  # action Drag
    TapDrag2Finger=31,  # action SecondaryDrag
    Drag3Finger=32,
    TapGestures=33,  # group all tap gestures under a single UI setting
    FnClickGestureSuppression=34,  # suppresses Tap and Edge gestures, toggled by Fn+Click
    Scroll1Finger=40,  # action ScrollOrPageXY / ScrollHorizontal
    Scroll2Finger=41,  # action ScrollOrPageXY / ScrollHorizontal
    Scroll2FingerHoriz=42,  # action ScrollHorizontal
    Scroll2FingerVert=43,  # action WheelScrolling
    Scroll2FingerStateless=44,
    NaturalScrolling=45,  # affects native HID wheel reporting by gestures, not when diverted
    Thumbwheel=46,  # action WheelScrolling
    VScrollInertia=48,
    VScrollBallistics=49,
    Swipe2FingerHoriz=50,  # action PageScreen
    Swipe3FingerHoriz=51,  # action PageScreen
    Swipe4FingerHoriz=52,  # action PageScreen
    Swipe3FingerVert=53,
    Swipe4FingerVert=54,
    LeftEdgeSwipe1Finger=60,
    RightEdgeSwipe1Finger=61,
    BottomEdgeSwipe1Finger=62,
    TopEdgeSwipe1Finger=63,
    LeftEdgeSwipe1Finger2=64,  # task HorzScrollNoRepeatSet
    RightEdgeSwipe1Finger2=65,  # task 122 ??
    BottomEdgeSwipe1Finger2=66,
    TopEdgeSwipe1Finger2=67,  # task 121 ??
    LeftEdgeSwipe2Finger=70,
    RightEdgeSwipe2Finger=71,
    BottomEdgeSwipe2Finger=72,
    TopEdgeSwipe2Finger=73,
    Zoom2Finger=80,  # action Zoom
    Zoom2FingerPinch=81,  # ZoomBtnInSet
    Zoom2FingerSpread=82,  # ZoomBtnOutSet
    Zoom3Finger=83,
    Zoom2FingerStateless=84,  # action Zoom
    TwoFingersPresent=85,
    Rotate2Finger=87,
    Finger1=90,
    Finger2=91,
    Finger3=92,
    Finger4=93,
    Finger5=94,
    Finger6=95,
    Finger7=96,
    Finger8=97,
    Finger9=98,
    Finger10=99,
    DeviceSpecificRawData=100,
)
GESTURE._fallback = lambda x: f"unknown:{x:04X}"

# Param Ids for feature GESTURE_2
PARAM = NamedInts(
    ExtraCapabilities=1,  # not suitable for use
    PixelZone=2,  # 4 2-byte integers, left, bottom, width, height; pixels
    RatioZone=3,  # 4 bytes, left, bottom, width, height; unit 1/240 pad size
    ScaleFactor=4,  # 2-byte integer, with 256 as normal scale
)
PARAM._fallback = lambda x: f"unknown:{x:04X}"
