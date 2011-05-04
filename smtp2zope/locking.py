##
# Portable, NFS-safe file locking with timeouts.
#
# This code has been taken from the GNU MailMan mailing list system,
# with our thanks. Code was modified by Maik Jablonski.

from stat import ST_NLINK, ST_MTIME
import errno
import os
import random
import socket
import time

from smtp2zope.config import DEFAULT_LOCK_LIFETIME

# Exceptions that can be raised by this module


class LockError(Exception):
    """Base class for all exceptions in this module."""


class AlreadyLockedError(LockError):
    """An attempt is made to lock an already locked object."""


class NotLockedError(LockError):
    """An attempt is made to unlock an object that isn't locked."""


class TimeOutError(LockError):
    """The timeout interval elapsed before the lock succeeded."""


class LockFile:
    """A portable way to lock resources by way of the file system. """

    COUNTER = 0

    def __init__(self, lockfile, lifetime=DEFAULT_LOCK_LIFETIME):
        """Create the resource lock using lockfile as the global lock file.

        Each process laying claim to this resource lock will create their own
        temporary lock files based on the path specified by lockfile.
        Optional lifetime is the number of seconds the process expects to hold
        the lock.  (see the module docstring for details).

        """
        self.__lockfile = lockfile
        self.__lifetime = lifetime
        # This works because we know we're single threaded
        self.__counter = LockFile.COUNTER
        LockFile.COUNTER += 1
        self.__tmpfname = '%s.%s.%d.%d' % (lockfile,
                                           socket.gethostname(),
                                           os.getpid(),
                                           self.__counter)

    def set_lifetime(self, lifetime):
        """Set a new lock lifetime.

        This takes affect the next time the file is locked, but does not
        refresh a locked file.
        """
        self.__lifetime = lifetime

    def get_lifetime(self):
        """Return the lock's lifetime."""
        return self.__lifetime

    def refresh(self, newlifetime=None, unconditionally=False):
        """Refreshes the lifetime of a locked file.

        Use this if you realize that you need to keep a resource locked longer
        than you thought.  With optional newlifetime, set the lock's lifetime.
        Raises NotLockedError if the lock is not set, unless optional
        unconditionally flag is set to true.
        """
        if newlifetime is not None:
            self.set_lifetime(newlifetime)
        # Do we have the lock?  As a side effect, this refreshes the lock!
        if not self.locked() and not unconditionally:
            raise NotLockedError('%s: %s' % (repr(self), self.__read()))

    def lock(self, timeout=0):
        """Acquire the lock.

        This blocks until the lock is acquired unless optional timeout is
        greater than 0, in which case, a TimeOutError is raised when timeout
        number of seconds (or possibly more) expires without lock acquisition.
        Raises AlreadyLockedError if the lock is already set.
        """
        if timeout:
            timeout_time = time.time() + timeout
        # Make sure my temp lockfile exists, and that its contents are
        # up-to-date (e.g. the temp file name, and the lock lifetime).
        self.__write()
        # TBD: This next call can fail with an EPERM.  I have no idea why, but
        # I'm nervous about wrapping this in a try/except.  It seems to be a
        # very rare occurence, only happens from cron, and (only?) on Solaris
        # 2.6.
        self.__touch()

        while True:
            # Create the hard link and test for exactly 2 links to the file
            try:
                os.link(self.__tmpfname, self.__lockfile)
                # If we got here, we know we know we got the lock, and never
                # had it before, so we're done.  Just touch it again for the
                # fun of it.
                self.__touch()
                break
            except OSError, e:
                # The link failed for some reason, possibly because someone
                # else already has the lock (i.e. we got an EEXIST), or for
                # some other bizarre reason.
                if e.errno == errno.ENOENT:
                    # TBD: in some Linux environments, it is possible to get
                    # an ENOENT, which is truly strange, because this means
                    # that self.__tmpfname doesn't exist at the time of the
                    # os.link(), but self.__write() is supposed to guarantee
                    # that this happens!  I don't honestly know why this
                    # happens, but for now we just say we didn't acquire the
                    # lock, and try again next time.
                    pass
                elif e.errno != errno.EEXIST:
                    # Something very bizarre happened.  Clean up our state and
                    # pass the error on up.
                    os.unlink(self.__tmpfname)
                    raise
                elif self.__linkcount() != 2:
                    # Somebody's messin' with us!
                    pass
                elif self.__read() == self.__tmpfname:
                    # It was us that already had the link.
                    raise AlreadyLockedError
                # otherwise, someone else has the lock
                pass
            # We did not acquire the lock, because someone else already has
            # it.  Have we timed out in our quest for the lock?
            if timeout and timeout_time < time.time():
                os.unlink(self.__tmpfname)
                raise TimeOutError
            # Okay, we haven't timed out, but we didn't get the lock.  Let's
            # find if the lock lifetime has expired.
            if time.time() > self.__releasetime():
                # Yes, so break the lock.
                self.__break()
            # Okay, someone else has the lock, our claim hasn't timed out yet,
            # and the expected lock lifetime hasn't expired yet.  So let's
            # wait a while for the owner of the lock to give it up.
            self.__sleep()

    def unlock(self, unconditionally=False):
        """Unlock the lock.

        If we don't already own the lock (either because of unbalanced unlock
        calls, or because the lock was stolen out from under us), raise a
        NotLockedError, unless optional `unconditionally' is true.
        """
        islocked = self.locked()
        if not islocked and not unconditionally:
            raise NotLockedError
        # If we owned the lock, remove the global file, relinquishing it.
        if islocked:
            try:
                os.unlink(self.__lockfile)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
        # Remove our tempfile
        try:
            os.unlink(self.__tmpfname)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def locked(self):
        """Return true if we own the lock, false if we do not.

        Checking the status of the lock resets the lock's lifetime, which
        helps avoid race conditions during the lock status test.
        """
        # Discourage breaking the lock for a while.
        try:
            self.__touch()
        except OSError, e:
            if e.errno == errno.EPERM:
                # We can't touch the file because we're not the owner.  I
                # don't see how we can own the lock if we're not the owner.
                return False
            else:
                raise
        # TBD: can the link count ever be > 2?
        if self.__linkcount() != 2:
            return False
        return self.__read() == self.__tmpfname

    def finalize(self):
        self.unlock(unconditionally=True)

    def __del__(self):
        self.finalize()

    #
    # Private interface
    #

    def __write(self):
        # Make sure it's group writable
        oldmask = os.umask(002)
        try:
            fp = open(self.__tmpfname, 'w')
            fp.write(self.__tmpfname)
            fp.close()
        finally:
            os.umask(oldmask)

    def __read(self):
        try:
            fp = open(self.__lockfile)
            filename = fp.read()
            fp.close()
            return filename
        except EnvironmentError, e:
            if e.errno != errno.ENOENT:
                raise
            return None

    def __touch(self, filename=None):
        t = time.time() + self.__lifetime
        try:
            # TBD: We probably don't need to modify atime, but this is easier.
            os.utime(filename or self.__tmpfname, (t, t))
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def __releasetime(self):
        try:
            return os.stat(self.__lockfile)[ST_MTIME]
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
            return -1

    def __linkcount(self):
        try:
            return os.stat(self.__lockfile)[ST_NLINK]
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
            return -1

    def __break(self):
        try:
            self.__touch(self.__lockfile)
        except OSError, e:
            if e.errno != errno.EPERM:
                raise
        # Get the name of the old winner's temp file.
        winner = self.__read()
        # Remove the global lockfile, which actually breaks the lock.
        try:
            os.unlink(self.__lockfile)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        # Try to remove the old winner's temp file, since we're assuming the
        # winner process has hung or died.
        try:
            if winner:
                os.unlink(winner)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def __sleep(self):
        interval = random.random() * 2.0 + 0.01
        time.sleep(interval)
