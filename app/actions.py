#
#
#

import logging

from logitech.unifying_receiver import api
from logitech import devices

from . import ui
import ui.pair


def full_scan(button, watcher):
	if watcher.active and watcher.listener:
		updated = False

		for devnumber in range(1, 1 + api.C.MAX_ATTACHED_DEVICES):
			devstatus = watcher.devices.get(devnumber)
			if devstatus:
				status = devices.request_status(devstatus, watcher.listener)
				updated |= watcher._device_status_changed(devstatus, status)
			else:
				devstatus = watcher._new_device(devnumber)
				updated |= devstatus is not None

		if updated:
			watcher._update_status_text()

		return updated


def pair(button, watcher):
	if watcher.active and watcher.listener:
		logging.debug("pair")

		parent = button.get_toplevel()
		title = parent.get_title() + ': ' + button.get_tooltip_text()
		w = ui.pair.create(parent, title)
		w.run()
		w.destroy()
