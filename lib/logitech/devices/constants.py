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
					STATUS.UNAVAILABLE: 'inactive',
					STATUS.BOOTING: 'initializing',
					STATUS.CONNECTED: 'connected',
				}


PROPS = type('PROPS', (),
				dict(
					TEXT='text',
					BATTERY_LEVEL='battery_level',
					BATTERY_STATUS='battery_status',
					LIGHT_LEVEL='light_level',
				))
