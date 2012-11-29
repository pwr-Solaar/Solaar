#
#
#

from collections import namedtuple
_D = namedtuple('_DeviceDescriptor', ['codename', 'name', 'kind'])
del namedtuple

DEVICES = ( _D('M315', 'Wireless Mouse M315', 'mouse'),
			_D('M325', 'Wireless Mouse M325', 'mouse'),
			_D('M505', 'Wireless Mouse M505', 'mouse'),
			_D('M510', 'Wireless Mouse M510', 'mouse'),
			_D('M515', 'Couch Mouse M515', 'mouse'),
			_D('M525', 'Wireless Mouse M525', 'mouse'),
			_D('M570', 'Wireless Trackball M570', 'trackball'),
			_D('M600', 'Touch Mouse M600', 'mouse'),
			_D('M705', 'Marathon Mouse M705', 'mouse'),
			_D('K270', 'Wireless Keyboard K270', 'keyboard'),
			_D('K350', 'Wireless Keyboard K350', 'keyboard'),
			_D('K360', 'Wireless Keyboard K360', 'keyboard'),
			_D('K400', 'Wireless Touch Keyboard K400', 'keyboard'),
			_D('K750', 'Wireless Solar Keyboard K750', 'keyboard'),
			_D('K800', 'Wireless Illuminated Keyboard K800', 'keyboard'),
			_D('T400', 'Zone Touch Mouse T400', 'mouse'),
			_D('T650', 'Wireless Rechargeable Touchpad T650', 'touchpad'),
			_D('Cube', 'Logitech Cube', 'mouse'),
			_D('Anywhere MX', 'Anywhere Mouse MX', 'mouse'),
			_D('Performance MX', 'Performance Mouse MX', 'mouse'),
		)
DEVICES = { d.codename: d for d in DEVICES }
