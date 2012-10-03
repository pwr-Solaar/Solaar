#
#
#

STATUS = type('STATUS', (),
				dict(
					UNKNOWN=None,
					UNAVAILABLE=-1,
					CONNECTED=0,
					# ACTIVE=1,
				))

PROPS = type('PROPS', (),
				dict(
					TEXT='text',
					BATTERY_LEVEL='battery-level',
					BATTERY_STATUS='battery-status',
					LIGHT_LUX='lux',
					LIGHT_LEVEL='light-level',
				))


from collections import defaultdict

STATUS_NAME = defaultdict(lambda x: None)
STATUS_NAME[STATUS.UNAVAILABLE] = 'disconnected'
STATUS_NAME[STATUS.CONNECTED] = 'connected'
# STATUS_NAME[STATUS.ACTIVE] = 'active'

del defaultdict
