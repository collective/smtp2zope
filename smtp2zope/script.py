#!/usr/bin/python

"""
 smtp2zope.py - Read a email from stdin and forward it to a url

 Usage: smtp2zope.py URL [MAXBYTES]

 URL      = call this URL with the email as a post-request
            Authentication can be included in URL:
            http://username:password@yourHost/...

 MAXBYTES = optional: only forward mails < MAXBYTES to URL

 Please note: Output is logged to maillog per default on unices.  See
 your maillog (e.g. /var/log/mail.log) to debug problems with the
 setup.

 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
"""

import base64
import re
import sys
import urllib
import urllib2

from smtp2zope import config
from smtp2zope.locking import LockFile
from smtp2zope.locking import TimeOutError

##
# Meaningful exit-codes for a smtp-server.
EXIT_USAGE = 64
EXIT_NOUSER = 67
EXIT_NOPERM = 77
EXIT_TEMPFAIL = 75

##
# Setup of loggers for error-messages
try:
    # When this works, output is expected to end up in something like
    # /var/log/mail.log
    import syslog
    syslog.openlog('mailboxer')
    log_critical = lambda msg: syslog.syslog(
        syslog.LOG_CRIT | syslog.LOG_MAIL, msg)
    log_error = lambda msg: syslog.syslog(
        syslog.LOG_ERR | syslog.LOG_MAIL, msg)
    log_warning = lambda msg: syslog.syslog(
        syslog.LOG_WARNING | syslog.LOG_MAIL, msg)
    log_info = lambda msg: syslog.syslog(
        syslog.LOG_INFO | syslog.LOG_MAIL, msg)
except:
    # if we can't open syslog, just fake it
    fake_logger = lambda msg: sys.stderr.write(msg + "\n")
    log_critical = fake_logger
    log_error = fake_logger
    log_warning = fake_logger
    log_info = fake_logger


def main():
    ##
    # Main part of submitting an email to a http-server.
    # All requests will be serialized with locks.

    # check number of parameters
    if len(sys.argv) == 1 or len(sys.argv) > 3:
        log_critical('Wrong number of parameters was given.')
        sys.exit(EXIT_USAGE)

    # optional MAXBYTES?
    MAXBYTES = config.MAXBYTES
    if len(sys.argv) == 3:
        try:
            MAXBYTES = long(sys.argv[2])
        except ValueError:
            log_critical('Specified value of MAXBYTES (%s) was not an integer.'
                         % sys.argv[2])
            sys.exit(EXIT_USAGE)

    # Get the raw mail
    mailString = sys.stdin.read()

    # Check size of mail
    mailLen = len(mailString)
    if MAXBYTES > 0 and mailLen > MAXBYTES:
        log_warning('Rejecting email, due to size (%s bytes, limit %s bytes).'
                    % (mailLen, MAXBYTES))
        sys.exit(EXIT_NOPERM)

    # Check for spam
    for regexp in config.SPAM_TAGS:
        if re.search(regexp, mailString):
            log_warning('Rejecting email, due to %s' % regexp)
            sys.exit(0)

    if config.USE_LOCKS:
        # Create temporary lockfile
        lock = LockFile(config.LOCKFILE_LOCATION)
        try:
            lock.lock(config.LOCK_TIMEOUT)
        except TimeOutError:
            log_info('Serialisation timeout occurred, message was requeued.')
            sys.exit(EXIT_TEMPFAIL)

    # Transfer mail to http-server.
    # urllib2 handles server-responses (errors) much better than urllib.
    # urllib2 is, in fact, too much better. Its built-in redirect handler
    # can mask authorization problems when a cookie-based authenticator is in
    # use -- as with Plone. Also, I can't think of any reason why we would
    # want to allow redirection of these requests!
    #
    # So, let's create and install a disfunctional redirect handler.

    class BrokenHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)

    # Install the broken redirect handler
    opener = urllib2.build_opener(BrokenHTTPRedirectHandler())
    urllib2.install_opener(opener)

    # Get the url to call
    callURL = sys.argv[1]

    # Check for authentication-string (username:passwd) in URL
    # URL looks like: http://username:passwd@host/...
    # Avoid getting tripped up by for example http://example.org/@@poimail
    auth_pattern = re.compile('://([^/:@]+:[^/:@]+)@')
    match = auth_pattern.search(callURL)
    if match:
        AUTHORIZATION = match.groups()[0]
        callURL = callURL.replace(AUTHORIZATION + '@', '')
    else:
        AUTHORIZATION = ''

    try:
        req = urllib2.Request(callURL)
        if AUTHORIZATION:
            auth = base64.encodestring(AUTHORIZATION).strip()
            req.add_header('Authorization', 'Basic %s' % auth)
        data = config.MAIL_PARAMETER_NAME + "=" + urllib.quote(mailString)
        urllib2.urlopen(req, data=data)
    except Exception, e:
        # If MailBoxer doesn't exist, bounce message with EXIT_NOUSER,
        # so the sender will receive a "user-doesn't-exist"-mail from MTA.
        if hasattr(e, 'code') and e.code == 404:
            log_error("URL at %s doesn't exist (%s)." % (callURL, e))
            sys.exit(EXIT_NOUSER)
        else:
            # Server down? EXIT_TEMPFAIL causes the MTA to try again later.
            log_error('A problem (%s) occurred uploading email to URL %s.' % (
                e, callURL))
            sys.exit(EXIT_TEMPFAIL)
    else:
        log_info("Successfully handled incoming mail.")

    # All locks will be removed when Python cleans up!
