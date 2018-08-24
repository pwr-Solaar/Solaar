# Logitech MK240 NANO Device Information
## `solaar show all` Dump
```
Unifying Receiver (NOTE: NOT claimed to be supporting Unifying from the package box, the only advanced feature that may be related is 128-bit AES encryption) (M/N: C-U0010)
  Device path  : /dev/hidraw0
  USB id       : 046d:c534
  Serial       : 0
    Firmware   : 29.01.B0016
  Has 2 paired device(s) out of a maximum of 6.
  Notifications: wireless, software present (0x000900)

  1: Wireless Keyboard MK270 (NOTE: The Product is actually "MK240 NANO Wireless Keyboard and Mouse Combo" with the "K240"(M/N: Y-R0036) keyboard model)
     Codename     : MK270
     Kind         : keyboard
     Wireless PID : 4023
     Protocol     : HID++ 2.0
     Polling rate : 20 ms (50Hz)
     Serial number: 4BBBBA4A
          Firmware: RQK 49.00.B0029
     Supports 18 HID++ 2.0 features:
         0: ROOT                   {0000}   
         1: FEATURE SET            {0001}   
         2: DEVICE FW VERSION      {0003}   
         3: DEVICE NAME            {0005}   
         4: BATTERY STATUS         {1000}   
         5: REPROG CONTROLS        {1B00}   
         6: WIRELESS DEVICE STATUS {1D4B}   
         7: FN INVERSION           {40A0}   
         8: ENCRYPTION             {4100}   
         9: KEYBOARD LAYOUT        {4520}   
        10: unknown:1810           {1810}   internal, hidden
        11: unknown:1830           {1830}   internal, hidden
        12: unknown:1890           {1890}   internal, hidden
        13: unknown:18A0           {18A0}   internal, hidden
        14: unknown:18B0           {18B0}   internal, hidden
        15: unknown:1DF3           {1DF3}   internal, hidden
        16: unknown:1E00           {1E00}   hidden
        17: unknown:1868           {1868}   internal, hidden
     Has 11 reprogrammable keys:
         0: MY HOME                    => HomePage                      is FN, FN sensitive, reprogrammable
         1: Mail                       => Email                         is FN, FN sensitive, reprogrammable
         2: SEARCH                     => Search                        is FN, FN sensitive, reprogrammable
         3: Calculator                 => Calculator                    is FN, FN sensitive, reprogrammable
         4: MEDIA PLAYER               => Music                         is FN, FN sensitive, reprogrammable
         5: Previous                   => Previous                      is FN, FN sensitive
         6: Play/Pause                 => Play/Pause                    is FN, FN sensitive
         7: Next                       => Next                          is FN, FN sensitive
         8: Mute                       => Mute                          is FN, FN sensitive
         9: Volume Down                => Volume Down                   is FN, FN sensitive
        10: Volume Up                  => Volume Up                     is FN, FN sensitive
     Battery: 30%, discharging. (NOTE: Capacity readings appears to be faked, or in extremely low sensitivity)

  2: Wireless Mouse M150 (NOTE: The Product is actually "MK240 NANO Wireless Keyboard and Mouse Combo" with the "M212"(M/N: M-R0041) mouse model)
     Codename     : M150
     Kind         : mouse
     Wireless PID : 4022
     Protocol     : HID++ 2.0
     Polling rate : 8 ms (125Hz)
     Serial number: 00000000
          Firmware: RQM 38.00.B0044
     Supports 18 HID++ 2.0 features:
         0: ROOT                   {0000}   
         1: FEATURE SET            {0001}   
         2: DEVICE FW VERSION      {0003}   
         3: DEVICE NAME            {0005}   
         4: BATTERY STATUS         {1000}   
         5: REPROG CONTROLS        {1B00}   
         6: WIRELESS DEVICE STATUS {1D4B}   
         7: VERTICAL SCROLLING     {2100}   
         8: MOUSE POINTER          {2200}   
         9: unknown:1810           {1810}   internal, hidden
        10: unknown:1830           {1830}   internal, hidden
        11: unknown:1850           {1850}   internal, hidden
        12: unknown:1890           {1890}   internal, hidden
        13: unknown:18B0           {18B0}   internal, hidden
        14: unknown:1DF3           {1DF3}   internal, hidden
        15: unknown:1868           {1868}   internal, hidden
        16: unknown:1869           {1869}   internal, hidden
        17: unknown:1E00           {1E00}   hidden
     Has 3 reprogrammable keys:
         0: LEFT CLICK                 => LeftClick                     mse, reprogrammable
         1: RIGHT CLICK                => RightClick                    mse, reprogrammable
         2: MIDDLE BUTTON              => MiddleMouseButton             mse, reprogrammable
     Battery: 30%, discharging. (NOTE: Capacity readings appears to be faked, or in extremely low sensitivity, in the Logitech SetPoint utility battery level is displayed as "HIGH")
```

## Connect Utility Report
```
Re-Connect Software Version : 2.00.3
Dj Api Version : 2, 50, 25

接收器(Receiver)
Name : 無線接收器(Wireless Receiver)
ModelId : 0x46dc534
Serial Number : 
Handle : 0xff000001
Wireless Status : 0x3
Firmware version : 029.001.00016
Bootloader version : 
Dfu Status : 0x1
Is Dfu Cancellable : Yes
Max Device Capacity : 6

    滑鼠(Mouse)
    Name :  
    ModelId : 0x0
    Serial Number : 4022-00-00-00-00
    Handle : 0x2000003
    Wireless Status : 0x0
    Firmware version : 038.000.00044
    Bootloader version : 
    Dfu Status : 0x1
    Is Dfu Cancellable : No
    Battery Status : 0x2
    Parent Handle : 0xff000001

    鍵盤(Keyboard)
    Name :  
    ModelId : 0x0
    Serial Number : 4023-4B-BB-BA-4A
    Handle : 0x1000002
    Wireless Status : 0x0
    Firmware version : 049.000.00029
    Bootloader version : 
    Dfu Status : 0x1
    Is Dfu Cancellable : No
    Battery Status : 0x2
    Parent Handle : 0xff000001
```
