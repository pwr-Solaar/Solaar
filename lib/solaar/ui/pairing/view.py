import logging

from typing import Protocol
from typing import Union

from gi.repository import Gdk
from gi.repository import Gtk

from solaar.i18n import _
from solaar.ui import icons as _icons

logger = logging.getLogger(__name__)


class PresenterProtocol(Protocol):
    def handle_prepare(self, assistant, page) -> None:
        ...

    def handle_close(self, assistant) -> None:
        ...


def _create_page_view(header=None, icon_name=None, text=None) -> Gtk.VBox:
    box = Gtk.VBox(False, 8)

    if header:
        item = Gtk.HBox(False, 16)
        box.pack_start(item, False, True, 0)

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
        box.pack_start(label, False, False, 0)
    return box


class PairingView:
    def __init__(self, window: Gtk.Window) -> None:
        self.window = window
        self.assistant: Union[Gtk.Assistant, None] = None

    def init_ui(self, presenter: PresenterProtocol, page_title: str, page_text: str) -> None:
        self.assistant = Gtk.Assistant()
        self.assistant.set_title(page_title)
        self.assistant.set_icon_name("list-add")

        self.assistant.set_size_request(400, 240)
        self.assistant.set_resizable(False)
        self.assistant.set_role("pair-device")

        self.assistant.set_transient_for(self.window)
        self.assistant.set_destroy_with_parent(True)
        self.assistant.set_modal(True)
        self.assistant.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.assistant.set_position(Gtk.WindowPosition.CENTER)

        page_intro = _create_page_view(page_title, "preferences-desktop-peripherals", page_text)
        page_intro.show_all()
        self.assistant.append_page(page_intro)
        self.assistant.set_page_type(page_intro, Gtk.AssistantPageType.PROGRESS)

        page_intro.show_all()
        spinner = Gtk.Spinner()
        spinner.set_visible(True)
        page_intro.pack_end(spinner, True, True, 24)

        self.assistant.connect("prepare", presenter.handle_prepare)
        self.assistant.connect("cancel", presenter.handle_close)
        self.assistant.connect("close", presenter.handle_close)

    def show_check_lock_state(self, page):
        spinner = page.get_children()[-1]
        spinner.start()
        self.assistant.set_page_complete(page, True)

    def show_passkey(self, page_title: str, page_text: str):
        passcode_page = _create_page_view(page_title, "preferences-desktop-peripherals", page_text)
        passcode_page.show_all()
        self.assistant.append_page(passcode_page)
        self.assistant.set_page_type(passcode_page, Gtk.AssistantPageType.PROGRESS)

        self.assistant.set_page_complete(passcode_page, True)
        self.assistant.next_page()

    def show_pairing_succeeded(self, device, handle_check_and_show_encryption_cb):
        pairing_success_page = _create_page_view()
        pairing_success_page.show_all()
        self.assistant.append_page(pairing_success_page)
        self.assistant.set_page_type(pairing_success_page, Gtk.AssistantPageType.SUMMARY)

        header = Gtk.Label(_("Found a new device:"))
        header.set_alignment(0.5, 0)
        pairing_success_page.pack_start(header, False, False, 0)

        device_icon = Gtk.Image()
        icon_set = _icons.device_icon_set(device.name, device.kind)
        device_icon.set_from_icon_set(icon_set, Gtk.IconSize.LARGE)
        device_icon.set_alignment(0.5, 1)
        pairing_success_page.pack_start(device_icon, True, True, 0)

        device_label = Gtk.Label()
        device_label.set_markup(f"<b>{device.name}</b>")
        device_label.set_alignment(0.5, 0)
        pairing_success_page.pack_start(device_label, True, True, 0)

        hbox = Gtk.HBox(False, 8)
        hbox.pack_start(Gtk.Label(" "), False, False, 0)
        hbox.set_property("expand", False)
        hbox.set_property("halign", Gtk.Align.CENTER)
        pairing_success_page.pack_start(hbox, False, False, 0)
        handle_check_and_show_encryption_cb(device, hbox)

        pairing_success_page.show_all()

        self.assistant.next_page()
        self.assistant.commit()

    def show_encryption(self, view):
        if self.assistant.is_drawable():
            view.pack_start(Gtk.Image.new_from_icon_name("security-low", Gtk.IconSize.MENU), False, False, 0)
            view.pack_start(Gtk.Label(_("The wireless link is not encrypted") + "!"), False, False, 0)
            view.show_all()

    def show_pairing_failed(self, title, text):
        self.assistant.commit()

        page = _create_page_view(title, "dialog-error", text)
        page.show_all()
        self.assistant.append_page(page)
        self.assistant.set_page_type(page, Gtk.AssistantPageType.SUMMARY)

        self.assistant.next_page()
        self.assistant.commit()

    def is_drawable(self):
        is_drawable = self.assistant.is_drawable()
        if not is_drawable:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("assistant %s destroyed, bailing out", self.assistant)
        return is_drawable

    def get_current_page(self) -> int:
        return self.assistant.get_current_page()

    def remove_page(self, page):
        self.assistant.remove_page(page)

    def show_finished(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("finish %s", self.assistant)

        self.assistant.destroy()

    def mainloop(self) -> None:
        self.assistant.present()
