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

from typing import Any
from typing import Callable


class RulesModel:
    def __init__(self, rules, load_rules_func: Callable[[], Any], save_rules_func: Callable[[], bool]):
        self.rules = rules
        self._load_rules = load_rules_func
        self._save_rules = save_rules_func
        self.unsaved_changes = False

    def load_rules(self) -> Any:
        loaded_rules = self._load_rules()
        self.unsaved_changes = False
        return loaded_rules

    def save_rules(self) -> bool:
        """Save rules to file, when there are unsaved changes.

        Returns
        -------
        bool
            True if latest config is saved, False otherwise.
        """
        if not self.unsaved_changes:
            return True

        success = self._save_rules()
        if success:
            self.unsaved_changes = False
        return success
