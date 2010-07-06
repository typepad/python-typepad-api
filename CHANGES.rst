typepad Changelog
=================

2.0 (tbd)
---------

* Now thread-safe.
* The client endpoint now adapts to a http or https scheme automatically depending on whether it has been assigned credentials for requests.
* The typepad.api module is now generated (using 'generate.py') from the TypePad reflection APIs (this makes the library easier to maintain when API changes are released for TypePad). This made for some significant changes to the library (some classes were renamed in the process and many additional methods and endpoints are now supported).
* Support for the TypePad blog APIs.
* Support for the TypePad feed subscription APIs.


1.1.2 (2010-04-20)
------------------

* Added support for discovering errors with files uploaded through the browser upload endpoint.
* Fixed error logging warnings about deprecated methods.


1.1.1 (2010-03-30)
------------------

* Updates for forward compatibility with the TypePad API.


1.1 (2009-11-24)
----------------

* Additional documentation for typepad.api module.
* Added ``typepad.api.browser_upload`` for uploading photo or audio posts directly to a TypePad group.
* Changed requirement for OAuth package to 1.0.1.
* Support for custom 'callback' parameter for ``typepad.api.tpobject.get()`` method.


1.0 (2009-09-30)
----------------

* Initial release.
