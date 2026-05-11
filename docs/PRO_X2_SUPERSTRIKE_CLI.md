# Logitech PRO X 2 Superstrike - Solaar CLI Reference

This document describes all available settings for the Logitech PRO X 2 Superstrike mouse via the Solaar CLI.

## Device Identification

| Property | Value |
|----------|-------|
| Name | PRO X 2 Superstrike |
| WPID | 40BD |
| Protocol | HID++ 4.2 |
| Kind | mouse |

## General CLI Syntax

```bash
# List all settings for device
solaar config <device>

# Read a specific setting
solaar config <device> <setting-name>

# Write a specific setting
solaar config <device> <setting-name> <value>
```

The `<device>` can be:
- Device number (e.g., `1`)
- Device name (e.g., `"PRO X 2 Superstrike"`)
- Serial number (e.g., `A1C55DB2`)

---

## Available Settings

### 1. Onboard Profiles

Controls whether the device uses its onboard profile or host-controlled settings.

| Property | Value |
|----------|-------|
| Setting Name | `onboard_profiles` |
| Type | Choice |
| Possible Values | `Disabled`, `Profile 1` |

**Commands:**

```bash
# Read current value
solaar config 1 onboard_profiles

# Set to disabled (allows host control of DPI, report rate, etc.)
solaar config 1 onboard_profiles Disabled

# Set to Profile 1 (use onboard profile)
solaar config 1 onboard_profiles "Profile 1"
```

**Note:** Many settings require `onboard_profiles` to be set to `Disabled` to be effective.

---

### 2. Report Rate

Controls the frequency of device movement reports.

| Property | Value |
|----------|-------|
| Setting Name | `report_rate_extended` |
| Type | Choice |
| Possible Values | `8ms`, `4ms`, `2ms`, `1ms`, `500us`, `250us`, `125us` |

**Commands:**

```bash
# Read current value
solaar config 1 report_rate_extended

# Set to 1ms (1000Hz)
solaar config 1 report_rate_extended 1ms

# Set to 500us (2000Hz)
solaar config 1 report_rate_extended 500us

# Set to 125us (8000Hz)
solaar config 1 report_rate_extended 125us
```

**Polling Rate Reference:**

| Value | Polling Rate |
|-------|--------------|
| `8ms` | 125 Hz |
| `4ms` | 250 Hz |
| `2ms` | 500 Hz |
| `1ms` | 1000 Hz |
| `500us` | 2000 Hz |
| `250us` | 4000 Hz |
| `125us` | 8000 Hz |

---

### 3. Sensitivity (DPI)

Controls mouse movement sensitivity.

| Property | Value |
|----------|-------|
| Setting Name | `dpi_extended` |
| Type | Complex (X, Y, LOD) |
| DPI Range | 100 - 32000 |
| LOD Values | `LOW`, `HIGH` |

**Commands:**

```bash
# Read current value
solaar config 1 dpi_extended

# Set DPI (format: {X:<value>, Y:<value>, LOD:<value>})
solaar config 1 dpi_extended "{X:800, Y:800, LOD:HIGH}"

# Set to 1600 DPI
solaar config 1 dpi_extended "{X:1600, Y:1600, LOD:HIGH}"

# Set different X and Y sensitivity
solaar config 1 dpi_extended "{X:800, Y:1600, LOD:LOW}"
```

---

## HITS Tuning Settings (Hall-Effect Inductive Trigger Switch)

These settings control the advanced click behavior of the PRO X 2 Superstrike's hall-effect switches.

### 4. Actuation Point

Controls how deep the button must be pressed to register a click.

| Property | Value |
|----------|-------|
| Setting Name (Left) | `superstrike-tuning_actuation-0` |
| Setting Name (Right) | `superstrike-tuning_actuation-1` |
| Type | Range |
| Range | 1 - 10 |
| Default | 5 |

**Value Interpretation:**
- `1` = Shallowest (hair trigger, minimal press)
- `10` = Deepest (full press required)

**Commands:**

```bash
# Read left button actuation
solaar config 1 superstrike-tuning_actuation-0

# Read right button actuation
solaar config 1 superstrike-tuning_actuation-1

# Set left button to shallow actuation (hair trigger)
solaar config 1 superstrike-tuning_actuation-0 1

# Set left button to deep actuation
solaar config 1 superstrike-tuning_actuation-0 10

# Set right button to medium actuation
solaar config 1 superstrike-tuning_actuation-1 5
```

---

### 5. Rapid Trigger Level

Controls the rapid trigger sensitivity, which allows the button to re-actuate quickly after partial release.

| Property | Value |
|----------|-------|
| Setting Name (Left) | `superstrike-tuning_rapid-trigger-level-0` |
| Setting Name (Right) | `superstrike-tuning_rapid-trigger-level-1` |
| Type | Range |
| Range | 1 - 5 |
| Default | 3 |

**Value Interpretation:**
- `1` = Fastest (most sensitive, smallest movement to re-trigger)
- `5` = Slowest (least sensitive, larger movement needed)

**Note:** Rapid trigger cannot be disabled on this device. The minimum level is 1.

**Commands:**

```bash
# Read left button rapid trigger level
solaar config 1 superstrike-tuning_rapid-trigger-level-0

# Read right button rapid trigger level
solaar config 1 superstrike-tuning_rapid-trigger-level-1

# Set left button to fastest rapid trigger
solaar config 1 superstrike-tuning_rapid-trigger-level-0 1

# Set left button to slowest rapid trigger
solaar config 1 superstrike-tuning_rapid-trigger-level-0 5

# Set right button to medium rapid trigger
solaar config 1 superstrike-tuning_rapid-trigger-level-1 3
```

---

### 6. Click Haptics

Controls the intensity of the haptic feedback when clicking.

| Property | Value |
|----------|-------|
| Setting Name (Left) | `superstrike-tuning_haptics-0` |
| Setting Name (Right) | `superstrike-tuning_haptics-1` |
| Type | Range |
| Range | 0 - 5 |
| Default | 3 |

**Value Interpretation:**
- `0` = Off (no haptic feedback)
- `1` = Minimal
- `2` = Light
- `3` = Medium
- `4` = Strong
- `5` = Strongest (maximum haptic feedback)

**Commands:**

```bash
# Read left button haptics level
solaar config 1 superstrike-tuning_haptics-0

# Read right button haptics level
solaar config 1 superstrike-tuning_haptics-1

# Disable haptics on left button
solaar config 1 superstrike-tuning_haptics-0 0

# Set left button to maximum haptics
solaar config 1 superstrike-tuning_haptics-0 5

# Set right button to medium haptics
solaar config 1 superstrike-tuning_haptics-1 3
```

---

## Complete Settings Summary

| Setting | CLI Name | Type | Range/Values | Button-Specific |
|---------|----------|------|--------------|-----------------|
| Onboard Profiles | `onboard_profiles` | Choice | `Disabled`, `Profile 1` | No |
| Report Rate | `report_rate_extended` | Choice | `8ms` to `125us` | No |
| Sensitivity | `dpi_extended` | Complex | 100-32000 DPI | No |
| Actuation Point | `superstrike-tuning_actuation-{0,1}` | Range | 1-10 | Yes |
| Rapid Trigger | `superstrike-tuning_rapid-trigger-level-{0,1}` | Range | 1-5 | Yes |
| Click Haptics | `superstrike-tuning_haptics-{0,1}` | Range | 0-5 | Yes |

---

## Batch Configuration Examples

### Gaming Profile (Fast Response)

```bash
#!/bin/bash
# Gaming profile: fast actuation, sensitive rapid trigger, medium haptics

solaar config 1 onboard_profiles Disabled
solaar config 1 report_rate_extended 125us
solaar config 1 dpi_extended "{X:800, Y:800, LOD:HIGH}"

# Left button - hair trigger
solaar config 1 superstrike-tuning_actuation-0 1
solaar config 1 superstrike-tuning_rapid-trigger-level-0 1
solaar config 1 superstrike-tuning_haptics-0 3

# Right button - hair trigger
solaar config 1 superstrike-tuning_actuation-1 1
solaar config 1 superstrike-tuning_rapid-trigger-level-1 1
solaar config 1 superstrike-tuning_haptics-1 3
```

### Productivity Profile (Comfortable)

```bash
#!/bin/bash
# Productivity profile: deeper actuation, slower rapid trigger, strong haptics

solaar config 1 onboard_profiles Disabled
solaar config 1 report_rate_extended 1ms
solaar config 1 dpi_extended "{X:1600, Y:1600, LOD:HIGH}"

# Left button - comfortable click
solaar config 1 superstrike-tuning_actuation-0 7
solaar config 1 superstrike-tuning_rapid-trigger-level-0 4
solaar config 1 superstrike-tuning_haptics-0 5

# Right button - comfortable click
solaar config 1 superstrike-tuning_actuation-1 7
solaar config 1 superstrike-tuning_rapid-trigger-level-1 4
solaar config 1 superstrike-tuning_haptics-1 5
```

### Silent Profile (No Haptics)

```bash
#!/bin/bash
# Silent profile: no haptic feedback

solaar config 1 superstrike-tuning_haptics-0 0
solaar config 1 superstrike-tuning_haptics-1 0
```

---

## Programmatic Usage

### Reading All Settings (JSON-like parsing)

```bash
# Get all settings as output
solaar config 1 2>/dev/null | grep "^[a-z]" | while read line; do
    setting=$(echo "$line" | cut -d'=' -f1 | tr -d ' ')
    value=$(echo "$line" | cut -d'=' -f2 | tr -d ' ')
    echo "{\"setting\": \"$setting\", \"value\": \"$value\"}"
done
```

### Reading a Single Setting Value

```bash
# Extract just the value
solaar config 1 superstrike-tuning_actuation-0 2>/dev/null | grep "^superstrike" | cut -d'=' -f2 | tr -d ' '
```

### Error Handling

```bash
# Check if command succeeded
if solaar config 1 superstrike-tuning_actuation-0 5 2>/dev/null; then
    echo "Setting applied successfully"
else
    echo "Failed to apply setting"
fi
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (device not found, invalid setting, invalid value) |

---

## Notes

1. **Device Discovery**: Use `solaar show` to list all connected devices and their indices.

2. **Persistence**: Settings are saved to `~/.config/solaar/config.yaml` and automatically reapplied when the device reconnects.

3. **Onboard Profiles**: When `onboard_profiles` is set to `Profile 1`, some settings (DPI, report rate) are controlled by the device's onboard memory and cannot be changed via Solaar.

4. **HITS Settings**: The actuation, rapid trigger, and haptics settings are stored in the device and persist across reconnections, regardless of the onboard profile setting.

5. **Button Index**: `0` = Left button, `1` = Right button.
