#
#
#

import logging
from gi.repository import (Gtk, GObject)

import ui
from logitech.unifying_receiver import status as _status

_PAIRING_TIMEOUT = 15


def _create_page(assistant, kind, header=None, icon_name=None, text=None):
	p = Gtk.VBox(False, 8)
	assistant.append_page(p)
	assistant.set_page_type(p, kind)

	if header:
		item = Gtk.HBox(False, 16)
		p.pack_start(item, False, True, 0)

		label = Gtk.Label(header)
		label.set_alignment(0, 0)
		label.set_line_wrap(True)
		item.pack_start(label, True, True, 0)

		if icon_name:
			icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
			icon.set_alignment(1, 0)
			item.pack_start(icon, False, False, 0)

	if text:
		label = Gtk.Label(text)
		label.set_alignment(0, 0)
		label.set_line_wrap(True)
		p.pack_start(label, False, False, 0)

	p.show_all()
	return p


# def _fake_device(receiver):
# 	from logitech.unifying_receiver import PairedDevice
# 	dev = PairedDevice(receiver, 6)
# 	dev._kind = 'touchpad'
# 	dev._codename = 'T650'
# 	dev._name = 'Wireless Rechargeable Touchpad T650'
# 	dev._serial = '0123456789'
# 	dev._protocol = 2.0
# 	dev.status = _status.DeviceStatus(dev, lambda *foo: None)
# 	return dev

def _check_lock_state(assistant, receiver):
	if not assistant.is_drawable():
		return False

	if receiver.status.get(_status.ERROR):
		# fake = _fake_device(receiver)
		# receiver._devices[fake.number] = fake
		# receiver.status.new_device = fake
		# fake.status._changed()
		_pairing_failed(assistant, receiver, receiver.status.pop(_status.ERROR))
		return False

	if receiver.status.new_device:
		_pairing_succeeded(assistant, receiver)
		return False

	return receiver.status.lock_open


def _prepare(assistant, page, receiver):
	index = assistant.get_current_page()
	# logging.debug("prepare %s %d %s", assistant, index, page)

	if index == 0:
		if receiver.set_lock(False, timeout=_PAIRING_TIMEOUT):
			assert receiver.status.new_device is None
			assert receiver.status.get(_status.ERROR) is None
			spinner = page.get_children()[-1]
			spinner.start()
			GObject.timeout_add(300, _check_lock_state, assistant, receiver)
			assistant.set_page_complete(page, True)
		else:
			GObject.idle_add(_pairing_failed, assistant, receiver, 'the pairing lock did not open')
	else:
		assistant.remove_page(0)


def _finish(assistant, receiver):
	logging.debug("finish %s", assistant)
	assistant.destroy()
	receiver.status.new_device = None
	if receiver.status.lock_open:
		receiver.set_lock()


def _cancel(assistant, receiver):
	logging.debug("cancel %s", assistant)
	assistant.destroy()
	device, receiver.status.new_device = receiver.status.new_device, None
	if device:
		try:
			del receiver[device.number]
		except:
			logging.error("failed to unpair %s", device)
	if receiver.status.lock_open:
		receiver.set_lock()


def _pairing_failed(assistant, receiver, error):
	assistant.commit()

	header = 'Pairing failed: %s.' % error
	if 'timeout' in str(error):
		text = 'Make sure your device is within range,\nand it has a decent battery charge.'
	else:
		text = None
	_create_page(assistant, Gtk.AssistantPageType.SUMMARY, header, 'dialog-error', text)

	assistant.next_page()
	assistant.commit()


def _pairing_succeeded(assistant, receiver):
	device = receiver.status.new_device
	assert device
	page = _create_page(assistant, Gtk.AssistantPageType.CONFIRM)

	device_icon = Gtk.Image()
	device_icon.set_from_icon_name(ui.get_icon(device.name, device.kind), Gtk.IconSize.DIALOG)
	device_icon.set_pixel_size(128)
	device_icon.set_alignment(0.5, 1)
	page.pack_start(device_icon, False, False, 0)

	device_label = Gtk.Label()
	device_label.set_markup('<b>' + device.name + '</b>')
	device_label.set_alignment(0.5, 0)
	page.pack_start(device_label, False, False, 0)

	if device.status.get('encrypted') == False:
		hbox = Gtk.HBox(False, 8)
		hbox.pack_start(Gtk.Image.new_from_icon_name('dialog-warning', Gtk.IconSize.MENU), False, False, 0)
		hbox.pack_start(Gtk.Label('The wireless link is not encrypted!'), False, False, 0)
		halign = Gtk.Alignment.new(0.5, 0, 0, 0)
		halign.add(hbox)
		page.pack_start(halign, False, False, 0)

	# hbox = Gtk.HBox(False, 8)
	# hbox.pack_start(Gtk.Entry(), False, False, 0)
	# hbox.pack_start(Gtk.ToggleButton('  Test  '), False, False, 0)
	# halign = Gtk.Alignment.new(0.5, 1, 0, 0)
	# halign.add(hbox)
	# page.pack_start(halign, True, True, 0)

	# entry_info = Gtk.Label()
	# entry_info.set_markup('<small>Use the controls above to confirm\n'
	# 						'this is the device you want to pair.</small>')
	# entry_info.set_sensitive(False)
	# entry_info.set_alignment(0.5, 0)
	# page.pack_start(entry_info, True, True, 0)

	page.show_all()

	assistant.next_page()
	assistant.set_page_complete(page, True)


def create(action, receiver):
	assistant = Gtk.Assistant()
	assistant.set_title(action.get_label())
	assistant.set_icon_name(action.get_icon_name())

	assistant.set_size_request(420, 260)
	assistant.set_resizable(False)
	assistant.set_role('pair-device')

	page_intro = _create_page(assistant, Gtk.AssistantPageType.PROGRESS,
					'Turn on the device you want to pair.', 'preferences-desktop-peripherals',
					'If the device is already turned on,\nturn if off and on again.')
	spinner = Gtk.Spinner()
	spinner.set_visible(True)
	page_intro.pack_end(spinner, True, True, 24)

	assistant.connect('prepare', _prepare, receiver)
	assistant.connect('cancel', _cancel, receiver)
	assistant.connect('close', _finish, receiver)

	return assistant
