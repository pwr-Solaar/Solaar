## Copyright (C) Solaar Contributors
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
import abc

from contextlib import contextmanager as contextlib_contextmanager
from typing import Any
from typing import Callable

from gi.repository import Gtk
from logitech_receiver import diversion


def norm(s):
    return s.replace("_", "").replace(" ", "").lower()


class CompletionEntry(Gtk.Entry):
    def __init__(self, values, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CompletionEntry.add_completion_to_entry(self, values)

    @classmethod
    def add_completion_to_entry(cls, entry, values):
        completion = entry.get_completion()
        if not completion:
            liststore = Gtk.ListStore(str)
            completion = Gtk.EntryCompletion()
            completion.set_model(liststore)
            completion.set_match_func(lambda completion, key, it: norm(key) in norm(completion.get_model()[it][0]))
            completion.set_text_column(0)
            entry.set_completion(completion)
        else:
            liststore = completion.get_model()
            liststore.clear()
        for v in sorted(set(values), key=str.casefold):
            liststore.append((v,))


class RuleComponentUI(abc.ABC):
    CLASS = diversion.RuleComponent

    def __init__(self, panel, on_update: Callable = None):
        self.panel = panel
        self.widgets = {}  # widget -> coord. in grid
        self.component = None
        self._ignore_changes = 0
        self._on_update_callback = (lambda: None) if on_update is None else on_update
        self.create_widgets()

    @abc.abstractmethod
    def create_widgets(self) -> dict:
        pass

    def show(self, component, editable=True):
        self._show_widgets(editable)
        self.component = component

    @abc.abstractmethod
    def collect_value(self) -> Any:
        pass

    @contextlib_contextmanager
    def ignore_changes(self):
        self._ignore_changes += 1
        yield None
        self._ignore_changes -= 1

    def _on_update(self, *_args):
        if not self._ignore_changes and self.component is not None:
            value = self.collect_value()
            self.component.__init__(value, warn=False)
            self._on_update_callback()
            return value
        return None

    def _show_widgets(self, editable):
        self._remove_panel_items()
        for widget, coord in self.widgets.items():
            self.panel.attach(widget, *coord)
            widget.set_sensitive(editable)
            widget.show()

    @classmethod
    def left_label(cls, component) -> str:
        return type(component).__name__

    @classmethod
    def right_label(cls, _component) -> str:
        return ""

    @classmethod
    def icon_name(cls) -> str:
        return ""

    def _remove_panel_items(self):
        for c in self.panel.get_children():
            self.panel.remove(c)

    def update_devices(self):  # noqa: B027
        pass
