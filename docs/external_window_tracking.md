# External Window Tracking

Starting from this version, Solaar provides an alternative method for window tracking that allows external services to notify Solaar about active windows and windows under the pointer.

## Background

Previously, Solaar could only track windows in two ways:
1. Using X11 APIs (when running under X11)
2. Using the Solaar GNOME Shell extension (when running under Wayland with GNOME)

This limitation made it difficult to use window-based rules in other desktop environments like KDE Plasma on Wayland.

## New DBus Methods

Solaar now exposes two DBus methods that external services can call to provide window information:

### UpdateActiveWindow

Updates the active window information.

**Interface**: `io.github.pwr_solaar.solaar`  
**Object Path**: `/io/github/pwr_solaar/solaar`  
**Method**: `UpdateActiveWindow(s wm_class)`  
**Parameters**: 
- `wm_class` (string): The WM_CLASS or application identifier of the active window

### UpdatePointerOverWindow

Updates the window under the pointer.

**Interface**: `io.github.pwr_solaar.solaar`  
**Object Path**: `/io/github/pwr_solaar/solaar`  
**Method**: `UpdatePointerOverWindow(s wm_class)`  
**Parameters**: 
- `wm_class` (string): The WM_CLASS or application identifier of the window under the pointer

## Usage Examples

### From Command Line

You can test the functionality using `dbus-send`:

```bash
# Update active window
dbus-send --session --dest=io.github.pwr_solaar.solaar \
  --type=method_call \
  /io/github/pwr_solaar/solaar \
  io.github.pwr_solaar.solaar.UpdateActiveWindow \
  string:"firefox"

# Update pointer-over window
dbus-send --session --dest=io.github.pwr_solaar.solaar \
  --type=method_call \
  /io/github/pwr_solaar/solaar \
  io.github.pwr_solaar.solaar.UpdatePointerOverWindow \
  string:"konsole"
```

### From KDE/KWin Script

You can create a KWin script to automatically notify Solaar about window changes:

```javascript
// KWin Script to notify Solaar about active window changes
workspace.clientActivated.connect(function(client) {
    if (client) {
        // Get the window class
        var wmClass = client.resourceClass.toString();
        
        // Call Solaar's DBus method
        callDBus(
            "io.github.pwr_solaar.solaar",
            "/io/github/pwr_solaar/solaar",
            "io.github.pwr_solaar.solaar",
            "UpdateActiveWindow",
            wmClass
        );
    }
});
```

### From Python Script

```python
import dbus

# Connect to session bus
bus = dbus.SessionBus()

# Get Solaar service
solaar = bus.get_object(
    'io.github.pwr_solaar.solaar',
    '/io/github/pwr_solaar/solaar'
)

# Update active window
solaar.UpdateActiveWindow('firefox', dbus_interface='io.github.pwr_solaar.solaar')

# Update pointer-over window
solaar.UpdatePointerOverWindow('konsole', dbus_interface='io.github.pwr_solaar.solaar')
```

## How It Works

When you call `UpdateActiveWindow` or `UpdatePointerOverWindow`, Solaar caches the provided window information. When rules with `Process` or `MouseProcess` conditions are evaluated, Solaar checks for cached values first before trying other methods (X11 or GNOME Shell extension).

This means:
1. External services have priority - if they provide window information, Solaar uses it
2. If no cached value is available, Solaar falls back to X11 (if not on Wayland)
3. As a last resort, Solaar tries the GNOME Shell extension (if on Wayland)

## Notes

- The cached window information persists until it's updated again or Solaar is restarted
- External services should update the window information whenever the active window or pointer position changes
- The `wm_class` parameter should match the application identifier used in your Solaar rules
