#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
_log = getLogger(__name__)
del getLogger

from gi.repository import Gtk, Gdk
from gi.repository.GObject import TYPE_PYOBJECT

from solaar import NAME
# from solaar import __version__ as VERSION
from logitech.unifying_receiver import hidpp10 as _hidpp10
from logitech.unifying_receiver.common import NamedInts as _NamedInts
from logitech.unifying_receiver.status import KEYS as _K
from . import config_panel as _config_panel
from . import action as _action, icons as _icons
from .about import show_window as _show_about_window


#
# constants
#

_SMALL_BUTTON_ICON_SIZE = Gtk.IconSize.MENU
_NORMAL_BUTTON_ICON_SIZE = Gtk.IconSize.BUTTON
_TREE_ICON_SIZE = Gtk.IconSize.BUTTON
_INFO_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_DEVICE_ICON_SIZE = Gtk.IconSize.DND

# tree model columns
_COLUMN = _NamedInts(ID=0, ACTIVE=1, NAME=2, ICON=3, STATUS_ICON=4, DEVICE=5)
_COLUMN_TYPES = (str, bool, str, str, str, TYPE_PYOBJECT)
_TREE_SEPATATOR = (None, False, None, None, None, None)

_TOOLTIP_LINK_SECURE = 'The wireless link between this device and its receiver is not encrypted.'
_TOOLTIP_LINK_INSECURE = ('The wireless link between this device and its receiver is not encrypted.\n'
						'\n'
						'For pointing devices (mice, trackballs, trackpads), this is a minor security issue.\n'
						'\n'
						'It is, however, a major security issue for text-input devices (keyboards, numpads),\n'
						'because typed text can be sniffed inconspicuously by 3rd parties within range.')

_UNIFYING_RECEIVER_TEXT = (
		'No paired devices.\n\n<small>Up to %d devices can be paired to this receiver.</small>',
		'%d paired device(s).\n\n<small>Up to %d devices can be paired to this receiver.</small>',
	)
_NANO_RECEIVER_TEXT = (
	'No paired device.\n\n<small> </small>',
	' \n\n<small>Only one device can be paired to this receiver.</small>',
	)

#
# create UI layout
#

Gtk.Window.set_default_icon_name(NAME.lower())
Gtk.Window.set_default_icon_from_file(_icons.icon_file(NAME.lower(), 32))

def _new_button(label, icon_name=None, icon_size=_NORMAL_BUTTON_ICON_SIZE, tooltip=None, toggle=False, clicked=None):
	if toggle:
		b = Gtk.ToggleButton()
	else:
		b = Gtk.Button(label) if label else Gtk.Button()

	if icon_name:
		image = Gtk.Image.new_from_icon_name(icon_name, icon_size)
		b.set_image(image)

	if tooltip:
		b.set_tooltip_text(tooltip)

	if not label and icon_size < _NORMAL_BUTTON_ICON_SIZE:
		b.set_relief(Gtk.ReliefStyle.NONE)
		b.set_focus_on_click(False)

	if clicked is not None:
		b.connect('clicked', clicked)

	return b


def _create_receiver_panel():
	p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

	p._count = Gtk.Label()
	p._count.set_padding(32, 0)
	p._count.set_alignment(0, 0.5)
	p.pack_start(p._count, True, True, 0)

	p._scanning = Gtk.Label('Scanning...')
	p._spinner = Gtk.Spinner()

	bp = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
	bp.pack_start(Gtk.Label(' '), True, True, 0)
	bp.pack_start(p._scanning, False, False, 0)
	bp.pack_end(p._spinner, False, False, 0)
	p.pack_end(bp, False, False, 0)

	return p


def _create_device_panel():
	p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

	def _status_line(label_text):
		b = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
		b.set_size_request(10, 28)

		b._label = Gtk.Label(label_text)
		b._label.set_alignment(0, 0.5)
		b._label.set_size_request(170, 10)
		b.pack_start(b._label, False, False, 0)

		b._icon = Gtk.Image()
		b.pack_start(b._icon, False, False, 0)

		b._text = Gtk.Label()
		b._text.set_alignment(0, 0.5)
		b.pack_start(b._text, True, True, 0)

		return b

	p._battery = _status_line('Battery')
	p.pack_start(p._battery, False, False, 0)

	p._secure = _status_line('Wireless Link')
	p._secure._icon.set_from_icon_name('dialog-warning', _INFO_ICON_SIZE)
	p.pack_start(p._secure, False, False, 0)

	p._lux = _status_line('Lighting')
	p.pack_start(p._lux, False, False, 0)

	p._config = _config_panel.create()
	p.pack_end(p._config, False, False, 8)

	return p


def _create_details_panel():
	p = Gtk.Frame()
	p.set_shadow_type(Gtk.ShadowType.NONE)
	p.set_size_request(240, 0)
	p.set_state_flags(Gtk.StateFlags.ACTIVE, True)

	p._text = Gtk.Label()
	p._text.set_padding(6, 4)
	p._text.set_alignment(0, 0)
	p._text.set_selectable(True)
	p.add(p._text)

	return p


def _create_buttons_box():
	bb = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
	bb.set_layout(Gtk.ButtonBoxStyle.END)

	bb._details = _new_button(None, 'dialog-information', _SMALL_BUTTON_ICON_SIZE,
					tooltip='Show Technical Details', toggle=True, clicked=_update_details)
	bb.add(bb._details)
	bb.set_child_secondary(bb._details, True)
	bb.set_child_non_homogeneous(bb._details, True)

	def _pair_new_device(trigger):
		assert _find_selected_device_id() is not None
		receiver = _find_selected_device()
		assert receiver is not None
		assert receiver.kind is None
		_action.pair(_window, receiver)

	bb._pair = _new_button('Pair new device', 'list-add', clicked=_pair_new_device)
	bb.add(bb._pair)

	def _unpair_current_device(trigger):
		assert _find_selected_device_id() is not None
		device = _find_selected_device()
		assert device is not None
		assert device.kind is not None
		_action.unpair(_window, device)

	bb._unpair = _new_button('Unpair', 'edit-delete', clicked=_unpair_current_device)
	bb.add(bb._unpair)

	return bb


def _create_empty_panel():
	p = Gtk.Label()
	p.set_markup('<small>Select a device</small>')
	p.set_sensitive(False)

	return p


def _create_info_panel():
	p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

	p._title = Gtk.Label(' ')
	p._title.set_alignment(0, 0.5)
	p._icon = Gtk.Image()

	b1 = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
	b1.pack_start(p._title, True, True, 0)
	b1.pack_start(p._icon, False, False, 0)
	p.pack_start(b1, False, False, 0)

	p.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 0)  # spacer

	p._receiver = _create_receiver_panel()
	p.pack_start(p._receiver, True, True, 0)

	p._device = _create_device_panel()
	p.pack_start(p._device, True, True, 0)

	p.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 0)  # spacer

	p._buttons = _create_buttons_box()
	p.pack_end(p._buttons, False, False, 0)

	return p


def _create_tree(model):
	tree = Gtk.TreeView()
	tree.set_size_request(240, 0)
	tree.set_headers_visible(False)
	tree.set_show_expanders(False)
	tree.set_level_indentation(16)
	tree.set_enable_tree_lines(True)
	# tree.set_rules_hint(True)
	tree.set_model(model)

	def _is_separator(model, item, _=None):
		return model.get_value(item, _COLUMN.ID) is None
	tree.set_row_separator_func(_is_separator, None)

	icon_cell_renderer = Gtk.CellRendererPixbuf()
	icon_cell_renderer.set_property('stock-size', _TREE_ICON_SIZE)
	icon_column = Gtk.TreeViewColumn('Icon', icon_cell_renderer)
	icon_column.add_attribute(icon_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
	icon_column.add_attribute(icon_cell_renderer, 'icon-name', _COLUMN.ICON)
	icon_column.set_fixed_width(1)
	tree.append_column(icon_column)

	name_cell_renderer = Gtk.CellRendererText()
	name_column = Gtk.TreeViewColumn('Name', name_cell_renderer)
	name_column.add_attribute(name_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
	name_column.add_attribute(name_cell_renderer, 'text', _COLUMN.NAME)
	name_column.set_expand(True)
	tree.append_column(name_column)
	tree.set_expander_column(name_column)

	battery_cell_renderer = Gtk.CellRendererPixbuf()
	battery_cell_renderer.set_property('stock-size', _TREE_ICON_SIZE)
	battery_column = Gtk.TreeViewColumn('Status', battery_cell_renderer)
	battery_column.add_attribute(battery_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
	battery_column.add_attribute(battery_cell_renderer, 'icon-name', _COLUMN.STATUS_ICON)
	battery_column.set_fixed_width(1)
	tree.append_column(battery_column)

	return tree


def _create_window_layout():
	assert _tree is not None
	assert _details is not None
	assert _info is not None
	assert _empty is not None

	assert _tree.get_selection().get_mode() == Gtk.SelectionMode.SINGLE
	_tree.get_selection().connect('changed', _device_selected)

	tree_panel = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
	tree_panel.set_homogeneous(False)
	tree_panel.pack_start(_tree, True, True, 0)
	tree_panel.pack_start(_details, False, False, 0)

	panel = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 16)
	panel.pack_start(tree_panel, False, False, 0)
	panel.pack_start(_info, True, True, 0)
	panel.pack_start(_empty, True, True, 0)

	about_button = _new_button('About ' + NAME, 'help-about',
					icon_size=_SMALL_BUTTON_ICON_SIZE, clicked=_show_about_window)

	bottom_buttons_box = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
	bottom_buttons_box.set_layout(Gtk.ButtonBoxStyle.START)
	bottom_buttons_box.add(about_button)

	# solaar_version = Gtk.Label()
	# solaar_version.set_markup('<small>' + NAME + ' v' + VERSION + '</small>')
	# bottom_buttons_box.add(solaar_version)
	# bottom_buttons_box.set_child_secondary(solaar_version, True)

	vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 8)
	vbox.set_border_width(8)
	vbox.pack_start(panel, True, True, 0)
	vbox.pack_end(bottom_buttons_box, False, False, 0)
	vbox.show_all()

	_details.set_visible(False)
	_info.set_visible(False)
	return vbox


def _create():
	window = Gtk.Window()
	window.set_title(NAME)
	window.set_role('status-window')

	# window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
	# window.set_skip_taskbar_hint(True)
	# window.set_skip_pager_hint(True)
	window.set_keep_above(True)
	window.connect('delete-event', _hide)

	vbox = _create_window_layout()
	window.add(vbox)

	geometry = Gdk.Geometry()
	geometry.min_width = 600
	geometry.min_height = 320
	geometry.max_width = 800
	geometry.max_height = 600
	window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE)
	window.set_position(Gtk.WindowPosition.CENTER)

	return window

#
# window updates
#

def _find_selected_device():
	selection = _tree.get_selection()
	model, item = selection.get_selected()
	return model.get_value(item, _COLUMN.DEVICE) if item else None


def _find_selected_device_id():
	selection = _tree.get_selection()
	model, item = selection.get_selected()
	return model.get_value(item, _COLUMN.ID) if item else None


# triggered by changing selection in the tree
def _device_selected(selection):
	model, item = selection.get_selected()
	device = model.get_value(item, _COLUMN.DEVICE) if item else None
	_update_info_panel(device, full=True)


def _receiver_row(receiver_path, receiver=None):
	item = _model.get_iter_first()
	while item:
		if _model.get_value(item, _COLUMN.ID) == receiver_path:
			return item
		item = _model.iter_next(item)

	if not item and receiver is not None:
		row_data = (receiver_path, True, receiver.name, _icons.device_icon_name(receiver.name), '', receiver)
		item = _model.append(None, row_data)
		_model.append(None, _TREE_SEPATATOR)

	return item or None


def _device_row(receiver_path, device_serial, device=None):
	receiver_row = _receiver_row(receiver_path, None if device is None else device.receiver)
	item = _model.iter_children(receiver_row)
	while item:
		if _model.get_value(item, _COLUMN.ID) == device_serial:
			return item
		item = _model.iter_next(item)

	if not item and device is not None:
		# print ("new device row", device)
		row_data = (device_serial, bool(device.status), device.codename, _icons.device_icon_name(device.name, device.kind), '', device)
		item = _model.append(receiver_row, row_data)

	return item or None

#
#
#

def select(receiver_path, device_id=None):
	assert _window
	assert receiver_path is not None
	if device_id is None:
		item = _receiver_row(receiver_path)
	else:
		item = _device_row(receiver_path, device_id)
	if item:
		selection = _tree.get_selection()
		selection.select_iter(item)


def _hide(w, _=None):
	assert w == _window
	# some window managers move the window to 0,0 after hide()
	# so try to remember the last position
	position = _window.get_position()
	_window.hide()
	_window.move(*position)
	return True


def popup(trigger=None, receiver_path=None, device_id=None):
	if receiver_path:
		select(receiver_path, device_id)
	_window.present()
	return True


def toggle(trigger=None):
	if _window.get_visible():
		_hide(_window)
	else:
		_window.present()

#
#
#

def _update_details(button):
	assert button
	visible = button.get_active()
	device = _find_selected_device()

	if visible:
		_details._text.set_markup('<small>reading...</small>')

		def _details_items(device):
			if device.kind is None:
				yield ('Path', device.path)
				yield ('USB id', '046d:' + device.product_id)
			else:
				# yield ('Codename', device.codename)
				hid = device.protocol
				yield ('Protocol', 'HID++ %1.1f' % hid if hid else 'unknown')
				if device.polling_rate:
					yield ('Polling rate', '%d ms' % device.polling_rate)
				yield ('Wireless PID', device.wpid)

			yield ('Serial', device.serial)

			for fw in list(device.firmware):
				yield (fw.kind, (fw.name + ' ' + fw.version).strip())

			flag_bits = device.status.get(_K.NOTIFICATION_FLAGS)
			if flag_bits is not None:
				flag_names = ('(none)',) if flag_bits == 0 else _hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits)
				yield ('Notifications', ('\n%15s' % ' ').join(flag_names))

		items = _details_items(device)
		text = '\n'.join('%-13s: %s' % i for i in items if i)
		_details._text.set_markup('<small><tt>' + text + '</tt></small>')

	_details.set_visible(visible)


def _update_receiver_panel(receiver, panel, buttons, full=False):
	devices_count = len(receiver)
	if receiver.max_devices > 1:
		if devices_count == 0:
			panel._count.set_markup(_UNIFYING_RECEIVER_TEXT[0] % receiver.max_devices)
		else:
			panel._count.set_markup(_UNIFYING_RECEIVER_TEXT[1] % (devices_count, receiver.max_devices))
	else:
		if devices_count == 0:
			panel._count.set_markup(_NANO_RECEIVER_TEXT[0])
		else:
			panel._count.set_markup(_NANO_RECEIVER_TEXT[1])

	is_pairing = receiver and receiver.status.lock_open
	if is_pairing:
		panel._scanning.set_visible(True)
		if not panel._spinner.get_visible():
			panel._spinner.start()
		panel._spinner.set_visible(True)
	else:
		panel._scanning.set_visible(False)
		if panel._spinner.get_visible():
			panel._spinner.stop()
		panel._spinner.set_visible(False)

	panel.set_visible(True)

	# b._insecure.set_visible(False)
	buttons._unpair.set_visible(False)
	buttons._pair.set_sensitive(devices_count < receiver.max_devices and not is_pairing)
	buttons._pair.set_visible(True)


def _update_device_panel(device, panel, buttons, full=False):
	is_active = bool(device.status)
	panel.set_sensitive(is_active)

	battery_level = device.status.get(_K.BATTERY_LEVEL)
	if battery_level is None:
		icon_name = _icons.battery()
		panel._battery._icon.set_sensitive(False)
		panel._battery._icon.set_from_icon_name(icon_name, _INFO_ICON_SIZE)
		panel._battery._text.set_sensitive(True)
		panel._battery._text.set_markup('<small>unknown</small>')
	else:
		charging = device.status.get(_K.BATTERY_CHARGING)
		icon_name = _icons.battery(battery_level, charging)
		panel._battery._icon.set_from_icon_name(icon_name, _INFO_ICON_SIZE)
		panel._battery._icon.set_sensitive(True)

		text = '%d%%' % battery_level
		if is_active:
			if charging:
				text += ' <small>(charging)</small>'
		else:
			text += ' <small>(last known)</small>'
		panel._battery._text.set_sensitive(is_active)
		panel._battery._text.set_markup(text)

	if is_active:
		not_secure = device.status.get(_K.LINK_ENCRYPTED) == False
		if not_secure:
			panel._secure._text.set_text('not encrypted')
			panel._secure._icon.set_from_icon_name('security-low', _INFO_ICON_SIZE)
			panel._secure.set_tooltip_text(_TOOLTIP_LINK_INSECURE)
		else:
			panel._secure._text.set_text('encrypted')
			panel._secure._icon.set_from_icon_name('security-high', _INFO_ICON_SIZE)
			panel._secure.set_tooltip_text(_TOOLTIP_LINK_SECURE)
		panel._secure._icon.set_visible(True)
	else:
		panel._secure._text.set_markup('<small>offline</small>')
		panel._secure._icon.set_visible(False)
		panel._secure.set_tooltip_text('')

	if is_active:
		light_level = device.status.get(_K.LIGHT_LEVEL)
		if light_level is None:
			panel._lux.set_visible(False)
		else:
			panel._lux._icon.set_from_icon_name(_icons.lux(light_level), _INFO_ICON_SIZE)
			panel._lux._text.set_text('%d lux' % light_level)
			panel._lux.set_visible(True)
	else:
		panel._lux.set_visible(False)

	buttons._pair.set_visible(False)
	buttons._unpair.set_visible(True)

	panel.set_visible(True)

	if full:
		_config_panel.update(panel._config, device, is_active)


def _update_info_panel(device, full=False):
	if device is None:
		_details.set_visible(False)
		_info.set_visible(False)
		_empty.set_visible(True)
		return

	is_active = bool(device.status)

	_info._title.set_markup('<b>%s</b>' % device.name)
	_info._title.set_sensitive(is_active)
	icon_name = _icons.device_icon_name(device.name, device.kind)
	_info._icon.set_from_icon_name(icon_name, _DEVICE_ICON_SIZE)
	_info._icon.set_sensitive(is_active)

	if device.kind is None:
		_info._device.set_visible(False)
		_update_receiver_panel(device, _info._receiver, _info._buttons, full)
	else:
		_info._receiver.set_visible(False)
		_update_device_panel(device, _info._device, _info._buttons, full)

	_empty.set_visible(False)
	_info.set_visible(True)

	if full:
		_update_details(_info._buttons._details)

#
# window layout:
#  +--------------------------------+
#  |  tree      | receiver  | empty |
#  |            | or device |       |
#  |------------| status    |       |
#  | details    |           |       |
#  |--------------------------------|
#  | (about)                        |
#  +--------------------------------|
# either the status or empty panel is visible at any point
# the details panel can be toggle on/off

_model = None
_tree = None
_details = None
_info = None
_empty = None
_window = None


def init():
	global _model, _tree, _details, _info, _empty, _window
	_model = Gtk.TreeStore(*_COLUMN_TYPES)
	_tree = _create_tree(_model)
	_details = _create_details_panel()
	_info = _create_info_panel()
	_empty = _create_empty_panel()
	_window = _create()


def destroy():
	global _model, _tree, _details, _info, _empty, _window
	w, _window = _window, None
	w.destroy()
	w = None

	_empty = None
	_info = None
	_details = None
	_tree = None
	_model = None


def update(device, need_popup=False):
	if _window is None:
		return

	assert device is not None

	if need_popup:
		popup()

	selected_device_id = _find_selected_device_id()

	if device.kind is None:
		# receiver
		is_alive = bool(device)
		item = _receiver_row(device.path, device if is_alive else None)
		assert item
		if is_alive and item:
			_model.set_value(item, _COLUMN.ACTIVE, True)
			is_pairing = is_alive and device.status.lock_open
			_model.set_value(item, _COLUMN.STATUS_ICON, 'network-wireless' if is_pairing else '')

			if selected_device_id == device.path:
				_update_info_panel(device, need_popup)

		elif item:
			separator = _model.iter_next(item)
			_model.remove(separator)
			_model.remove(item)
			# _config_panel.clean(device.path)

	else:
		# peripheral
		is_alive = device.status is not None
		item = _device_row(device.receiver.path, device.serial, device if is_alive else None)
		if is_alive and item:
			_model.set_value(item, _COLUMN.ACTIVE, bool(device.status))
			battery_level = device.status.get(_K.BATTERY_LEVEL)
			if battery_level is None:
				_model.set_value(item, _COLUMN.STATUS_ICON, '')
			else:
				charging = device.status.get(_K.BATTERY_CHARGING)
				icon_name = _icons.battery(battery_level, charging)
				_model.set_value(item, _COLUMN.STATUS_ICON, icon_name)

			if selected_device_id is None:
				select(device.receiver.path, device.serial)
			elif selected_device_id == device.serial:
				_update_info_panel(device, need_popup)

		elif item:
			_model.remove(item)
			_config_panel.clean(device.serial)

	# make sure all rows are visible
	_tree.expand_all()
