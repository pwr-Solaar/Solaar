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


NAME = type('NAME', (),
				dict(
					M315='Wireless Mouse M315',
					M325='Wireless Mouse M325',
					M510='Wireless Mouse M510',
					M515='Couch Mouse M515',
					M570='Wireless Trackball M570',
					K270='Wireless Keyboard K270',
					K350='Wireless Keyboard K350',
					K750='Wireless Solar Keyboard K750',
					K800='Wireless Illuminated Keyboard K800',
				))

from ..unifying_receiver.common import FallbackDict

FULL_NAME = FallbackDict(lambda x: x,
				dict(
					M315=NAME.M315,
					M325=NAME.M325,
					M510=NAME.M510,
					M515=NAME.M515,
					M570=NAME.M570,
					K270=NAME.K270,
					K350=NAME.K350,
					K750=NAME.K750,
					K800=NAME.K800,
				))

del FallbackDict
