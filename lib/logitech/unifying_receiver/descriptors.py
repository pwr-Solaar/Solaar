#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple

from .common import NamedInts as _NamedInts
from . import hidpp10

#
#
#

_DeviceDescriptor = namedtuple('_DeviceDescriptor',
				['name', 'kind', 'codename', 'registers', 'settings'])

DEVICES = {}

def _D(name, codename=None, kind=None, registers=None, settings=None):
	if kind is None:
		kind = (hidpp10.DEVICE_KIND.mouse if 'Mouse' in name
				else hidpp10.DEVICE_KIND.keyboard if 'Keyboard' in name
				else hidpp10.DEVICE_KIND.touchpad if 'Touchpad' in name
				else hidpp10.DEVICE_KIND.trackball if 'Trackball' in name
				else None)
	assert kind is not None

	if codename is None:
		codename = name.split(' ')[-1]
	assert codename is not None

	DEVICES[codename] = _DeviceDescriptor(name, kind, codename, registers, settings)


_D('Wireless Mouse M315')
_D('Wireless Mouse M325')
_D('Wireless Mouse M505')
_D('Wireless Mouse M510')
_D('Couch Mouse M515')
_D('Wireless Mouse M525')
_D('Wireless Trackball M570')
_D('Touch Mouse M600')
_D('Marathon Mouse M705',
				settings=[hidpp10.SmoothScroll_Setting(0x01)],
				)
_D('Wireless Keyboard K230')
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
_D('Performance Mouse MX', codename='Performance MX',
				settings=[
						hidpp10.MouseDPI_Setting(0x63, _NamedInts(**{str(x * 100): (0x80 + x) for x in range(1, 16)})),
						],
				)

del namedtuple
