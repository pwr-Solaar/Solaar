# pass

import os.path as _os_path
from . import (icon, notify, window)


_images_path = None
_IMAGES = {}


def init(images_path=None):
	global _images_path
	_images_path = images_path


def image(name):
	if name in _IMAGES:
		return _IMAGES[name]

	if _images_path:
		path = _os_path.join(_images_path, name + '.png')
		if _os_path.isfile(path):
			_IMAGES[name] = path
			return path
		else:
			_IMAGES[name] = None
