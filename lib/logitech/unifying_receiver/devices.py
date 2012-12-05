#
#
#

from collections import namedtuple

_DeviceDescriptor = namedtuple('_DeviceDescriptor',
				['name', 'kind', 'codename', 'settings'])

DEVICES = {}

def _D(name, codename=None, kind=None):
	if kind is None:
		kind = ('mouse' if 'Mouse' in name
				else 'keyboard' if 'Keyboard' in name
				else 'touchpad' if 'Touchpad' in name
				else 'trackball' if 'Trackball' in name
				else None)
	assert kind is not None

	if codename is None:
		codename = name.split(' ')[-1]
	assert codename is not None

	DEVICES[codename] = _DeviceDescriptor(name, kind, codename, None)


_D('Wireless Mouse M315')
_D('Wireless Mouse M325')
_D('Wireless Mouse M505')
_D('Wireless Mouse M510')
_D('Couch Mouse M515')
_D('Wireless Mouse M525')
_D('Wireless Trackball M570')
_D('Touch Mouse M600')
_D('Marathon Mouse M705')
_D('Wireless Keyboard K270')
_D('Wireless Keyboard K350')
_D('Wireless Keyboard K360')
_D('Wireless Touch Keyboard K400')
_D('Wireless Solar Keyboard K750')
_D('Wireless Illuminated Keyboard K800')
_D('Zone Touch Mouse T400')
_D('Wireless Rechargeable Touchpad T650')
_D('Logitech Cube', kind='mouse')
_D('Anywhere Mouse MX', codename='Anywhere MX')
_D('Performance Mouse MX', codename='Performance MX')
			# DPI=(0x64, {0x80: 100,
			# 			0x81: 200,
			# 			0x82: 300,
			# 			0x83: 400,
			# 			0x84: 500,
			# 			0x85: 600,
			# 			0x86: 800,
			# 			0x87: 900,
			# 			0x88: 1000,
			# 			0x89: 1100,
			# 			0x8A: 1200,
			# 			0x8B: 1300,
			# 			0x8C: 1400,
			# 			0x8D: 1500}),
			# Leds=(0x51, {}),

del _D
del _DeviceDescriptor
del namedtuple
