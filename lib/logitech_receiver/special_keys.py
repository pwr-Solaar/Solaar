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
	BURN=0x0009,
	Calculator=0x000A,
	CALENDAR=0x000B,
	CLOSE=0x000C,
	EJECT=0x000D,
	Mail=0x000E,
	HELP_AS_HID=0x000F,
	HELP_AS_F1=0x0010,
	LAUNCH_WORD_PROC=0x0011,
	LAUNCH_SPREADSHEET=0x0012,
	LAUNCH_PRESENTATION=0x0013,
	UNDO_AS_CTRL_Z=0x0014,
	UNDO_AS_HID=0x0015,
	REDO_AS_CTRL_Y=0x0016,
	REDO_AS_HID=0x0017,
	PRINT_AS_CTRL_P=0x0018,
	PRINT_AS_HID=0x0019,
	SAVE_AS_CTRL_S=0x001A,
	SAVE_AS_HID=0x001B,
	PRESET_A=0x001C,
	PRESET_B=0x001D,
	PRESET_C=0x001E,
	PRESET_D=0x001F,
	FAVORITES=0x0020,
	GADGETS=0x0021,
	MY_HOME=0x0022,
	GADGETS_AS_WIN_G=0x0023,
	MAXIMIZE_AS_HID=0x0024,
	MAXIMIZE_AS_WIN_SHIFT_M=0x0025,
	MINIMIZE_AS_HID=0x0026,
	MINIMIZE_AS_WIN_M=0x0027,
	MEDIA_PLAYER=0x0028,
	MEDIA_CENTER_LOGI=0x0029,
	MEDIA_CENTER_MSFT=0x002A, # Should not be used as it is not reprogrammable under Windows
	CUSTOM_MENU=0x002B,
	MESSENGER=0x002C,
	MY_DOCUMENTS=0x002D,
	MY_MUSIC=0x002E,
	WEBCAM=0x002F,
	MY_PICTURES=0x0030,
	MY_VIDEOS=0x0031,
	MY_COMPUTER_AS_HID=0x0032,
	MY_COMPUTER_AS_WIN_E=0x0033,
	LAUNC_PICTURE_VIEWER=0x0035,
	ONE_TOUCH_SEARCH=0x0036,
	PRESET_1=0x0037,
	PRESET_2=0x0038,
	PRESET_3=0x0039,
	PRESET_4=0x003A,
	RECORD=0x003B,
	INTERNET_REFRESH=0x003C,
	ROTATE_RIGHT=0x003D,
	Search=0x003E,		# SEARCH
	SHUFFLE=0x003F,
	SLEEP=0x0040,
	INTERNET_STOP=0x0041,
	SYNCHRONIZE=0x0042,
	ZOOM=0x0043,
	ZOOM_IN_AS_HID=0x0044,
	ZOOM_IN_AS_CTRL_WHEEL=0x0045,
	ZOOM_IN_AS_CLTR_PLUS=0x0046,
	ZOOM_OUT_AS_HID=0x0047,
	ZOOM_OUT_AS_CTRL_WHEEL=0x0048,
	ZOOM_OUT_AS_CLTR_MINUS=0x0049,
	ZOOM_RESET=0x004A,
	ZOOM_FULL_SCREEN=0x004B,
	PRINT_SCREEN=0x004C,
	PAUSE_BREAK=0x004D,
	SCROLL_LOCK=0x004E,
	CONTEXTUAL_MENU=0x004F,
	Left_Button=0x0050,		# LEFT_CLICK
	Right_Button=0x0051,		# RIGHT_CLICK
	Middle_Button=0x0052,		# MIDDLE_BUTTON
	Back_Button=0x0053,		# from M510v2 was BACK_AS_BUTTON_4
    	Back=0x0054,			# BACK_AS_HID
	BACK_AS_ALT_WIN_ARROW=0x0055,
	Forward_Button=0x0056,		# from M510v2 was FORWARD_AS_BUTTON_5
	FORWARD_AS_HID=0x0057,
	FORWARD_AS_ALT_WIN_ARROW=0x0058,
	BUTTON_6=0x0059,
	LEFT_SCROLL_AS_BUTTON_7=0x005A,
	Left_Tilt=0x005B,		# from M510v2 was LEFT_SCROLL_AS_AC_PAN
	RIGHT_SCROLL_AS_BUTTON_8=0x005C,
	Right_Tilt=0x005D,		# from M510v2 was RIGHT_SCROLL_AS_AC_PAN
	BUTTON_9=0x005E,
	BUTTON_10=0x005F,
	BUTTON_11=0x0060,
	BUTTON_12=0x0061,
	BUTTON_13=0x0062,
	BUTTON_14=0x0063,
	BUTTON_15=0x0064,
	BUTTON_16=0x0065,
	BUTTON_17=0x0066,
	BUTTON_18=0x0067,
	BUTTON_19=0x0068,
	BUTTON_20=0x0069,
	BUTTON_21=0x006A,
	BUTTON_22=0x006B,
	BUTTON_23=0x006C,
	BUTTON_24=0x006D,
	Show_Desktop=0x006E,	# Show_Desktop
	Lock_PC=0x006F,
	FN_F1=0x0070,
	FN_F2=0x0071,
	FN_F3=0x0072,
	FN_F4=0x0073,
	FN_F5=0x0074,
	FN_F6=0x0075,
	FN_F7=0x0076,
	FN_F8=0x0077,
	FN_F9=0x0078,
	FN_F10=0x0079,
	FN_F11=0x007A,
	FN_F12=0x007B,
	FN_F13=0x007C,
	FN_F14=0x007D,
	FN_F15=0x007E,
	FN_F16=0x007F,
	FN_F17=0x0080,
	FN_F18=0x0081,
	FN_F19=0x0082,
	IOS_HOME=0x0083,
	ANDROID_HOME=0x0084,
	ANDROID_MENU=0x0085,
	ANDROID_SEARCH=0x0086,
	ANDROID_BACK=0x0087,
	HOME_COMBO=0x0088,
	LOCK_COMBO=0x0089,
	IOS_VIRTUAL_KEYBOARD=0x008A,
	IOS_LANGUAGE_SWICH=0x008B,
	MAC_EXPOSE=0x008C,
	MAC_DASHBOARD=0x008D,
	WIN7_SNAP_LEFT=0x008E,
	WIN7_SNAP_RIGHT=0x008F,
	Minimize_Window=0x0090,		# WIN7_MINIMIZE_AS_WIN_ARROW
	Maximize_Window=0x0091,		# WIN7_MAXIMIZE_AS_WIN_ARROW
	WIN7_STRETCH_UP=0x0092,
	WIN7_MONITOR_SWITCH_AS_WIN_SHIFT_LEFTARROW=0x0093,
	WIN7_MONITOR_SWITCH_AS_WIN_SHIFT_RIGHTARROW=0x0094,
	Switch_Screen=0x0095,		# WIN7_SHOW_PRESENTATION_MODE
	WIN7_SHOW_MOBILITY_CENTER=0x0096,
	ANALOG_HSCROLL=0x0097,
	METRO_APPSWITCH=0x009F,
	METRO_APPBAR=0x00A0,
	METRO_CHARMS=0x00A1,
	CALC_VKEYBOARD=0x00A2,
	METRO_SEARCH=0x00A3,
	COMBO_SLEEP=0x00A4,
	METRO_SHARE=0x00A5,
	METRO_SETTINGS=0x00A6,
	METRO_DEVICES=0x00A7,
	METRO_START_SCREEN=0x00A9,
	ZOOMIN=0x00AA,
	ZOOMOUT=0x00AB,
	BACK_HSCROLL=0x00AC,
	SHOW_DESKTOP_HPP=0x00AE,
	Fn_Left_Click=0x00B7,		# from K400 Plus
	Yellow_Left_Click_Key=0x00B8,	# from K400 Plus
    	Screen_Capture=0x00BF,		# from Craft Keyboard
	Thumb_Button=0x00C3,		# from MX Master
    	Top_Button=0x00C4,		# from MX Master
	Brightness_Down=0x00C7,		# from Craft Keyboard
	Brightness_Up=0x00C8,		# from Craft Keyboard
	Switch_Workspaces=0x00E0,	# from Craft Keyboard
	Application_Launcher=0x00E1,	# from Craft Keyboard
	Backlight_Down=0x00E2,		# from Craft Keyboard
	Backlight_Up=0x00E3,		# from Craft Keyboard
	Previous_Fn=0x00E4,		# from Craft Keyboard
	Play__Pause_Fn=0x00E5,		# from Craft Keyboard
	Next_Fn=0x00E6,			# from Craft Keyboard
	Mute_Fn=0x00E7,			# from Craft Keyboard
	Volume_Down_Fn=0x00E8,		# from Craft Keyboard
	Volume_Up_Fn=0x00E9,		# from Craft Keyboard
	Context_Menu=0x00EA,			# from Craft Keyboard
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
	Music=0x001D, # also known as MediaPlayer

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
	Search=0x0029, # also known as AdvSmartSearch
	RecordMediaPlayer=0x002A,
	BrowserRefresh=0x002B,
	RotateRight=0x002C,
	Search_Files=0x002D,		# SearchForFiles
	MM_SHUFFLE=0x002E,
	Sleep=0x002F, # also known as StandBySet
	BrowserStop=0x0030,
	OneTouchSync=0x0031,
	ZoomSet=0x0032,
	ZoomBtnInSet2=0x0033,
	ZoomBtnInSet=0x0034,
	ZoomBtnOutSet2=0x0035,
	ZoomBtnOutSet=0x0036,
	ZoomBtnResetSet=0x0037,
	Left_Click=0x0038,		# LeftClick
	Right_Click=0x0039,		# RightClick
	Mouse_Middle_Button=0x003A,	# from M510v2 was MiddleMouseButton
	Back=0x003B,
	Mouse_Back_Button=0x003C,	# from M510v2 was BackEx
	BrowserForward=0x003D,
	Mouse_Forward_Button=0x003E,	# from M510v2 was BrowserForwardEx
	Mouse_Scroll_Left_Button_=0x003F,	# from M510v2 was HorzScrollLeftSet
	Mouse_Scroll_Right_Button=0x0040,	# from M510v2 was HorzScrollRightSet
	QuickSwitch=0x0041,
	BatteryStatus=0x0042,
	Show_Desktop=0x0043,		# ShowDesktop
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
	Do_Nothing_One=0x0062, # also known as Do_Nothing
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
	Calculator_VKEY=0x007B, # also known as Calculator
	MetroSearch=0x007C,
	MetroStartScreen=0x0080,
	MetroShare=0x007D,
	MetroSettings=0x007E,
	MetroDevices=0x007F,
	MetroBackLeftHorz=0x0082,
	MetroForwRightHorz=0x0083,
	Win8_Back=0x0084, # also known as MetroCharms
	Win8_Forward=0x0085, # also known as AppSwitchBar
	Win8Charm_Appswitch_GifAnimation=0x0086,
	Win8BackHorzLeft=0x008B, # also known as Back
	Win8ForwardHorzRight=0x008C, # also known as BrowserForward
	MetroSearch2=0x0087,
	MetroShare2=0x0088,
	MetroSettings2=0x008A,
	MetroDevices2=0x0089,
	Win8MetroWin7Forward=0x008D, # also known as MetroStartScreen
	Win8ShowDesktopWin7Back=0x008E, # also known as ShowDesktop
	MetroApplicationSwitch=0x0090, # also known as MetroStartScreen
	ShowUI=0x0092,
	Switch_Screen=0x0093,		# from K400 Plus
	Maximize_Window=0x0095,		# from K400 Plus
	Screen_Capture=0x009B,		# from Craft Keyboard
	Toggle_Free_Spin=0x009D,	# from MX Master
	Mouse_Thumb_Button=0x00A9,	# from MX Master
	Brightness_Down=0x00A3,		# from Craft Keyboard
	Brightness_Up=0x00A4,		# from Craft Keyboard
	Switch_Workspace=0x00BF,	# from Craft Keyboard
	Application_Launcher=0x00C0,	# from Craft Keyboard
	Backlight_Down=0x00C1,		# from Craft Keyboard
	Backlight_Up=0x00C2,		# from Craft Keyboard
	Context_Menu=0x00C3,		# from Craft Keyboard
)
TASK._fallback = lambda x: 'unknown:%04X' % x
# hidpp 4.5 info from https://lekensteyn.nl/files/logitech/x1b04_specialkeysmsebuttons.html
KEY_FLAG = _NamedInts(
	virtual=0x80,
	persistently_divertable=0x40,
	divertable=0x20,
	reprogrammable=0x10,
	FN_sensitive=0x08,
	nonstandard=0x04,
	is_FN=0x02,
	mse=0x01
)

DISABLE = _NamedInts(
	Caps_Lock=0x01,
	Num_Lock=0x02,
	Scroll_Lock=0x04,
	Insert=0x08,
	Win=0x10, # aka Super
)
DISABLE._fallback = lambda x: 'unknown:%02X' % x
