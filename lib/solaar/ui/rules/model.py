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
from typing import Callable


class RulesModel:
    def __init__(self, load_rules_func: Callable, save_rules_func: Callable[..., bool]):
        self.load_rules = load_rules_func
        self.save_rules = save_rules_func
        self.unsaved_changes = False

    def load_rules(self):
        self.load_rules()
        self.unsaved_changes = False

    def save_rules(self) -> bool:
        success = self.save_rules()
        if success:
            self.unsaved_changes = False
        return success
