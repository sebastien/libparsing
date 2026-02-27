# -----------------------------------------------------------------------------
# Project   : Reporter
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : BSD License                       <http://ffctn.com/licenses/bsd>
# -----------------------------------------------------------------------------
# Creation  : 21-Sep-2009
# Last mod  : 04-Nov-2010
# -----------------------------------------------------------------------------

import sys, smtplib, json, time, socket, io

# TODO: Add info
# TODO: Add better message formatting

# Good error format
#
# [!] WARNING:-:module.Class.methodName:Your message (var=xx,var=xx)

__doc__ = """
The reporter module defines a simple interface to report errors that may occur
during program execution. Errors are composed of the following property:

 - 'message' which is the textual description of the error
 - 'component' which is the textual identifier for the component
 - 'code' which is the (optional) error code

Errors have three levels of severity:

 - 'warning'  which would be ''low severity''
 - 'error'    which would be ''medium severity''
 - 'critical' which would be ''high severity''

The reporter module offers three main ways of reporting errors:

 - 'StderrReporter' which logs all the errors to stderrr (the default)
 - 'FileReporter' which logs all the errors to a file (which could be a named pipe
   if you want to process it to somewhere else).
 - 'SMTPReporter' which will send an email as soon as the error happens
 - 'XMPPReporter' which will send an instant message as soon as the error happens.

The main functions you'll use in this module are the following:

>    reporter.warning(message, component, code=None)
>    reporter.error(message, component, code=None)
>    reporter.critical(message, component, code=None)

all of these functions will use the global 'reporter.REPORTER' instance, to which
you can 'register' more reporters. Here's for instance a setup where you'll report
errors both on stderr and on XMPP:

>    reporter.REPORTER.register(reporter.StderrReporter())
>    reporter.REPORTER.register(reporter.XMPPReporter('reporter@myserver.com','mypassword','admin@myserver.com'))

"""

DEBUG = 0
DEV = 1
INFO = 2
WARNING = 3
ERROR = 4
CRITICAL = 5

# ------------------------------------------------------------------------------
#
# REPORTER
#
# ------------------------------------------------------------------------------


class Reporter:
	"""Abstract class that defines the main (abstract) methods for an error
	reporter."""

	TEMPLATES = [
		">>> %s|%s|%s|%s",
		"--- %s|%s|%s|%s",
		" -  %s|%s|%s|%s",
		"WRN %s|%s|%s|%s",
		"ERR %s|%s|%s|%s",
		"!!! %s|%s|%s|%s",
	]

	def __init__(self, level=0):
		self.level = level
		self.delegates = []

	def register(self, *reporters):
		for reporter in reporters:
			assert not (reporter in self.delegates)
			self.delegates.append(reporter)

	def unregister(self, *reporters):
		for reporter in reporters:
			assert reporter in self.delegates
			self.delegates.remove(reporter)

	def timestamp(self):
		return time.strftime("%Y-%m-%dT%H:%M:%S")

	def debug(self, message, component, code=None):
		if DEBUG >= self.level:
			self._send(
				DEBUG,
				self.TEMPLATES[DEBUG]
				% (self.timestamp(), code or "-", component, message),
			)

	def dev(self, message, component, code=None):
		if DEV >= self.level:
			self._send(
				DEV,
				self.TEMPLATES[DEV]
				% (self.timestamp(), code or "-", component, message),
			)

	def info(self, message, component, code=None):
		"""Sends an info with the given message (as a string) and
		component (as a string)."""
		if INFO >= self.level:
			self._send(
				INFO,
				self.TEMPLATES[INFO]
				% (self.timestamp(), code or "-", component, message),
			)

	def warning(self, message, component, code=None):
		"""Sends a warning with the given message (as a string) and
		component (as a string)."""
		if WARNING >= self.level:
			self._send(
				WARNING,
				self.TEMPLATES[WARNING]
				% (self.timestamp(), code or "-", component, message),
			)

	def error(self, message, component, code=None):
		"""Sends an error with the given message (as a string) and
		component (as a string)."""
		if ERROR >= self.level:
			self._send(
				ERROR,
				self.TEMPLATES[ERROR]
				% (self.timestamp(), code or "-", component, message),
			)

	def critical(self, message, component, code=None):
		"""Sends a critical error with the given message (as a string) and
		component (as a string)."""
		if CRITICAL >= self.level:
			self._send(
				CRITICAL,
				self.TEMPLATES[CRITICAL]
				% (self.timestamp(), code or "-", component, message),
			)

	def _send(self, level, message):
		self._forward(level, message)

	def _forward(self, level, message):
		for delegate in self.delegates:
			delegate._send(level, message)


# ------------------------------------------------------------------------------
#
# FILE REPORTER
#
# ------------------------------------------------------------------------------


class FileReporter(Reporter):
	def __init__(self, path=None, fd=None, level=0):
		Reporter.__init__(self, level)
		if path:
			assert fd is None
			self.fd = open(path, "a", encoding="utf-8")
		else:
			assert path is None
			assert not (fd is None)
			assert isinstance(fd, io.TextIOBase)
			self.fd = fd

	def _send(self, level, message):
		if self.level > level:
			return
		self.fd.write(message + "\n")
		self.fd.flush()


# ------------------------------------------------------------------------------
#
# CONSOLE REPORTER
#
# ------------------------------------------------------------------------------


class ConsoleReporter(FileReporter):
	COLOR_NONE = -1
	COLOR_BLACK = 1
	COLOR_RED = 2
	COLOR_GREEN = 3
	COLOR_BLUE = 4
	COLOR_MAGENTA = 5
	COLOR_CYAN = 6
	COLOR_BLACK_BOLD = 11
	COLOR_RED_BOLD = 12
	COLOR_GREEN_BOLD = 13
	COLOR_BLUE_BOLD = 14
	COLOR_MAGENTA_BOLD = 15
	COLOR_CYAN_BOLD = 16

	def __init__(self, fd=None, level=0, color=True):
		FileReporter.__init__(self, fd=fd, level=level)
		self.color = color
		self.colorByLevel = [
			self.COLOR_GREEN_BOLD,  # DEBUG
			self.COLOR_GREEN,  # DEV
			self.COLOR_NONE,  # INFO
			self.COLOR_MAGENTA,  # WARNING
			self.COLOR_RED,  # ERROR
			self.COLOR_RED_BOLD,  # CRITICAL
		]

	def _send(self, level, message):
		color = self.getColorForLevel(level)
		FileReporter._send(
			self, level, self._colorStart(color) + message + self._colorEnd(color)
		)

	def getColorForLevel(self, level):
		level = max(0, min(level, len(self.colorByLevel)))
		return self.colorByLevel[level]

	def _colorStart(self, color):
		if not self.color:
			return ""
		if color == self.COLOR_NONE:
			return ""
		elif color == self.COLOR_BLACK:
			return "[0m[00;30m"
		elif color == self.COLOR_BLACK_BOLD:
			return "[0m[01;30m"
		elif color == self.COLOR_RED:
			return "[0m[00;31m"
		elif color == self.COLOR_RED_BOLD:
			return "[0m[01;31m"
		elif color == self.COLOR_GREEN:
			return "[0m[00;32m"
		elif color == self.COLOR_GREEN_BOLD:
			return "[0m[01;32m"
		elif color == self.COLOR_BLUE:
			return "[0m[00;34m"
		elif color == self.COLOR_BLUE_BOLD:
			return "[0m[01;34m"
		elif color == self.COLOR_MAGENTA:
			return "[0m[00;35m"
		elif color == self.COLOR_MAGENTA_BOLD:
			return "[0m[01;35m"
		elif color == self.COLOR_CYAN:
			return "[0m[00;35m"
		elif color == self.COLOR_CYAN_BOLD:
			return "[0m[01;35m"
		else:
			raise Exception("ConsoleReporter._colorStart: Unsupported color", color)

	def _colorEnd(self, color):
		if self.color and color != self.COLOR_NONE:
			return "[0m"
		else:
			return ""


# ------------------------------------------------------------------------------
#
# STDERR REPORTER
#
# ------------------------------------------------------------------------------


class StderrReporter(ConsoleReporter):
	def __init__(self, level=0, color=True):
		ConsoleReporter.__init__(self, fd=sys.stderr, level=level, color=color)


# ------------------------------------------------------------------------------
#
# STDOUT REPORTER
#
# ------------------------------------------------------------------------------


class StdoutReporter(ConsoleReporter):
	def __init__(self, level=0, color=True):
		ConsoleReporter.__init__(self, fd=sys.stdout, level=level, color=color)


# ------------------------------------------------------------------------------
#
# SMTP REPORTER
#
# ------------------------------------------------------------------------------


class SMTPReporter(Reporter):
	def __init__(self, recipient, origin=None, host="localhost", level=0):
		Reporter.__init__(self, level=level)
		self.host = host
		self.recipient = recipient
		self.origin = origin or "reporter@%s" % (host)

	def _send(self, level, message):
		if self.level > level:
			return
		server = smtplib.SMTP(host)
		server.sendmail(self.origin, [user], message)
		server.quit()


# ------------------------------------------------------------------------------
#
# XMPP REPORTER
#
# ------------------------------------------------------------------------------


class XMPPReporter(Reporter):
	def __init__(self, fromName, fromPassword, toUser, level=0):
		Reporter.__init__(self, level=level)
		import xmpp

		self.xmpp = xmpp
		self.name = fromName
		self.password = fromPassword
		self.recipient = toUser

	def _send(self, level, message):
		if self.level > level:
			return
		xmpp = self.xmpp
		name = self.name
		password = self.password
		jid = xmpp.protocol.JID(name)
		client = xmpp.Client(jid.getDomain(), debug=([]))
		conn = client.connect()
		if not conn:
			error(
				"Cannot connect to XMPP account (name=%s)" % (self.name),
				"reporter.XMPPReporter",
			)
			return False
		auth = client.auth(jid.getNode(), password, resource=(jid.getResource()))
		if not auth:
			error(
				"Cannot authenticate to XMPP account (name=%s)" % (self.name),
				"reporter.XMPPReporter",
			)
			return False
		client.send(xmpp.protocol.Message(self.recipient, message))
		client.disconnect()


# ------------------------------------------------------------------------------
#
# BEANSTALK REPORTER
#
# ------------------------------------------------------------------------------


class BeanstalkReporter(Reporter):
	"""Allows to send jobs on the Beanstalkd work queue, that could later be
	processed by a BeanstalkWorker."""

	def __init__(self, host="0.0.0.0", port=11300, tube="report", level=0):
		Reporter.__init__(self, level=level)
		self.host = host
		self.port = port
		self.tube = tube
		self.beanstalk = None
		try:
			self.connect()
		except socket.error as e:
			print("[!] BeanstalkWorker cannot connect to beanstalkd server")

	def connect(self):
		import beanstalkc

		self.beanstalkc = beanstalkc
		self.beanstalk = self.beanstalkc.Connection(host=self.host, port=self.port)
		self.beanstalk.use(self.tube)

	def _send(self, level, message):
		if self.beanstalk:
			self.beanstalk.put(
				json.dumps(
					{
						"type": "reporter.Message",
						"message": message,
						"level": level,
					}
				)
			)
		else:
			print("[!] BeanstalkWorker cannot connect to beanstalkd server")


# ------------------------------------------------------------------------------
#
# BEANSTALK WORKER
#
# ------------------------------------------------------------------------------


class BeanstalkWorker:
	"""Processes report jobs posted through Beanstalkd."""

	def __init__(self, host="0.0.0.0", port=11300, tube="report"):
		import beanstalkc

		self.beanstalkc = beanstalkc
		self.beanstalk = beanstalkc.Connection(host=host, port=port)
		self.beanstalk.watch(tube)
		self.beanstalk.ignore("default")
		self.isRunning = False

	def start(self):
		self.isRunning = True
		self.run()

	def stop(self):
		self.isRunning = False

	def run(self):
		while self.isRunning:
			self._iterate()

	def _iterate(self):
		try:
			job = self.beanstalk.reserve()
		except (
			(
				self.beanstalkc.DeadlineSoon,
				self.beanstalkc.CommandFailed,
				self.beanstalkc.UnexpectedResponse,
			),
			e,
		):
			reporter.error(str(e), "beanstalkc")
			return False
		# We make sure that the job is JSON
		try:
			data = json.loads(job.body)
		except:
			job.release()
			return False
		if (
			not data
			or not (type(data) is dict)
			or not (data.get("type") == "reporter.Message")
		):
			return False
		else:
			self._process(data, job)
			return True

	def _process(self, message, job):
		REPORTER._send(message["level"], message["message"])
		job.delete()


# ------------------------------------------------------------------------------
#
# MODULE GLOBALES AND FUNCTIONS
#
# ------------------------------------------------------------------------------

REPORTER = Reporter()


def register(*reporter):
	"""Registers the reporter instance(s) in the `REPORTER` singleton."""
	return REPORTER.register(*reporter)


def unregister(*repporter):
	"""Unegisters the reporter instance(s) in the `REPORTER` singleton."""
	return REPORTER.unregister(*reporter)


def debug(message, component, code=None):
	return REPORTER.debug(message, component, code)


def dev(message, component, code=None):
	return REPORTER.dev(message, component, code)


def info(message, component, code=None):
	return REPORTER.info(message, component, code)


def warning(message, component, code=None):
	return REPORTER.warning(message, component, code)


def error(message, component, code=None):
	return REPORTER.error(message, component, code)


def critical(message, component, code=None):
	return REPORTER.critical(message, component, code)


def bind(component):
	"""Returns `(info,warning,error,critical)` functions that take `(message,code=None)`
	as parameters. This should be used in the following way, at the head of a
	module:

	>    debug, dev, info, warning, error, critical = reporter.bind("mymodule")

	and then

	>    info("Hello, world!")
	"""

	def wrap(function):
		def _(*args, **kwargs):
			function(" ".join(map(str, args)), component, code=kwargs.get("code"))

		return _

	return (
		wrap(debug),
		wrap(dev),
		wrap(info),
		wrap(warning),
		wrap(error),
		wrap(critical),
	)


# EOF - vim: ts=4 sw=4 noet
