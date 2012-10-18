#
#
#

STATUS = type('STATUS', (),
				dict(
					UNKNOWN=-9999,
					UNAVAILABLE=-1,
					BOOTING=0,
					CONNECTED=1,
				))

STATUS_NAME = {
					STATUS.UNKNOWN: '...',
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
				))

# when the receiver reports a device that is not connected
# (and thus cannot be queried), guess the name and type
# based on this table
NAMES = {
			'M315': ('Wireless Mouse M315', 'mouse'),
			'M325': ('Wireless Mouse M325', 'mouse'),
			'M510': ('Wireless Mouse M510', 'mouse'),
			'M515': ('Couch Mouse M515', 'mouse'),
			'M570': ('Wireless Trackball M570', 'trackball'),
			'K270': ('Wireless Keyboard K270', 'keyboard'),
			'K350': ('Wireless Keyboard K350', 'keyboard'),
			'K750': ('Wireless Solar Keyboard K750', 'keyboard'),
			'K800': ('Wireless Illuminated Keyboard K800', 'keyboard'),
		}
