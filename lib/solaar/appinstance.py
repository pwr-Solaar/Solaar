#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

#
#
#

import fcntl as _fcntl
import os.path as _path
import os as _os

from solaar import NAME
_program = NAME.lower()
del NAME

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger


def check():
	"""Select a file lock location and try to acquire it.
	Suitable locations are $XDG_RUNTIME_DIR, /run/lock, /var/lock, and $TMPDIR.
	The first one found and writable is used.
	"""
	# ensure no more than a single instance runs at a time
	lock_fd = None
	for p in _os.environ.get('XDG_RUNTIME_DIR'), '/run/lock', '/var/lock', _os.environ.get('TMPDIR', '/tmp'):
		# pick the first temporary writable folder
		if p and _path.isdir(p) and _os.access(p, _os.W_OK):
			lock_path = _path.join(p, _program + '.single-instance.' + str(_os.getuid()))
			try:
				lock_fd = open(lock_path, 'wb')
				if _log.isEnabledFor(_DEBUG):
					_log.debug("single-instance lock file is %s", lock_path)
				break
			except:
				pass

	if lock_fd:
		try:
			_fcntl.flock(lock_fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
			if _log.isEnabledFor(_DEBUG):
				_log.debug("acquired single-instance lock %s", lock_fd)
			return lock_fd
		except IOError as e:
			if e.errno == 11:
				_log.warn("lock file is busy, %s already running: %s", _program, e)
				import sys
				sys.exit(_program + ": error: already running")
			else:
				raise
	else:
		import sys
		print (_program + ": warning: no suitable location for the lockfile found; ignoring", file=sys.stderr)


def close(lock_fd):
	"""Release a file lock."""
	if lock_fd:
		_fcntl.flock(lock_fd, _fcntl.LOCK_UN)
		lock_fd.close()
		if _log.isEnabledFor(_DEBUG):
			_log.debug("released single-instance lock %s", lock_fd)
