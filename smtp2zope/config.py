import os
import tempfile

##
# If you wish to use HTTP Basic Authentication, set a user id and
# password here.  Alternatively you can call the URL like:
#
# http://username:password@yourHost/MailBoxer/manage_mailboxer
#
# Note that this is not necessary in the default MailBoxer
# configuration, but may be used to add some extra security.
#
# Format: username:password
AUTHORIZATION = ''

##
# MAXBYTES is the number of maximum bytes per mail are allowed to
# transfer to MailBoxer. 0 means unlimited. MAXBYTES can be specified
# as last parameter when calling smtp2zope.py
MAXBYTES = 0

##
# SPAM_TAGS are a list of regular expressions which will be checked
# against the email before forwarding to Zope.  If the regexp is
# found, the email will be discarded silently.
SPAM_TAGS = ["\[SPAM\]", "\[VIRUS\]"]

##
# If you have a special setup which don't allow locking /
# serialization, set USE_LOCKS = 0
USE_LOCKS = 1

##
# This should work with Unix & Windows & MacOS,
# if not, set it on your own (e.g. '/tmp/smtp2zope.lock').
LOCKFILE_LOCATION = os.path.join(tempfile.gettempdir(), 'smtp2zope.lock')

##
# The amount of time in seconds to wait to be serialised.
LOCK_TIMEOUT = 30

##
# Number of seconds the process expects to hold the lock.
DEFAULT_LOCK_LIFETIME = 30

##
# REQUEST-parameter for submitted mail via URL
MAIL_PARAMETER_NAME = "Mail"
