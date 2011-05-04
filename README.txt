Introduction
============

``smtp2zope`` is a script that takes an email as input, does some
transformation, and submits it to a backend server using a url.
Traditionally, Zope is expected to be the receiving server, hence the
name, but should work fine for other servers too.

Originally, the code here comes from the MailBoxer_ product for Zope.

.. _MailBoxer: http://www.iungo.org/products/MailBoxer


Usage
-----

When installing this package, a ``smtp2zope`` script is generated.
The script reads from standard input and expects a url and optional
maximum number of bytes as arguments::

  smtp2zope URL [MAXBYTES]

URL:

  call this URL with the email as a post-request.  Authentication can
  be included in URL: http://username:password@example.org/some-page

MAXBYTES:

  optional: only forward mails with a size of less than MAXBYTES to
  the URL

So a test run could look like this::

  cat testmail.txt > /path/to/smtp2zope http://admin:secret@example.org/my-mail-handler


Mail server integration
-----------------------

Mail comes in through a mail server.  So when you want mail for
``mailme@example.org`` to be handled by smtp2zope and sent to your web
server, you should add an alias in your smtp server configuration.
Something like this probably works (there might be slight differences
depending on which mail server you use)::

  mailme@example.org "|/path/to/smtp2zope http://admin:secret@example.org/my-mail-handler 1000000"

The number at the end restricts the maximum size of a message; this is
optional, but highly recommended.


Debugging
---------

Please note: output is logged to maillog per default on unices.  See
your maillog (e.g. ``/var/log/mail.log``) to debug problems with the setup.


Buildout
--------

If you like setting up your project with zc.buildout (I myself do),
this simple snippet is enough to create the ``bin/smtp2zope`` script::

  [script]
  recipe = zc.recipe.egg
  eggs = smtp2zope


Credits
-------

- Original implementation: Maik Jablonski

- Packaging: Maurits van Rees
