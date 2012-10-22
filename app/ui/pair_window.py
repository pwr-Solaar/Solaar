#
#
#

import logging
from gi.repository import (Gtk, GObject)

import ui


def _create_page(assistant, text, kind):
	p = Gtk.VBox(False, 12)
	p.set_border_width(8)

	if text:
		label = Gtk.Label(text)
		label.set_alignment(0, 0)
		p.pack_start(label, False, True, 0)

	assistant.append_page(p)
	assistant.set_page_type(p, kind)

	p.show_all()
	return p


def _device_confirmed(entry, _2, trigger, assistant, page):
	assistant.commit()
	assistant.set_page_complete(page, True)
	return True


def _finish(assistant, action):
	logging.debug("finish %s", assistant)
	assistant.destroy()
	action.set_sensitive(True)

def _cancel(assistant, action, state):
	logging.debug("cancel %s", assistant)
	state.stop_scan()
	_finish(assistant, action)

def _prepare(assistant, page, state):
	index = assistant.get_current_page()
	logging.debug("prepare %s %d %s", assistant, index, page)

	if index == 0:
		state.reset()
		GObject.timeout_add(state.TICK, state.countdown, assistant)
		spinner = page.get_children()[-1]
		spinner.start()
		return

	assistant.remove_page(0)
	state.stop_scan()


def _scan_complete_ui(assistant, device):
	if device is None:
		page = _create_page(assistant,
							'No new device detected.\n'
							'\n'
							'Make sure your device is within range of the receiver,\nand it has a decent battery charge.\n',
							Gtk.AssistantPageType.CONFIRM)
	else:
		page = _create_page(assistant,
							None,
							Gtk.AssistantPageType.CONFIRM)

		hbox = Gtk.HBox(False, 16)
		device_icon = Gtk.Image()
		device_icon.set_from_icon_name(ui.get_icon(device.name, device.kind), Gtk.IconSize.DIALOG)
		hbox.pack_start(device_icon, False, False, 0)
		device_label = Gtk.Label(device.kind + '\n' + device.name)
		hbox.pack_start(device_label, False, False, 0)
		halign = Gtk.Alignment.new(0.5, 0.5, 0, 1)
		halign.add(hbox)
		page.pack_start(halign, False, True, 0)

		hbox = Gtk.HBox(False, 16)
		hbox.pack_start(Gtk.Entry(), False, False, 0)
		hbox.pack_start(Gtk.ToggleButton('Test'), False, False, 0)
		halign = Gtk.Alignment.new(0.5, 0.5, 0, 1)
		halign.add(hbox)
		page.pack_start(halign, False, False, 0)

		entry_info = Gtk.Label('Use the controls above to confirm\n'
								'this is the device you want to pair.')
		entry_info.set_sensitive(False)
		page.pack_start(entry_info, False, False, 0)

		page.show_all()
		assistant.set_page_complete(page, True)

	assistant.next_page()

def _scan_complete(assistant, device):
	GObject.idle_add(_scan_complete_ui, assistant, device)


def create(action, state):
	assistant = Gtk.Assistant()
	assistant.set_title(action.get_label())
	assistant.set_icon_name(action.get_icon_name())

	assistant.set_size_request(440, 240)
	assistant.set_resizable(False)
	assistant.set_role('pair-device')

	page_intro = _create_page(assistant,
					'Turn on the device you want to pair.\n'
					'\n'
					'If the device is already turned on,\nturn if off and on again.',
					Gtk.AssistantPageType.INTRO)
	spinner = Gtk.Spinner()
	spinner.set_visible(True)
	page_intro.pack_end(spinner, True, True, 16)

	assistant.scan_complete = _scan_complete

	assistant.connect('prepare', _prepare, state)
	assistant.connect('cancel', _cancel, action, state)
	assistant.connect('close', _finish, action)
	assistant.connect('apply', _finish, action)

	return assistant
