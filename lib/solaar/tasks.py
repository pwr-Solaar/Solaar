#!/usr/bin/env python3

## Copyright (C) 2012-2013  Daniel Pavel
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

from threading import Thread

logger = logging.getLogger(__name__)

try:
    from Queue import Queue
except ImportError:
    from queue import Queue


class TaskRunner(Thread):
    def __init__(self, name):
        super().__init__(name=name)
        self.daemon = True
        self.queue = Queue(16)
        self.alive = False

    def __call__(self, function, *args, **kwargs):
        task = (function, args, kwargs)
        self.queue.put(task)

    def stop(self):
        self.alive = False
        self.queue.put(None)

    def run(self):
        self.alive = True

        logger.debug("started")

        while self.alive:
            task = self.queue.get()
            if task:
                function, args, kwargs = task
                assert function
                try:
                    function(*args, **kwargs)
                except Exception:
                    logger.exception("calling %s", function)

        logger.debug("stopped")
