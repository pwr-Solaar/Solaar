#
#
#

# import logging

# try:
# 	from gi.repository import Indicate
# 	from time import time as _timestamp

# 	# import ui

# 	# necessary because the notifications daemon does not know about our XDG_DATA_DIRS
# 	_icons = {}

# 	# def _icon(title):
# 	# 	if title not in _icons:
# 	# 		_icons[title] = ui.icon_file(title)

# 	# 	return _icons.get(title)

# 	def init(app_title):
# 		global available

# 		try:
# 			s = Indicate.Server()
# 			s.set_type('message.im')
# 			s.set_default()
# 			print s
# 			s.show()
# 			s.connect('server-display', server_display)

# 			i = Indicate.Indicator()
# 			i.set_property('sender', 'test message sender')
# 			i.set_property('body', 'test message body')
# 			i.set_property_time('time', _timestamp())
# 			i.set_subtype('im')
# 			print i, i.list_properties()
# 			i.show()
# 			i.connect('user-display', display)

# 			pass
# 		except:
# 			available = False

# 	init('foo')

# 	# assumed to be working since the import succeeded
# 	available = True

# 	def server_display(s):
# 		print 'server display', s

# 	def display(i):
# 		print "indicator display", i
# 		i.hide()

# except ImportError:
# 	available = False
# 	init = lambda app_title: False
# 	uninit = lambda: None
# 	show = lambda dev: None
