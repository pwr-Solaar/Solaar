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


def run(receivers, args, find_receiver, find_device):
    assert receivers

    if getattr(args, "slot", None) is not None:
        _run_slot_unpair(receivers, args, find_receiver)
        return

    assert args.device, "unpair requires a device name, or use --slot"

    device_name = args.device.lower()
    dev = next(find_device(receivers, device_name), None)
    if not dev:
        raise Exception(f"no device found matching '{device_name}'")

    if not dev.receiver.may_unpair:
        print(
            f"Receiver with USB id {dev.receiver.product_id} for {dev.name} [{dev.wpid}:{dev.serial}] does not unpair,",
            "but attempting anyway.",
        )
    try:
        # query these now, it's last chance to get them
        number, codename, wpid, serial = dev.number, dev.codename, dev.wpid, dev.serial
        dev.receiver._unpair_device(number, True)  # force an unpair
        print(f"Unpaired {int(number)}: {dev.name} ({codename}) [{wpid}:{serial}]")
    except Exception as e:
        raise e


def _run_slot_unpair(receivers, args, find_receiver):
    if args.receiver:
        rcv = find_receiver(receivers, args.receiver.lower())
        if not rcv:
            raise Exception(f"no receiver found matching '{args.receiver}'")
    elif len(receivers) == 1:
        rcv = receivers[0]
    else:
        names = ", ".join(f"{r.name} [{r.serial}]" for r in receivers)
        raise Exception(f"multiple receivers present, pass --receiver to pick one (found: {names})")

    if rcv.receiver_kind != "lightspeed":
        raise Exception(
            f"--slot unpair is currently only supported on Lightspeed receivers "
            f"(this is a {rcv.receiver_kind or 'unknown'} receiver: {rcv.name})"
        )

    slot = int(args.slot)
    max_slots = rcv.max_devices or 1
    if slot < 1 or slot > max_slots:
        raise Exception(f"--slot {slot} out of range (valid: 1..{max_slots} on {rcv.name})")

    # Populate the cache from the receiver's pairing registers so we can report
    # what the slot currently holds. Truthy cache does NOT imply the device is
    # reachable on RF — it only means the pairing registers are readable.
    list(rcv)
    cached = rcv._devices.get(slot)
    if cached:
        slot_desc = f"{cached.name} [{cached.wpid}:{cached.serial}]"
    elif slot in rcv._devices:
        slot_desc = "cached None sentinel (pairing info unreadable)"
    else:
        slot_desc = "no pairing info cached"

    print(f"Slot {slot} on {rcv.name} [{rcv.serial}]: {slot_desc}")

    if getattr(args, "dry_run", False):
        print(f"[dry-run] would force-unpair slot {slot} — no register write issued")
        return

    ok = rcv.force_unpair_slot(slot)
    if ok:
        print(f"Slot {slot} unpair register write acknowledged by receiver")
    else:
        print(f"Slot {slot} unpair register write was not acknowledged (may be a no-op)")
