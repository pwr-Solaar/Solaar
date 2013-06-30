#
# USB ids of Logitech wireless receivers.
# Only receivers supporting the HID++ protocol can go in here.
#

from __future__ import absolute_import, division, print_function, unicode_literals

# each tuple contains (vendor_id, product_id, usb interface number, hid driver)

# standard Unifying receivers (marked with the orange Unifying logo)
UNIFYING_RECEIVER         = (0x046d, 0xc52b, 2, 'logitech-djreceiver')
UNIFYING_RECEIVER_2       = (0x046d, 0xc532, 2, 'logitech-djreceiver')

# Nano receviers that support the Unifying protocol
NANO_RECEIVER_ADVANCED    = (0x046d, 0xc52f, 1, 'hid-generic')

# Nano receivers that don't support the Unifying protocol
NANO_RECEIVER_C517        = (0x046d, 0xc517, 1, 'hid-generic')
NANO_RECEIVER_C518        = (0x046d, 0xc518, 1, 'hid-generic')
NANO_RECEIVER_C51A        = (0x046d, 0xc51a, 1, 'hid-generic')
NANO_RECEIVER_C51B        = (0x046d, 0xc51b, 1, 'hid-generic')
NANO_RECEIVER_C521        = (0x046d, 0xc521, 1, 'hid-generic')
NANO_RECEIVER_C525        = (0x046d, 0xc525, 1, 'hid-generic')
NANO_RECEIVER_C526        = (0x046d, 0xc526, 1, 'hid-generic')



ALL = (
		UNIFYING_RECEIVER,
		UNIFYING_RECEIVER_2,
		NANO_RECEIVER_ADVANCED,
		NANO_RECEIVER_C517,
		NANO_RECEIVER_C518,
		NANO_RECEIVER_C51A,
		NANO_RECEIVER_C51B,
		NANO_RECEIVER_C521,
		NANO_RECEIVER_C525,
		NANO_RECEIVER_C526,
	)
