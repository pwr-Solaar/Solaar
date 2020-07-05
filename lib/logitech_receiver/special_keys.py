# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
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

# Reprogrammable keys information
# Mostly from Logitech documentation, but with some edits for better Lunix compatability

from __future__ import absolute_import, division, print_function, unicode_literals

from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts

# <controls.xml awk -F\" '/<Control /{sub(/^LD_FINFO_(CTRLID_)?/, "", $2);printf("\t%s=0x%04X,\n", $2, $4)}' | sort -t= -k2
CONTROL = _NamedInts(
    Volume_Up=0x0001,
    Volume_Down=0x0002,
    Mute=0x0003,
    Play__Pause=0x0004,
    Next=0x0005,
    Previous=0x0006,
    Stop=0x0007,
    Application_Switcher=0x0008,
    Burn=0x0009,
    Calculator=0x000A,
    Calendar=0x000B,
    Close=0x000C,
    Eject=0x000D,
    Mail=0x000E,
    Help_As_HID=0x000F,
    Help_As_F1=0x0010,
    Launch_Word_Proc=0x0011,
    Launch_Spreadsheet=0x0012,
    Launch_Presentation=0x0013,
    Undo_As_Ctrl_Z=0x0014,
    Undo_As_HID=0x0015,
    Redo_As_Ctrl_Y=0x0016,
    Redo_As_HID=0x0017,
    Print_As_Ctrl_P=0x0018,
    Print_As_HID=0x0019,
    Save_As_Ctrl_S=0x001A,
    Save_As_HID=0x001B,
    Preset_A=0x001C,
    Preset_B=0x001D,
    Preset_C=0x001E,
    Preset_D=0x001F,
    Favorites=0x0020,
    Gadgets=0x0021,
    My_Home=0x0022,
    Gadgets_As_Win_G=0x0023,
    Maximize_As_HID=0x0024,
    Maximize_As_Win_Shift_M=0x0025,
    Minimize_As_HID=0x0026,
    Minimize_As_Win_M=0x0027,
    Media_Player=0x0028,
    Media_Center_Logi=0x0029,
    Media_Center_Msft=0x002A,  # Should not be used as it is not reprogrammable under Windows
    Custom_Menu=0x002B,
    Messenger=0x002C,
    My_Documents=0x002D,
    My_Music=0x002E,
    Webcam=0x002F,
    My_Pictures=0x0030,
    My_Videos=0x0031,
    My_Computer_As_HID=0x0032,
    My_Computer_As_Win_E=0x0033,
    Launch_Picture_Viewer=0x0035,
    One_Touch_Search=0x0036,
    Preset_1=0x0037,
    Preset_2=0x0038,
    Preset_3=0x0039,
    Preset_4=0x003A,
    Record=0x003B,
    Internet_Refresh=0x003C,
    Search=0x003E,  # SEARCH
    Shuffle=0x003F,
    Sleep=0x0040,
    Internet_Stop=0x0041,
    Synchronize=0x0042,
    Zoom=0x0043,
    Zoom_In_As_HID=0x0044,
    Zoom_In_As_Ctrl_Wheel=0x0045,
    Zoom_In_As_Cltr_Plus=0x0046,
    Zoom_Out_As_HID=0x0047,
    Zoom_Out_As_Ctrl_Wheel=0x0048,
    Zoom_Out_As_Ctrl_Minus=0x0049,
    Zoom_Reset=0x004A,
    Zoom_Full_Screen=0x004B,
    Print_Screen=0x004C,
    Pause_Break=0x004D,
    Scroll_Lock=0x004E,
    Contextual_Menu=0x004F,
    Left_Button=0x0050,  # LEFT_CLICK
    Right_Button=0x0051,  # RIGHT_CLICK
    Middle_Button=0x0052,  # MIDDLE_BUTTON
    Back_Button=0x0053,  # from M510v2 was BACK_AS_BUTTON_4
    Back=0x0054,  # BACK_AS_HID
    Back_As_Alt_Win_Arrow=0x0055,
    Forward_Button=0x0056,  # from M510v2 was FORWARD_AS_BUTTON_5
    Forward_As_HID=0x0057,
    Forward_As_Alt_Win_Arrow=0x0058,
    Button_6=0x0059,
    Left_Scroll_As_Button_7=0x005A,
    Left_Tilt=0x005B,  # from M510v2 was LEFT_SCROLL_AS_AC_PAN
    Right_Scroll_As_Button_8=0x005C,
    Right_Tilt=0x005D,  # from M510v2 was RIGHT_SCROLL_AS_AC_PAN
    Button_9=0x005E,
    Button_10=0x005F,
    Button_11=0x0060,
    Button_12=0x0061,
    Button_13=0x0062,
    Button_14=0x0063,
    Button_15=0x0064,
    Button_16=0x0065,
    Button_17=0x0066,
    Button_18=0x0067,
    Button_19=0x0068,
    Button_20=0x0069,
    Button_21=0x006A,
    Button_22=0x006B,
    Button_23=0x006C,
    Button_24=0x006D,
    Show_Desktop=0x006E,  # Show_Desktop
    Lock_PC=0x006F,
    Fn_F1=0x0070,
    Fn_F2=0x0071,
    Fn_F3=0x0072,
    Fn_F4=0x0073,
    Fn_F5=0x0074,
    Fn_F6=0x0075,
    Fn_F7=0x0076,
    Fn_F8=0x0077,
    Fn_F9=0x0078,
    Fn_F10=0x0079,
    Fn_F11=0x007A,
    Fn_F12=0x007B,
    Fn_F13=0x007C,
    Fn_F14=0x007D,
    Fn_F15=0x007E,
    Fn_F16=0x007F,
    Fn_F17=0x0080,
    Fn_F18=0x0081,
    Fn_F19=0x0082,
    IOS_Home=0x0083,
    Android_Home=0x0084,
    Android_Menu=0x0085,
    Android_Search=0x0086,
    Android_Back=0x0087,
    Home_Combo=0x0088,
    Lock_Combo=0x0089,
    IOS_Virtual_Keyboard=0x008A,
    IOS_Language_Switch=0x008B,
    Mac_Expose=0x008C,
    Mac_Dashboard=0x008D,
    Win7_Snap_Left=0x008E,
    Win7_Snap_Right=0x008F,
    Minimize_Window=0x0090,  # WIN7_MINIMIZE_AS_WIN_ARROW
    Maximize_Window=0x0091,  # WIN7_MAXIMIZE_AS_WIN_ARROW
    Win7_Stretch_Up=0x0092,
    Win7_Monitor_Switch_As_Win_Shift_LeftArrow=0x0093,
    Win7_Monitor_Switch_As_Win_Shift_RightArrow=0x0094,
    Switch_Screen=0x0095,  # WIN7_SHOW_PRESENTATION_MODE
    Win7_Show_Mobility_Center=0x0096,
    Analog_HScroll=0x0097,
    Metro_Appswitch=0x009F,
    Metro_Appbar=0x00A0,
    Metro_Charms=0x00A1,
    Calc_Vkeyboard=0x00A2,
    Metro_Search=0x00A3,
    Combo_Sleep=0x00A4,
    Metro_Share=0x00A5,
    Metro_Settings=0x00A6,
    Metro_Devices=0x00A7,
    Metro_Start_Screen=0x00A9,
    Zoomin=0x00AA,
    Zoomout=0x00AB,
    Back_Hscroll=0x00AC,
    Show_Desktop_HPP=0x00AE,
    Fn_Left_Click=0x00B7,  # from K400 Plus
    # https://docs.google.com/document/u/0/d/1YvXICgSe8BcBAuMr4Xu_TutvAxaa-RnGfyPFWBWzhkc/export?format=docx
    # Extract to csv.  Eliminate extra linefeeds and spaces.
    # awk -F, '/0x/{gsub(" \\+ ","_",$2); gsub("/","__",$2); gsub(" -","_Down",$2);
    # gsub(" \\+","_Up",$2); gsub("[()\"-]","",$2); gsub(" ","_",$2); printf("\t%s=0x%04X,\n", $2, $1)}' < controls.cvs
    Second_Left_Click=0x00B8,  # Second_LClick / on K400 Plus
    Fn_Second_Left_Click=0x00B9,  # Fn_Second_LClick
    Multiplatform_App_Switch=0x00BA,
    Multiplatform_Home=0x00BB,
    Multiplatform_Menu=0x00BC,
    Multiplatform_Back=0x00BD,
    Multiplatform_Insert=0x00BE,
    Screen_Capture__Print_Screen=0x00BF,  # on Craft Keyboard
    Fn_Down=0x00C0,
    Fn_Up=0x00C1,
    Multiplatform_Lock=0x00C2,
    App_Switch_Gesture=0x00C3,  # Thumb_Button on MX Master
    Smart_Shift=0x00C4,  # Top_Button on MX Master
    Microphone=0x00C5,
    Wifi=0x00C6,
    Brightness_Down=0x00C7,
    Brightness_Up=0x00C8,
    Display_Out__Project_Screen_=0x00C9,
    View_Open_Apps=0x00CA,
    View_All_Apps=0x00CB,
    Switch_App=0x00CC,
    Fn_Inversion_Change=0x00CD,
    MultiPlatform_Back=0x00CE,
    MultiPlatform_Forward=0x00CF,
    MultiPlatform_Gesture_Button=0x00D0,
    Host_Switch_Channel_1=0x00D1,
    Host_Switch_Channel_2=0x00D2,
    Host_Switch_Channel_3=0x00D3,
    MultiPlatform_Search=0x00D4,
    MultiPlatform_Home__Mission_Control=0x00D5,
    MultiPlatform_Menu__Show__Hide_Virtual_Keyboard__Launchpad=0x00D6,
    Virtual_Gesture_Button=0x00D7,
    Cursor_Button_Long_Press=0x00D8,
    Next_Button_Shortpress=0x00D9,  # Next_Button
    Next_Button_Long_Press=0x00DA,
    Back_Button_Short_Press=0x00DB,  # Back
    Back_Button_Long_Press=0x00DC,
    Multi_Platform_Language_Switch=0x00DD,
    F_Lock=0x00DE,
    Switch_Highlight=0x00DF,
    Mission_Control__Task_View=0x00E0,  # Switch_Workspaces on Craft Keyboard
    Dashboard_Launchpad__Action_Center=0x00E1,  # Application_Launcher on Craft Keyboard
    Backlight_Down=0x00E2,
    Backlight_Up=0x00E3,
    Previous_Fn=0x00E4,  # Reprogrammable_Previous_Track / on Craft Keyboard
    Play__Pause_Fn=0x00E5,  # Reprogrammable_Play__Pause / on Craft Keyboard
    Next_Fn=0x00E6,  # Reprogrammable_Next_Track / on Craft Keyboard
    Mute_Fn=0x00E7,  # Reprogrammable_Mute / on Craft Keyboard
    Volume_Down_Fn=0x00E8,  # Reprogrammable_Volume_Down / on Craft Keyboard
    Volume_Up_Fn=0x00E9,  # Reprogrammable_Volume_Up / on Craft Keyboard
    App_Contextual_Menu__Right_Click=0x00EA,  # Context_Menu on Craft Keyboard
    Right_Arrow=0x00EB,
    Left_Arrow=0x00EC,
    DPI_Change=0x00ED,
    New_Tab=0x00EE,
    F2=0x00EF,
    F3=0x00F0,
    F4=0x00F1,
    F5=0x00F2,
    F6=0x00F3,
    F7=0x00F4,
    F8=0x00F5,
    F1=0x00F6,
    Next_Color_Effect=0x00F7,
    Increase_Color_Effect_Speed=0x00F8,
    Decrease_Color_Effect_Speed=0x00F9,
    Load_Lighting_Custom_Profile=0x00FA,
    Laser_Button_Short_Press=0x00FB,
    Laser_Button_Long_Press=0x00FC,
    DPI_Switch=0x00FD,
    Multiplatform_Home__Show_Desktop=0x00FE,
    Multiplatform_App_Switch__Show_Dashboard=0x00FF,
    Multiplatform_App_Switch_2=0x0100,  # Multiplatform_App_Switch
    Fn_Inversion__Hot_Key=0x0101,
    LeftAndRightClick=0x0102,
    LED_Toggle=0x013B,  #
)
CONTROL._fallback = lambda x: 'unknown:%04X' % x

# <tasks.xml awk -F\" '/<Task /{gsub(/ /, "_", $6); printf("\t%s=0x%04X,\n", $6, $4)}'
TASK = _NamedInts(
    Volume_Up=0x0001,
    Volume_Down=0x0002,
    Mute=0x0003,
    # Multimedia tasks:
    Play__Pause=0x0004,
    Next=0x0005,
    Previous=0x0006,
    Stop=0x0007,
    Application_Switcher=0x0008,
    BurnMediaPlayer=0x0009,
    Calculator=0x000A,
    Calendar=0x000B,
    Close_Application=0x000C,
    Eject=0x000D,
    Email=0x000E,
    Help=0x000F,
    OffDocument=0x0010,
    OffSpreadsheet=0x0011,
    OffPowerpnt=0x0012,
    Undo=0x0013,
    Redo=0x0014,
    Print=0x0015,
    Save=0x0016,
    SmartKeySet=0x0017,
    Favorites=0x0018,
    GadgetsSet=0x0019,
    HomePage=0x001A,
    WindowsRestore=0x001B,
    WindowsMinimize=0x001C,
    Music=0x001D,  # also known as MediaPlayer

    # Both 0x001E and 0x001F are known as MediaCenterSet
    Media_Center_Logitech=0x001E,
    Media_Center_Microsoft=0x001F,
    UserMenu=0x0020,
    Messenger=0x0021,
    PersonalFolders=0x0022,
    MyMusic=0x0023,
    Webcam=0x0024,
    PicturesFolder=0x0025,
    MyVideos=0x0026,
    My_Computer=0x0027,
    PictureAppSet=0x0028,
    Search=0x0029,  # also known as AdvSmartSearch
    RecordMediaPlayer=0x002A,
    BrowserRefresh=0x002B,
    RotateRight=0x002C,
    Search_Files=0x002D,  # SearchForFiles
    MM_SHUFFLE=0x002E,
    Sleep=0x002F,  # also known as StandBySet
    BrowserStop=0x0030,
    OneTouchSync=0x0031,
    ZoomSet=0x0032,
    ZoomBtnInSet2=0x0033,
    ZoomBtnInSet=0x0034,
    ZoomBtnOutSet2=0x0035,
    ZoomBtnOutSet=0x0036,
    ZoomBtnResetSet=0x0037,
    Left_Click=0x0038,  # LeftClick
    Right_Click=0x0039,  # RightClick
    Mouse_Middle_Button=0x003A,  # from M510v2 was MiddleMouseButton
    Back=0x003B,
    Mouse_Back_Button=0x003C,  # from M510v2 was BackEx
    BrowserForward=0x003D,
    Mouse_Forward_Button=0x003E,  # from M510v2 was BrowserForwardEx
    Mouse_Scroll_Left_Button_=0x003F,  # from M510v2 was HorzScrollLeftSet
    Mouse_Scroll_Right_Button=0x0040,  # from M510v2 was HorzScrollRightSet
    QuickSwitch=0x0041,
    BatteryStatus=0x0042,
    Show_Desktop=0x0043,  # ShowDesktop
    WindowsLock=0x0044,
    FileLauncher=0x0045,
    FolderLauncher=0x0046,
    GotoWebAddress=0x0047,
    GenericMouseButton=0x0048,
    KeystrokeAssignment=0x0049,
    LaunchProgram=0x004A,
    MinMaxWindow=0x004B,
    VOLUMEMUTE_NoOSD=0x004C,
    New=0x004D,
    Copy=0x004E,
    CruiseDown=0x004F,
    CruiseUp=0x0050,
    Cut=0x0051,
    Do_Nothing=0x0052,
    PageDown=0x0053,
    PageUp=0x0054,
    Paste=0x0055,
    SearchPicture=0x0056,
    Reply=0x0057,
    PhotoGallerySet=0x0058,
    MM_REWIND=0x0059,
    MM_FASTFORWARD=0x005A,
    Send=0x005B,
    ControlPanel=0x005C,
    UniversalScroll=0x005D,
    AutoScroll=0x005E,
    GenericButton=0x005F,
    MM_NEXT=0x0060,
    MM_PREVIOUS=0x0061,
    Do_Nothing_One=0x0062,  # also known as Do_Nothing
    SnapLeft=0x0063,
    SnapRight=0x0064,
    WinMinRestore=0x0065,
    WinMaxRestore=0x0066,
    WinStretch=0x0067,
    SwitchMonitorLeft=0x0068,
    SwitchMonitorRight=0x0069,
    ShowPresentation=0x006A,
    ShowMobilityCenter=0x006B,
    HorzScrollNoRepeatSet=0x006C,
    TouchBackForwardHorzScroll=0x0077,
    MetroAppSwitch=0x0078,
    MetroAppBar=0x0079,
    MetroCharms=0x007A,
    Calculator_VKEY=0x007B,  # also known as Calculator
    MetroSearch=0x007C,
    MetroStartScreen=0x0080,
    MetroShare=0x007D,
    MetroSettings=0x007E,
    MetroDevices=0x007F,
    MetroBackLeftHorz=0x0082,
    MetroForwRightHorz=0x0083,
    Win8_Back=0x0084,  # also known as MetroCharms
    Win8_Forward=0x0085,  # also known as AppSwitchBar
    Win8Charm_Appswitch_GifAnimation=0x0086,
    Win8BackHorzLeft=0x008B,  # also known as Back
    Win8ForwardHorzRight=0x008C,  # also known as BrowserForward
    MetroSearch2=0x0087,
    MetroShare2=0x0088,
    MetroSettings2=0x008A,
    MetroDevices2=0x0089,
    Win8MetroWin7Forward=0x008D,  # also known as MetroStartScreen
    Win8ShowDesktopWin7Back=0x008E,  # also known as ShowDesktop
    MetroApplicationSwitch=0x0090,  # also known as MetroStartScreen
    ShowUI=0x0092,
    # https://docs.google.com/document/d/1Dpx_nWRQAZox_zpZ8SNc9nOkSDE9svjkghOCbzopabc/edit
    # Extract to csv.  Eliminate extra linefeeds and spaces. Turn / into __ and space into _
    # awk -F, '/0x/{gsub(" \\+ ","_",$2);  gsub("_-","_Down",$2); gsub("_\\+","_Up",$2);
    # gsub("[()\"-]","",$2); gsub(" ","_",$2); printf("\t%s=0x%04X,\n", $2, $1)}' < tasks.csv > tasks.py
    Switch_Presentation__Switch_Screen=0x0093,  # on K400 Plus
    Minimize_Window=0x0094,
    Maximize_Window=0x0095,  # on K400 Plus
    MultiPlatform_App_Switch=0x0096,
    MultiPlatform_Home=0x0097,
    MultiPlatform_Menu=0x0098,
    MultiPlatform_Back=0x0099,
    Switch_Language=0x009A,  # Mac_switch_language
    Screen_Capture=0x009B,  # Mac_screen_Capture, on Craft Keyboard
    Gesture_Button=0x009C,
    Smart_Shift=0x009D,
    AppExpose=0x009E,
    Smart_Zoom=0x009F,
    Lookup=0x00A0,
    Microphone_on__off=0x00A1,
    Wifi_on__off=0x00A2,
    Brightness_Down=0x00A3,
    Brightness_Up=0x00A4,
    Display_Out=0x00A5,
    View_Open_Apps=0x00A6,
    View_All_Open_Apps=0x00A7,
    AppSwitch=0x00A8,
    Gesture_Button_Navigation=0x00A9,  # Mouse_Thumb_Button on MX Master
    Fn_inversion=0x00AA,
    Multiplatform_Back=0x00AB,
    Multiplatform_Forward=0x00AC,
    Multiplatform_Gesture_Button=0x00AD,
    HostSwitch_Channel_1=0x00AE,
    HostSwitch_Channel_2=0x00AF,
    HostSwitch_Channel_3=0x00B0,
    Multiplatform_Search=0x00B1,
    Multiplatform_Home__Mission_Control=0x00B2,
    Multiplatform_Menu__Launchpad=0x00B3,
    Virtual_Gesture_Button=0x00B4,
    Cursor=0x00B5,
    Keyboard_Right_Arrow=0x00B6,
    SW_Custom_Highlight=0x00B7,
    Keyboard_Left_Arrow=0x00B8,
    TBD=0x00B9,
    Multiplatform_Language_Switch=0x00BA,
    SW_Custom_Highlight_2=0x00BB,
    Fast_Forward=0x00BC,
    Fast_Backward=0x00BD,
    Switch_Highlighting=0x00BE,
    Mission_Control__Task_View=0x00BF,  # Switch_Workspace on Craft Keyboard
    Dashboard_Launchpad__Action_Center=0x00C0,  # Application_Launcher on Craft Keyboard
    Backlight_Down=0x00C1,  # Backlight_Down_FW_internal_function
    Backlight_Up=0x00C2,  # Backlight_Up_FW_internal_function
    Right_Click__App_Contextual_Menu=0x00C3,  # Context_Menu on Craft Keyboard
    DPI_Change=0x00C4,
    New_Tab=0x00C5,
    F2=0x00C6,
    F3=0x00C7,
    F4=0x00C8,
    F5=0x00C9,
    F6=0x00CA,
    F7=0x00CB,
    F8=0x00CC,
    F1=0x00CD,
    Laser_Button=0x00CE,
    Laser_Button_Long_Press=0x00CF,
    Start_Presentation=0x00D0,
    Blank_Screen=0x00D1,
    DPI_Switch=0x00D2,  # AdjustDPI on MX Vertical
    Home__Show_Desktop=0x00D3,
    App_Switch__Dashboard=0x00D4,
    App_Switch=0x00D5,
    Fn_Inversion=0x00D6,
    LeftAndRightClick=0x00D7,
    LedToggle=0x00DD,  #
)
TASK._fallback = lambda x: 'unknown:%04X' % x
# Capabilities and desired software handling for a control
# Ref: https://drive.google.com/file/d/10imcbmoxTJ1N510poGdsviEhoFfB_Ua4/view
# We treat bytes 4 and 8 of `getCidInfo` as a single bitfield
KEY_FLAG = _NamedInts(
    analytics_key_events=0x400,
    force_raw_XY=0x200,
    raw_XY=0x100,
    virtual=0x80,
    persistently_divertable=0x40,
    divertable=0x20,
    reprogrammable=0x10,
    FN_sensitive=0x08,
    nonstandard=0x04,
    is_FN=0x02,
    mse=0x01
)
# Flags describing the reporting method of a control
# We treat bytes 2 and 5 of `get/setCidReporting` as a single bitfield
MAPPING_FLAG = _NamedInts(
    analytics_key_events_reporting=0x100,
    force_raw_XY_diverted=0x40,
    raw_XY_diverted=0x10,
    persistently_diverted=0x04,
    diverted=0x01
)
CID_GROUP_BIT = _NamedInts(g8=0x80, g7=0x40, g6=0x20, g5=0x10, g4=0x08, g3=0x04, g2=0x02, g1=0x01)
CID_GROUP = _NamedInts(g8=8, g7=7, g6=6, g5=5, g4=4, g3=3, g2=2, g1=1)
DISABLE = _NamedInts(
    Caps_Lock=0x01,
    Num_Lock=0x02,
    Scroll_Lock=0x04,
    Insert=0x08,
    Win=0x10,  # aka Super
)
DISABLE._fallback = lambda x: 'unknown:%02X' % x

##
## Information for x1c00 Persistent from https://drive.google.com/drive/folders/0BxbRzx7vEV7eWmgwazJ3NUFfQ28
##

KEYMOD = _NamedInts(CTRL=0x01, SHIFT=0x02, ALT=0x04, META=0x08, RCTRL=0x10, RSHIFT=0x20, RALT=0x40, RMETA=0x80)

ACTIONID = _NamedInts(
    Empty=0x00,
    Key=0x01,
    Mouse=0x02,
    Xdisp=0x03,
    Ydisp=0x04,
    Vscroll=0x05,
    Hscroll=0x06,
    Control=0x07,
    Internal=0x08,
    Power=0x09
)

MOUSE_BUTTONS = _NamedInts(
    Left=0x01,
    Right=0x02,
    Middle=0x04,
    Back=0x08,
    Forward=0x10,
)
MOUSE_BUTTONS._fallback = lambda x: 'unknown:%02X' % x

# HID USB Keycodes from https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
USB_HID_KEYCODES = _NamedInts(
    NONE=0x00,
    ERR_OVF=0x01,
    A=0x04,
    B=0x05,
    C=0x06,
    D=0x07,
    E=0x08,
    F=0x09,
    G=0x0a,
    H=0x0b,
    I=0x0c,
    J=0x0d,
    K=0x0e,
    L=0x0f,
    M=0x10,
    N=0x11,
    O=0x12,
    P=0x13,
    Q=0x14,
    R=0x15,
    S=0x16,
    T=0x17,
    U=0x18,
    V=0x19,
    W=0x1a,
    X=0x1b,
    Y=0x1c,
    Z=0x1d,
    ENTER=0x28,
    ESC=0x29,
    BACKSPACE=0x2a,
    TAB=0x2b,
    SPACE=0x2c,
    MINUS=0x2d,
    EQUAL=0x2e,
    LEFTBRACE=0x2f,
    RIGHTBRACE=0x30,
    BACKSLASH=0x31,
    HASHTILDE=0x32,
    SEMICOLON=0x33,
    APOSTROPHE=0x34,
    GRAVE=0x35,
    COMMA=0x36,
    DOT=0x37,
    SLASH=0x38,
    CAPSLOCK=0x39,
    F1=0x3a,
    F2=0x3b,
    F3=0x3c,
    F4=0x3d,
    F5=0x3e,
    F6=0x3f,
    F7=0x40,
    F8=0x41,
    F9=0x42,
    F10=0x43,
    F11=0x44,
    F12=0x45,
    SYSRQ=0x46,
    SCROLLLOCK=0x47,
    PAUSE=0x48,
    INSERT=0x49,
    HOME=0x4a,
    PAGEUP=0x4b,
    DELETE=0x4c,
    END=0x4d,
    PAGEDOWN=0x4e,
    RIGHT=0x4f,
    LEFT=0x50,
    DOWN=0x51,
    UP=0x52,
    NUMLOCK=0x53,
    KPSLASH=0x54,
    KPASTERISK=0x55,
    KPMINUS=0x56,
    KPPLUS=0x57,
    KPENTER=0x58,
    KP1=0x59,
    KP2=0x5a,
    KP3=0x5b,
    KP4=0x5c,
    KP5=0x5d,
    KP6=0x5e,
    KP7=0x5f,
    KP8=0x60,
    KP9=0x61,
    KP0=0x62,
    KPDOT=0x63,
    COMPOSE=0x65,
    POWER=0x66,
    KPEQUAL=0x67,
    F13=0x68,
    F14=0x69,
    F15=0x6a,
    F16=0x6b,
    F17=0x6c,
    F18=0x6d,
    F19=0x6e,
    F20=0x6f,
    F21=0x70,
    F22=0x71,
    F23=0x72,
    F24=0x73,
    OPEN=0x74,
    HELP=0x75,
    PROPS=0x76,
    FRONT=0x77,
    STOP=0x78,
    AGAIN=0x79,
    UNDO=0x7a,
    CUT=0x7b,
    COPY=0x7c,
    PASTE=0x7d,
    FIND=0x7e,
    MUTE=0x7f,
    VOLUMEUP=0x80,
    VOLUMEDOWN=0x81,
    KPCOMMA=0x85,
    RO=0x87,
    KATAKANAHIRAGANA=0x88,
    YEN=0x89,
    HENKAN=0x8a,
    MUHENKAN=0x8b,
    KPJPCOMMA=0x8c,
    HANGEUL=0x90,
    HANJA=0x91,
    KATAKANA=0x92,
    HIRAGANA=0x93,
    ZENKAKUHANKAKU=0x94,
    KPLEFTPAREN=0xb6,
    KPRIGHTPAREN=0xb7,
    LEFTCTRL=0xe0,
    LEFTSHIFT=0xe1,
    LEFTALT=0xe2,
    LEFTWINDOWS=0xe3,
    RIGHTCTRL=0xe4,
    RIGHTSHIFT=0xe5,
    RIGHTALT=0xe6,
    RIGHTMETA=0xe7,
    MEDIA_PLAYPAUSE=0xe8,
    MEDIA_STOPCD=0xe9,
    MEDIA_PREVIOUSSONG=0xea,
    MEDIA_NEXTSONG=0xeb,
    MEDIA_EJECTCD=0xec,
    MEDIA_VOLUMEUP=0xed,
    MEDIA_VOLUMEDOWN=0xee,
    MEDIA_MUTE=0xef,
    MEDIA_WWW=0xf0,
    MEDIA_BACK=0xf1,
    MEDIA_FORWARD=0xf2,
    MEDIA_STOP=0xf3,
    MEDIA_FIND=0xf4,
    MEDIA_SCROLLUP=0xf5,
    MEDIA_SCROLLDOWN=0xf6,
    MEDIA_EDIT=0xf7,
    MEDIA_SLEEP=0xf8,
    MEDIA_COFFEE=0xf9,
    MEDIA_REFRESH=0xfa,
    MEDIA_CALC=0xfb,
)
USB_HID_KEYCODES[0x1e] = '1'
USB_HID_KEYCODES[0x1f] = '2'
USB_HID_KEYCODES[0x20] = '3'
USB_HID_KEYCODES[0x21] = '4'
USB_HID_KEYCODES[0x22] = '5'
USB_HID_KEYCODES[0x23] = '6'
USB_HID_KEYCODES[0x24] = '7'
USB_HID_KEYCODES[0x25] = '8'
USB_HID_KEYCODES[0x26] = '9'
USB_HID_KEYCODES[0x27] = '0'
USB_HID_KEYCODES[0x64] = '102ND'

# Construct keys plus modifiers
modifiers = {
    0x0: '',
    0x1: 'Cntrl+',
    0x2: 'Shift+',
    0x4: 'Alt+',
    0x8: 'Meta+',
    0x3: 'Cntrl+Shift+',
    0x5: 'Cntrl+Alt+',
    0x9: 'Cntrl+Meta+',
    0x6: 'Shift+Alt+',
    0xA: 'Shift+Meta+',
    0xC: 'Alt+Meta+'
}
KEYS = []
for val, name in modifiers.items():
    for key in USB_HID_KEYCODES:
        KEYS.append(_NamedInt((int(key) << 8) + val, name + str(key)))
