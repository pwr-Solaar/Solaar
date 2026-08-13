## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import logging
import math
import time

from dataclasses import dataclass
from enum import Enum

from gi.repository import GLib
from gi.repository import Gtk
from logitech_receiver import hidpp10_constants

from solaar.i18n import _
from solaar.i18n import ngettext

from . import icons

logger = logging.getLogger(__name__)

_PAIRING_TIMEOUT = 30  # seconds
_STATUS_CHECK = 500  # milliseconds
_PROGRESS_GRACE = 3  # seconds to wait for a first progress notification before giving up on them

# steps the user has to perform to enter a passkey
_STEP_LEFT = "left"
_STEP_RIGHT = "right"
_STEP_BOTH = "both"
_STEP_ENTER = "enter"

# widget state kept between the periodic checks, stashed on the widgets themselves
_PASSKEY_PAGE = "_solaar_passkey_page"
_PAIRED_ADDRESS = "_solaar_paired_address"
_ON_RETRY = "_solaar_on_retry"
_COUNTDOWN = "_solaar_countdown"
_STEPS = "_solaar_steps"
_PROGRESS = "_solaar_progress"

# step strip metrics, in pixels
_CELL_WIDTH = 28
_CELL_HEIGHT = 38
_CELL_GAP = 8
_CELL_RADIUS = 9
_NUMBER_GAP = 6
_NUMBER_HEIGHT = 12
_ROW_GAP = 8
_SEPARATOR_GAP = 10
_STRIP_MARGIN = 8
_STEPS_PER_ROW = 5
_FINAL_STEP_SCALE = 1.25
_LABEL_WIDTH_CHARS = 40  # keeps the wrapped labels inside the width of the dialog


class GtkSignal(Enum):
    CANCEL = "cancel"
    CLOSE = "close"
    CLICKED = "clicked"
    DRAW = "draw"


def create(receiver, on_retry=None):
    receiver.reset_pairing()  # clear out any information on previous pairing
    title = _("%(receiver_name)s: pair new device") % {"receiver_name": receiver.name}
    if receiver.receiver_kind == "bolt":
        text = _("Bolt receivers are only compatible with Bolt devices.")
        text += "\n\n"
        text += _("Press a pairing button or key until the pairing light flashes quickly.")
        text += "\n"
        text += _("Press and hold the pairing button on the device for about three seconds.")
    else:
        if receiver.receiver_kind == "unifying":
            text = _("Unifying receivers are only compatible with Unifying devices.")
        else:
            text = _("Other receivers are only compatible with a few devices.")
        text += "\n\n"
        text += _("For most devices, turn on the device you want to pair.")
        text += _("If the device is already turned on, turn it off and on again.")
        text += "\n"
        text += _("The device must not be paired with a nearby powered-on receiver.")
        text += "\n"
        text += _(
            "For devices with multiple channels, "
            "press, hold, and release the button for the channel you wish to pair"
            "\n"
            "or use the channel switch button to select a channel "
            "and then press, hold, and release the channel switch button."
        )
        text += "\n"
        text += _("The channel indicator light should be blinking rapidly.")
    if receiver.remaining_pairings() and receiver.remaining_pairings() >= 0:
        text += (
            ngettext(
                "\n\nThis receiver has %d pairing remaining.",
                "\n\nThis receiver has %d pairings remaining.",
                receiver.remaining_pairings(),
            )
            % receiver.remaining_pairings()
        )
        text += _("\nCancelling at this point will not use up a pairing.")
    ok = prepare(receiver)
    assistant = _create_assistant(receiver, ok, _finish, title, text, on_retry)
    if ok:
        GLib.timeout_add(_STATUS_CHECK, check_lock_state, assistant, receiver)
        deadline = time.monotonic() + _PAIRING_TIMEOUT
        GLib.timeout_add(_STATUS_CHECK, _update_countdown, assistant, receiver, deadline)
    return assistant


def _update_countdown(assistant, receiver, deadline):
    """Counts down the time left to find a device.

    Only this phase gets a countdown: Solaar sets its timeout itself, whereas the
    passkey entry timeout lives in the receiver's firmware and is never reported,
    so any timer shown during entry would be made up.
    """
    countdown = getattr(assistant, _COUNTDOWN, None)
    if countdown is None:
        return False
    remaining = deadline - time.monotonic()
    found = receiver.pairing.device_address or getattr(assistant, _PASSKEY_PAGE, None) is not None
    if not assistant.is_drawable() or remaining <= 0 or found:
        countdown.hide()
        return False
    seconds = int(math.ceil(remaining))
    countdown.set_fraction(remaining / _PAIRING_TIMEOUT)
    countdown.set_text(ngettext("%d second left", "%d seconds left", seconds) % seconds)
    return True


def prepare(receiver):
    if receiver.receiver_kind == "bolt":
        if receiver.discover(timeout=_PAIRING_TIMEOUT):
            return True
        else:
            receiver.pairing.error = "discovery did not start"
            return False
    elif receiver.set_lock(False, timeout=_PAIRING_TIMEOUT):
        return True
    else:
        receiver.pairing.error = "the pairing lock did not open"
        return False


def check_lock_state(assistant, receiver, count=2):
    if not assistant.is_drawable():
        logger.debug("assistant %s destroyed, bailing out", assistant)
        return False
    return _check_lock_state(assistant, receiver, count)


def _check_lock_state(assistant, receiver, count):
    if receiver.pairing.error:
        _pairing_failed(assistant, receiver, receiver.pairing.error)
        return False
    elif receiver.pairing.new_device:
        receiver.remaining_pairings(False)  # Update remaining pairings
        _pairing_succeeded(assistant, receiver, receiver.pairing.new_device)
        return False
    elif not receiver.pairing.lock_open and not receiver.pairing.discovering:
        if count > 0:
            # the actual device notification may arrive later so have a little patience
            GLib.timeout_add(_STATUS_CHECK, check_lock_state, assistant, receiver, count - 1)
        else:
            _pairing_failed(assistant, receiver, "failed to open pairing lock")
        return False
    elif receiver.pairing.lock_open and receiver.pairing.device_passkey:
        _show_passcode(assistant, receiver, receiver.pairing.device_passkey)
        return True
    elif receiver.pairing.discovering and receiver.pairing.device_address and receiver.pairing.device_name:
        add = receiver.pairing.device_address
        if getattr(assistant, _PAIRED_ADDRESS, None) == add:
            return True  # pairing was already requested for this device
        ent = 20 if receiver.pairing.device_kind == hidpp10_constants.DEVICE_KIND.keyboard else 10
        setattr(assistant, _PAIRED_ADDRESS, add)
        if receiver.pair_device(address=add, authentication=receiver.pairing.device_authentication, entropy=ent):
            return True
        else:
            _pairing_failed(assistant, receiver, "failed to open pairing lock")
            return False
    return True


def _pairing_failed(assistant, receiver, error):
    assistant.remove_page(0)  # needed to reset the window size
    logger.debug("%s fail: %s", receiver, error)
    _create_failure_page(assistant, receiver, error)


def _pairing_succeeded(assistant, receiver, device):
    assistant.remove_page(0)  # needed to reset the window size
    logger.debug("%s success: %s", receiver, device)
    _create_success_page(assistant, device)


def _finish(assistant, receiver):
    logger.debug("finish %s", assistant)
    assistant.destroy()
    receiver.pairing.new_device = None
    if receiver.pairing.lock_open:
        if receiver.receiver_kind == "bolt":
            receiver.pair_device("cancel")
        else:
            receiver.set_lock()
    if receiver.pairing.discovering:
        receiver.discover(True)
    if not receiver.pairing.lock_open and not receiver.pairing.discovering:
        receiver.pairing.error = None


def _passkey_steps(passkey, authentication):
    """Returns the ordered steps needed to enter the passkey on the device.

    Mice and touchpads take the passkey as ten button presses followed by a
    simultaneous press of both buttons, keyboards as its digits followed by the
    enter key. Returns None when the passkey cannot be interpreted, so that
    callers running inside a periodic check never have to handle an exception.
    """
    if passkey is None:
        return None
    if authentication & 0x01:  # keyboards spell the passcode out
        return [character for character in str(passkey)] + [_STEP_ENTER]
    try:
        bits = f"{int(passkey):010b}"
    except (TypeError, ValueError):
        return None
    # keep this mapping as it is: the receiver never reports which button was
    # pressed, so a changed polarity cannot be validated from inside Solaar
    return [_STEP_RIGHT if bit == "1" else _STEP_LEFT for bit in bits] + [_STEP_BOTH]


def _passkey_description(steps, passkey, authentication):
    """Renders the steps as the sentence used for the tooltip and for screen readers."""
    if authentication & 0x01:
        return _("Type %(passcode)s and then press the enter key.") % {"passcode": passkey}
    passcode = ", ".join(_("right") if step == _STEP_RIGHT else _("left") for step in steps[:-1])
    return _("Press %(code)s\nand then press left and right buttons simultaneously.") % {"code": passcode}


@dataclass
class _StepCell:
    """Placement of a single step inside the step strip."""

    x: float
    y: float
    width: float
    height: float
    step: str
    index: int


def _step_strip_cells(steps):
    """Lays the steps out in rows, with the final step alone below a separator."""
    leading = steps[:-1]  # the final step gets a band of its own, below the separator
    rows = [leading[index : index + _STEPS_PER_ROW] for index in range(0, len(leading), _STEPS_PER_ROW)]
    columns = max((len(row) for row in rows), default=1)
    width = 2 * _STRIP_MARGIN + columns * _CELL_WIDTH + (columns - 1) * _CELL_GAP
    row_height = _CELL_HEIGHT + _NUMBER_GAP + _NUMBER_HEIGHT
    cells = []
    index = 0
    y = float(_STRIP_MARGIN)
    for row in rows:
        row_width = len(row) * _CELL_WIDTH + (len(row) - 1) * _CELL_GAP
        x = (width - row_width) / 2
        for step in row:
            cells.append(_StepCell(x, y, _CELL_WIDTH, _CELL_HEIGHT, step, index))
            x += _CELL_WIDTH + _CELL_GAP
            index += 1
        y += row_height + _ROW_GAP
    separator_y = y - _ROW_GAP + _SEPARATOR_GAP
    final_width = _CELL_WIDTH * _FINAL_STEP_SCALE
    final_height = _CELL_HEIGHT * _FINAL_STEP_SCALE
    final_y = separator_y + _SEPARATOR_GAP
    cells.append(_StepCell((width - final_width) / 2, final_y, final_width, final_height, steps[-1], index))
    height = final_y + final_height + _NUMBER_GAP + _NUMBER_HEIGHT + _STRIP_MARGIN
    return cells, separator_y, width, height


def _strip_accent_color(style):
    """Takes the highlight colour from the theme, so the strip stays legible everywhere."""
    found, color = style.lookup_color("theme_selected_bg_color")
    if found:
        return color
    color = style.get_color(Gtk.StateFlags.SELECTED)
    if color is not None:
        return color
    return style.get_color(Gtk.StateFlags.NORMAL)


def _rounded_rectangle(cr, x, y, width, height, radius):
    radius = min(radius, width / 2, height / 2)
    cr.new_sub_path()
    cr.arc(x + width - radius, y + radius, radius, -0.5 * math.pi, 0.0)
    cr.arc(x + width - radius, y + height - radius, radius, 0.0, 0.5 * math.pi)
    cr.arc(x + radius, y + height - radius, radius, 0.5 * math.pi, math.pi)
    cr.arc(x + radius, y + radius, radius, math.pi, 1.5 * math.pi)
    cr.close_path()


def _draw_mouse_cell(cr, cell, accent, outline, fill_alpha, outline_alpha):
    """Draws a mouse seen from above, with the buttons this step needs filled in."""
    radius = _CELL_RADIUS * cell.width / _CELL_WIDTH
    split_y = cell.y + cell.height * 0.42
    split_x = cell.x + cell.width / 2
    cr.save()
    _rounded_rectangle(cr, cell.x, cell.y, cell.width, cell.height, radius)
    cr.clip()
    cr.set_source_rgba(accent.red, accent.green, accent.blue, fill_alpha)
    if cell.step in (_STEP_LEFT, _STEP_BOTH):
        cr.rectangle(cell.x, cell.y, cell.width / 2, split_y - cell.y)
        cr.fill()
    if cell.step in (_STEP_RIGHT, _STEP_BOTH):
        cr.rectangle(split_x, cell.y, cell.width / 2, split_y - cell.y)
        cr.fill()
    cr.restore()
    wheel_width = cell.width * 0.20
    wheel_height = cell.height * 0.28
    cr.set_source_rgba(outline.red, outline.green, outline.blue, outline_alpha)
    _rounded_rectangle(cr, cell.x, cell.y, cell.width, cell.height, radius)
    cr.stroke()
    cr.move_to(cell.x, split_y)
    cr.line_to(cell.x + cell.width, split_y)
    cr.stroke()
    cr.move_to(split_x, cell.y)
    cr.line_to(split_x, split_y - wheel_height / 2)
    cr.stroke()
    _rounded_rectangle(cr, split_x - wheel_width / 2, split_y - wheel_height / 2, wheel_width, wheel_height, wheel_width / 2)
    cr.stroke()


def _draw_key_cell(cr, cell, accent, outline, fill_alpha, outline_alpha):
    """Draws a key cap carrying either a digit of the passcode or an enter arrow."""
    radius = _CELL_RADIUS * cell.width / _CELL_WIDTH / 2
    cr.set_source_rgba(accent.red, accent.green, accent.blue, fill_alpha)
    _rounded_rectangle(cr, cell.x, cell.y, cell.width, cell.height, radius)
    cr.fill()
    cr.set_source_rgba(outline.red, outline.green, outline.blue, outline_alpha)
    _rounded_rectangle(cr, cell.x, cell.y, cell.width, cell.height, radius)
    cr.stroke()
    if cell.step == _STEP_ENTER:
        # an arrow pointing down and then left, the usual shape of an enter key
        top = cell.y + cell.height * 0.32
        bottom = cell.y + cell.height * 0.62
        left = cell.x + cell.width * 0.28
        right = cell.x + cell.width * 0.72
        cr.move_to(right, top)
        cr.line_to(right, bottom)
        cr.line_to(left, bottom)
        cr.stroke()
        head = cell.width * 0.14
        cr.move_to(left + head, bottom - head)
        cr.line_to(left, bottom)
        cr.line_to(left + head, bottom + head)
        cr.stroke()
    else:
        cr.set_font_size(cell.height * 0.46)
        extents = cr.text_extents(cell.step)
        cr.move_to(
            cell.x + (cell.width - extents.width) / 2 - extents.x_bearing,
            cell.y + (cell.height - extents.height) / 2 - extents.y_bearing,
        )
        cr.show_text(cell.step)


def _draw_check_mark(cr, cell, outline, outline_alpha):
    """Marks a step the receiver has already accepted."""
    size = cell.width * 0.22
    x = cell.x + cell.width * 0.72
    y = cell.y + cell.height * 0.78
    cr.set_source_rgba(outline.red, outline.green, outline.blue, outline_alpha)
    cr.move_to(x - size, y)
    cr.line_to(x - size / 3, y + size * 0.7)
    cr.line_to(x + size, y - size * 0.8)
    cr.stroke()


def _draw_step_strip(area, cr):
    """Paints which button every step needs, and how far entry has got.

    The two are kept apart on purpose: the filled quadrant always says which
    button to press, and only the emphasis says where the user is.
    """
    steps = getattr(area, _STEPS, None)
    if not steps:
        return False
    progress = getattr(area, _PROGRESS, None)
    # without progress notifications no step is singled out, and the strip is
    # simply the whole sequence, numbered and always readable
    done = 0 if progress is None else min(progress, len(steps))
    current = None if progress is None else min(progress, len(steps) - 1)
    cells, separator_y, width, _height = _step_strip_cells(steps)
    style = area.get_style_context()
    accent = _strip_accent_color(style)
    outline = style.get_color(Gtk.StateFlags.NORMAL)
    is_mouse = steps[-1] == _STEP_BOTH
    cr.save()
    cr.translate(max(0, (area.get_allocated_width() - width) / 2), 0)
    cr.set_line_width(1.0)
    cr.set_line_join(0)  # cairo.LINE_JOIN_MITER, spelled out to avoid importing cairo
    cr.select_font_face("sans-serif")
    cr.set_source_rgba(outline.red, outline.green, outline.blue, 0.25)
    cr.move_to(_STRIP_MARGIN, separator_y)
    cr.line_to(width - _STRIP_MARGIN, separator_y)
    cr.stroke()
    for cell in cells:
        if cell.index < done:
            fill_alpha, outline_alpha = 0.45, 0.35
        elif cell.index == current:
            fill_alpha, outline_alpha = 1.0, 1.0
        else:
            fill_alpha, outline_alpha = 0.22, 0.55
        if cell.index == current:
            cr.set_source_rgba(accent.red, accent.green, accent.blue, 1.0)
            cr.set_line_width(2.0)
            _rounded_rectangle(cr, cell.x - 3, cell.y - 3, cell.width + 6, cell.height + 6, _CELL_RADIUS)
            cr.stroke()
            cr.set_line_width(1.0)
        if is_mouse:
            _draw_mouse_cell(cr, cell, accent, outline, fill_alpha, outline_alpha)
        else:
            _draw_key_cell(cr, cell, accent, outline, fill_alpha, outline_alpha)
        if cell.index < done:
            _draw_check_mark(cr, cell, outline, 0.8)
        number = str(cell.index + 1)
        cr.set_font_size(_NUMBER_HEIGHT)
        cr.set_source_rgba(outline.red, outline.green, outline.blue, outline_alpha)
        extents = cr.text_extents(number)
        cr.move_to(
            cell.x + (cell.width - extents.width) / 2 - extents.x_bearing,
            cell.y + cell.height + _NUMBER_GAP - extents.y_bearing,
        )
        cr.show_text(number)
    cr.restore()
    return False


def _create_step_strip(steps, description):
    area = Gtk.DrawingArea()
    setattr(area, _STEPS, steps)
    setattr(area, _PROGRESS, 0)
    _cells, _separator_y, width, height = _step_strip_cells(steps)
    area.set_size_request(width, int(math.ceil(height)))
    area.connect(GtkSignal.DRAW.value, _draw_step_strip)
    # a drawing area is invisible to screen readers, so the sequence has to
    # stay available as text as well
    area.set_tooltip_text(description)
    area.get_accessible().set_description(description)
    return area


def _show_passcode(assistant, receiver, passkey):
    """Shows the passkey page, creating it on the first check and refreshing it afterwards."""
    page = getattr(assistant, _PASSKEY_PAGE, None)
    if page is None:
        page = _create_passcode_page(assistant, receiver, passkey)
        setattr(assistant, _PASSKEY_PAGE, page)
        assistant.set_page_complete(page, True)
        assistant.next_page()
    _update_passcode_page(page, receiver)


def _create_passcode_page(assistant, receiver, passkey):
    logger.debug("%s show passkey: %s", receiver, passkey)
    name = receiver.pairing.device_name
    authentication = receiver.pairing.device_authentication
    intro_text = _("%(receiver_name)s: pair new device") % {"receiver_name": receiver.name}
    page_text = _("Enter passcode on %(name)s.") % {"name": name}
    steps = _passkey_steps(passkey, authentication)
    if steps is None:  # unreadable passkey, so fall back to the plain instructions
        page_text += "\n"
        page_text += _("Type %(passcode)s and then press the enter key.") % {"passcode": passkey}
    elif authentication & 0x01:  # for keyboards the passcode is meant to be read
        page_text += "\n"
        page_text += _passkey_description(steps, passkey, authentication)
    page = _create_page(
        assistant,
        Gtk.AssistantPageType.PROGRESS,
        intro_text,
        "preferences-desktop-peripherals",
        page_text,
    )
    if steps is None:
        return page
    strip = _create_step_strip(steps, _passkey_description(steps, passkey, authentication))
    page.pack_start(strip, False, False, 0)
    status = Gtk.Label(label=_("Waiting for the first click…"))
    status.set_line_wrap(True)
    status.set_max_width_chars(_LABEL_WIDTH_CHARS)
    status.set_halign(Gtk.Align.CENTER)
    page.pack_start(status, False, False, 0)
    if steps[-1] == _STEP_BOTH:
        # the receiver reports that a button was pressed but never which one,
        # so say so rather than let a counted click look like a checked one
        honesty = Gtk.Label(label=_("Solaar cannot tell which button was pressed — only that the receiver accepted a click."))
        honesty.set_line_wrap(True)
        honesty.set_max_width_chars(_LABEL_WIDTH_CHARS)
        honesty.set_halign(Gtk.Align.CENTER)
        honesty.get_style_context().add_class("dim-label")
        page.pack_start(honesty, False, False, 0)
    reminder = Gtk.Label(label=_("Keep the device switched on and within range until pairing finishes."))
    reminder.set_line_wrap(True)
    reminder.set_max_width_chars(_LABEL_WIDTH_CHARS)
    reminder.set_halign(Gtk.Align.CENTER)
    reminder.get_style_context().add_class("dim-label")
    page.pack_start(reminder, False, False, 0)
    page.show_all()
    page.strip = strip
    page.status = status
    page.started = time.monotonic()
    return page


def _update_passcode_page(page, receiver):
    """Refreshes the page in place, so that the periodic check never appends another one."""
    strip = getattr(page, "strip", None)
    if strip is None:
        return
    steps = getattr(strip, _STEPS)
    total = len(steps) - 1  # the receiver counts presses, not the final combined one
    entered = receiver.pairing.passkey_entered
    if receiver.pairing.passkey_complete:
        progress = len(steps)
        text = _("The receiver is checking the sequence…")
    elif entered > 0:
        progress = entered
        if entered >= total and steps[-1] == _STEP_BOTH:
            text = _("Finally, press the left and right buttons at the same time.")
        else:
            text = _("Clicks registered by the receiver: %(done)d of %(total)d") % {
                "done": min(entered, total),
                "total": total,
            }
    elif time.monotonic() - page.started < _PROGRESS_GRACE:
        progress = 0
        text = _("Waiting for the first click…")
    else:  # this receiver never reports progress, so highlight nothing at all
        progress = None
        text = _("This receiver does not report entry progress. Follow the numbered steps in order.")
    page.status.set_label(text)
    setattr(strip, _PROGRESS, progress)
    strip.queue_draw()


def _create_assistant(receiver, ok, finish, title, text, on_retry=None):
    assistant = Gtk.Assistant()
    assistant.set_title(title)
    assistant.set_icon_name("list-add")
    assistant.set_size_request(400, 240)
    assistant.set_resizable(False)
    assistant.set_role("pair-device")
    # stash the callback before any page is built, so that a failure while preparing
    # also gets a retry button
    setattr(assistant, _ON_RETRY, on_retry)
    if ok:
        page_intro = _create_page(
            assistant,
            Gtk.AssistantPageType.PROGRESS,
            title,
            "preferences-desktop-peripherals",
            text,
        )
        countdown = Gtk.ProgressBar()
        countdown.set_show_text(True)
        countdown.set_visible(True)
        page_intro.pack_end(countdown, False, False, 0)
        setattr(assistant, _COUNTDOWN, countdown)
        spinner = Gtk.Spinner()
        spinner.set_visible(True)
        spinner.start()
        page_intro.pack_end(spinner, True, True, 24)
        assistant.set_page_complete(page_intro, True)
    else:
        page_intro = _create_failure_page(assistant, receiver, receiver.pairing.error)
    assistant.connect(GtkSignal.CANCEL.value, finish, receiver)
    assistant.connect(GtkSignal.CLOSE.value, finish, receiver)
    return assistant


def _create_success_page(assistant, device):
    def _check_encrypted(device, assistant, hbox):
        if assistant.is_drawable() and device.link_encrypted is False:
            hbox.pack_start(Gtk.Image.new_from_icon_name("security-low", Gtk.IconSize.MENU), False, False, 0)
            hbox.pack_start(Gtk.Label(label=_("The wireless link is not encrypted")), False, False, 0)
            hbox.show_all()
        return False

    page = _create_page(assistant, Gtk.AssistantPageType.SUMMARY)
    header = Gtk.Label(label=_("Found a new device:"))
    page.pack_start(header, False, False, 0)
    device_icon = Gtk.Image()
    icon_name = icons.device_icon_name(device.name, device.kind)
    device_icon.set_from_icon_name(icon_name, icons.LARGE_SIZE)
    page.pack_start(device_icon, True, True, 0)
    device_label = Gtk.Label()
    device_label.set_markup(f"<b>{device.name}</b>")
    page.pack_start(device_label, True, True, 0)
    hbox = Gtk.HBox(homogeneous=False, spacing=8)
    hbox.pack_start(Gtk.Label(label=" "), False, False, 0)
    hbox.set_property("expand", False)
    hbox.set_property("halign", Gtk.Align.CENTER)
    page.pack_start(hbox, False, False, 0)
    GLib.timeout_add(_STATUS_CHECK, _check_encrypted, device, assistant, hbox)  # wait a bit to check link status
    page.show_all()
    assistant.next_page()
    assistant.commit()


def _failure_text(label):
    """Describes a pairing failure, matching the error labels exactly.

    The cause has to be chosen from literals rather than translated at runtime,
    because gettext can only translate strings it saw when the catalogs were built.
    """
    if label == "device timeout" or label == "failed to open pairing lock":
        return _("Make sure your device is within range, and has a decent battery charge.")
    if label == "device not supported":
        return _("A new device was detected, but it is not compatible with this receiver.")
    if label == "too many devices":
        return _("More paired devices than receiver can support.")
    if label == "sequence timeout":
        return _("Sequence entry timed out.") + "\n" + _("Press the pairing button on your device again and retry.")
    if label == "failed":
        # the receiver reports nothing beyond this, so do not guess at a cause: a
        # wrong button, a mistimed press and a wrong sequence all arrive as "failed"
        return (
            _("The click sequence was not accepted.")
            + "\n"
            + _("The receiver only reports that verification failed; it cannot tell which buttons were pressed.")
            + "\n"
            + _("Press the pairing button on your device again and retry.")
        )
    return _("No further details are available about the error.")


def _retry_pairing(_button, assistant, receiver, on_retry):
    _finish(assistant, receiver)
    on_retry()


def _create_failure_page(assistant, receiver, error) -> Gtk.VBox:
    page = _create_page(
        assistant,
        Gtk.AssistantPageType.SUMMARY,
        _("Pairing failed"),
        "dialog-error",
        _failure_text(str(error)),
    )
    token = Gtk.Label()
    token.set_markup(f"<small><tt>{GLib.markup_escape_text(str(error))}</tt></small>")
    token.set_line_wrap(True)
    token.set_max_width_chars(_LABEL_WIDTH_CHARS)
    token.set_halign(Gtk.Align.CENTER)
    token.get_style_context().add_class("dim-label")
    page.pack_start(token, False, False, 0)
    on_retry = getattr(assistant, _ON_RETRY, None)
    if on_retry is not None:
        # packed into the page rather than added as an assistant action widget, so
        # that this path keeps working wherever the assistant is only duck-typed
        retry = Gtk.Button(label=_("Try again"))
        retry.set_halign(Gtk.Align.CENTER)
        retry.connect(GtkSignal.CLICKED.value, _retry_pairing, assistant, receiver, on_retry)
        page.pack_start(retry, False, False, 0)
    page.show_all()
    assistant.next_page()
    assistant.commit()
    return page


def _create_page(assistant, kind, header=None, icon_name=None, text=None) -> Gtk.VBox:
    p = Gtk.VBox(homogeneous=False, spacing=8)
    assistant.append_page(p)
    assistant.set_page_type(p, kind)
    if header:
        item = Gtk.HBox(homogeneous=False, spacing=16)
        p.pack_start(item, False, True, 0)
        label = Gtk.Label(label=header)
        label.set_line_wrap(True)
        item.pack_start(label, True, True, 0)
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
            item.pack_start(icon, False, False, 0)
    if text:
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        p.pack_start(label, False, False, 0)
    p.show_all()
    return p
