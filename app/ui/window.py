#
#
#

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from .. import constants as C


_DEVICE_ICON_SIZE = 48
_STATUS_ICON_SIZE = 64
_PLACEHOLDER = '~'
_images = None
_MAX_DEVICES = 7

_ICONS = {}


def _icon(icon, title, size=_DEVICE_ICON_SIZE, fallback=None):
	icon = icon or Gtk.Image()

	if title and title in _ICONS:
		icon.set_from_pixbuf(_ICONS[title])
	else:
		icon_file = _images(title) if title else None
		if icon_file:
			pixbuf = GdkPixbuf.Pixbuf().new_from_file(icon_file)
			if pixbuf.get_width() > size or pixbuf.get_height() > size:
				if pixbuf.get_width() > pixbuf.get_height():
					new_width = size
					new_height = size * pixbuf.get_height() / pixbuf.get_width()
				else:
					new_width = size * pixbuf.get_width() / pixbuf.get_height()
					new_height = size
				pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.HYPER)
			icon.set_from_pixbuf(pixbuf)
			_ICONS[title] = pixbuf
		elif fallback:
			icon.set_from_icon_name(fallback, size if size < _DEVICE_ICON_SIZE else Gtk.IconSize.DIALOG)

	if size >= _DEVICE_ICON_SIZE:
		icon.set_size_request(size, size)
	return icon


def update(window, ur_available, devices):
	if not window or not window.get_child():
		return
	controls = list(window.get_child().get_children())

	first = controls[0]
	first.set_visible(not ur_available or not devices)
	if ur_available:
		ur_status = C.FOUND_RECEIVER if devices else C.NO_DEVICES
	else:
		ur_status = C.NO_RECEIVER
	_, label = first.get_children()
	label.set_markup('<big><b>%s</b></big>\n%s' % (C.UNIFYING_RECEIVER, ur_status))

	for index in range(1, _MAX_DEVICES):
		box = controls[index]
		devstatus = [d for d in devices if d.number == index]
		devstatus = devstatus[0] if devstatus else None
		box.set_visible(devstatus is not None)

		if devstatus:
			box.set_sensitive(devstatus.code >= 0)
			icon, expander = box.get_children()
			if not expander.get_data('devstatus'):
				expander.set_data('devstatus', devstatus,)
				_icon(icon, 'devices/' + devstatus.name, fallback=devstatus.type.lower())

			label = expander.get_label_widget()
			if expander.get_expanded():
				label.set_markup('<big><b>%s</b></big>' % devstatus.name)
			else:
				label.set_markup('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.props['text']))

			ebox = expander.get_child()

			# refresh_button = ebox.get_children()[0]
			# refresh_button.connect('activate', devstatus.refresh)

			texts = []

			battery_icon = ebox.get_children()[-1]
			if 'battery-level' in devstatus.props:
				level = devstatus.props['battery-level']
				icon_name = 'battery/' + str((level + 10) // 20)
				_icon(battery_icon, icon_name, _STATUS_ICON_SIZE)
				texts.append('Battery: ' + str(level) + '%')
			else:
				_icon(battery_icon, 'battery/unknown', _STATUS_ICON_SIZE)
				texts.append('Battery: unknown')
			battery_icon.set_tooltip_text(texts[-1])

			light_icon = ebox.get_children()[-2]
			if 'light-level' in devstatus.props:
				lux = devstatus.props['light-level']
				icon_name = 'light/' + str((lux + 50) // 100)
				_icon(light_icon, icon_name, _STATUS_ICON_SIZE)

				texts.append('Light: ' + str(lux) + ' lux')
				light_icon.set_tooltip_text(texts[-1])
				light_icon.set_visible(True)
			else:
				light_icon.set_visible(False)

			label = ebox.get_children()[-3]
			label.set_text('\n'.join(texts))

def _expander_activate(expander):
	devstatus = expander.get_data('devstatus')
	if devstatus:
		label = expander.get_label_widget()
		if expander.get_expanded():
			label.set_markup('<big><b>%s</b></big>\n%s' % (devstatus.name, devstatus.props['text']))
		else:
			label.set_markup('<big><b>%s</b></big>' % devstatus.name)


def _device_box(title):
	icon = _icon(None, 'devices/' + title)
	icon.set_alignment(0.5, 0)

	label = Gtk.Label()
	label.set_markup('<big><b>%s</b></big>' % title)
	label.set_alignment(0, 0.5)
	label.set_can_focus(False)

	box = Gtk.HBox(spacing=10)
	box.pack_start(icon, False, False, 0)

	if title == C.UNIFYING_RECEIVER:
		box.add(label)
	else:
		expander = Gtk.Expander()
		expander.set_can_focus(False)
		expander.set_label_widget(label)
		expander.connect('activate', _expander_activate)

		ebox = Gtk.HBox(False, 10)
		ebox.set_border_width(4)

		# refresh_button = Gtk.Button()
		# refresh_button.set_image(_icon(None, None, size=Gtk.IconSize.SMALL_TOOLBAR, fallback='reload'))
		# refresh_button.set_focus_on_click(False)
		# refresh_button.set_can_focus(False)
		# refresh_button.set_image_position(Gtk.PositionType.TOP)
		# refresh_button.set_alignment(0.5, 0.5)
		# refresh_button.set_relief(Gtk.ReliefStyle.NONE)
		# refresh_button.set_size_request(20, 20)
		# refresh_button.set_tooltip_text('Refresh')
		# ebox.pack_start(refresh_button, False, False, 2)

		label = Gtk.Label()
		label.set_alignment(0, 0.5)
		ebox.pack_start(label, False, True, 8)

		light_icon = _icon(None, 'light/unknown', _STATUS_ICON_SIZE)
		ebox.pack_end(light_icon, False, True, 0)

		battery_icon = _icon(None, 'battery/unknown', _STATUS_ICON_SIZE)
		ebox.pack_end(battery_icon, False, True, 0)

		expander.add(ebox)
		box.pack_start(expander, True, True, 1)

	box.show_all()
	box.set_visible(title != _PLACEHOLDER)
	return box


def create(title, images=None):
	global _images
	_images = images or (lambda x: None)

	vbox = Gtk.VBox(spacing=8)
	vbox.set_border_width(6)

	vbox.add(_device_box(C.UNIFYING_RECEIVER))
	for i in range(1, _MAX_DEVICES):
		vbox.add(_device_box(_PLACEHOLDER))
	vbox.set_visible(True)

	window = Gtk.Window()  # Gtk.WindowType.POPUP)
	window.set_title(title)
	window.set_icon_from_file(_images('icon'))
	window.set_keep_above(True)
	window.set_decorated(False)
	window.set_skip_taskbar_hint(True)
	window.set_skip_pager_hint(True)
	window.set_deletable(False)
	window.set_resizable(False)
	window.set_position(Gtk.WindowPosition.MOUSE)
	window.set_type_hint(Gdk.WindowTypeHint.TOOLTIP)
	window.connect('focus-out-event', _hide)

	window.add(vbox)
	return window


def _hide(window, _):
	window.set_visible(False)


def toggle(_, window):
	if window.get_visible():
		window.set_visible(False)
	else:
		window.present()
