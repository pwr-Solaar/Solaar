#
#
#

STATUS = type('STATUS', (),
				dict(
					UNKNOWN=-9999,
					UNAVAILABLE=-1,
					CONNECTED=0,
				))

STATUS_NAME = {
					STATUS.UNAVAILABLE: 'inactive',
					STATUS.CONNECTED: 'connected',
				}


PROPS = type('PROPS', (),
				dict(
					TEXT='text',
					BATTERY_LEVEL='battery_level',
					BATTERY_STATUS='battery_status',
					LIGHT_LEVEL='light_level',
				))
