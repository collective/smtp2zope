Changelog
=========

1.2 (2012-10-14)
----------------

- Moved to https://github.com/collective/smtp2zope
  [maurits]


1.1 (2011-05-05)
----------------

- Use a better way to determine the basic authentication information
  that is passed in the url so the logic does not fail when the url
  has an ``@`` sign somewhere else.
  [maurits]

- Fixed error "local variable 'AUTHORIZATION' referenced before
  assignment" when not using basic authentication
  (http://user:pw@example.com).
  [maurits]


1.0 (2011-05-04)
----------------

- Initial release
