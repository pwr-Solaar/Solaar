#
#
#

STATUS = type('STATUS', (),
				dict(
					UI_NOTIFY=0x01,
					UI_POPUP=0x02,
					UNKNOWN=-0xFFFF,
					UNPAIRED=-0x1000,
					UNAVAILABLE=-1,
					BOOTING=0,
					CONNECTED=1,
				))

STATUS_NAME = {
					STATUS.UNKNOWN: '...',
					STATUS.UNPAIRED: 'unpaired',
					STATUS.UNAVAILABLE: 'inactive',
					STATUS.BOOTING: 'initializing',
					STATUS.CONNECTED: 'connected',
				}


# device properties that may be reported
PROPS = type('PROPS', (),
				dict(
					BATTERY_LEVEL='battery_level',
					BATTERY_STATUS='battery_status',
					LIGHT_LEVEL='light_level',
					UI_FLAGS='ui_flags',
				))

# when the receiver reports a device that is not connected
# (and thus cannot be queried), guess the name and type
# based on this table
NAMES = {
			'M315': ('Wireless Mouse M315', 'mouse'),
			'M325': ('Wireless Mouse M325', 'mouse'),
			'M505': ('Wireless Mouse M505', 'mouse'),
			'M510': ('Wireless Mouse M510', 'mouse'),
			'M515': ('Couch Mouse M515', 'mouse'),
			'M525': ('Wireless Mouse M525', 'mouse'),
			'M570': ('Wireless Trackball M570', 'trackball'),
			'M600': ('Touch Mouse M600', 'mouse'),
			'M705': ('Marathon Mouse M705', 'mouse'),
			'K270': ('Wireless Keyboard K270', 'keyboard'),
			'K350': ('Wireless Keyboard K350', 'keyboard'),
			'K360': ('Wireless Keyboard K360', 'keyboard'),
			'K400': ('Wireless Touch Keyboard K400', 'keyboard'),
			'K750': ('Wireless Solar Keyboard K750', 'keyboard'),
			'K800': ('Wireless Illuminated Keyboard K800', 'keyboard'),
			'T400': ('Zone Touch Mouse T400', 'mouse'),
			'T650': ('Wireless Rechargeable Touchpad T650', 'touchpad'),
			'Cube': ('Logitech Cube', 'mouse'),
			'Anywhere MX': ('Anywhere Mouse MX', 'mouse'),
			'Performance MX': ('Performance Mouse MX', 'mouse'),
		}
