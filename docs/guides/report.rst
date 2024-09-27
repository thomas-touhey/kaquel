.. _issue-reporting-guide:

Reporting a bug or vulnerability
================================

If you have identified that the module does not work properly, this guide is
here to help you identify the steps in reporting the issue properly for it
to be fixed, or in some cases, at least publicly documented.

Writing a bug or vulnerability report
-------------------------------------

The report MUST include the following information:

* System and system version on which the issue occurs; e.g. Debian 14,
  Ubuntu 22.04 LTS, Windows 11 Pro, ...
* Module version (e.g. 0.1, 1.2, ...).

Then, you must indicate the steps to reproduce the issue, including a
`minimal, reproducible example`_ using the library.

It is important that you respect the exact order in which you execute every
action, since this may be the source of the issue.

Sending your bug or vulnerability report
----------------------------------------

If your issue has security implications, e.g. if it allows a malicious
device to access the host and/or execute arbitrary code without authorisation,
please send an e-mail to Thomas Touhey at <thomas+kaquel@touhey.fr>.

.. note::

    Please only use this e-mail address if there is security implications
    to your demand. If you are not sure if your issue qualifies or not,
    send it anyway; use your best judgment.

For all other issues, you can create an issue on the `issue tracker at
Gitlab`_.

.. warning::

    Once your issue is up or sent, **please check on it every few days at
    least, or leave a way for the maintainers to contact you without
    giving up their privacy** (i.e. no phone numbers, social network
    profile or instant messaging address); an e-mail address is fine.

    An issue reported by someone who can't answer once additional details
    are required from them is an issue that gets closed and has wasted
    everyone's time and efforts.

.. warning::

    For any type of issue, due to the fact that this project is free software
    maintained by people on their free time, there is no guarantee of any
    delay, or even of a response or that the issue won't be closed due to
    lack of availability on the maintainers' part.

    Note however that this warning is worst case scenario, and hopefully,
    it won't come to that for any correctly reported issue.

.. _Issue tracker at Gitlab:
    https://gitlab.com/kaquel/kaquel/-/issues
.. _Minimal, reproducible example:
    https://stackoverflow.com/help/minimal-reproducible-example
