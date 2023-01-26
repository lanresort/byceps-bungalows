==========================
LANresort Bungalows System
==========================

For our LANresort_ events, which are LAN parties in holiday village
bungalows, we use a custom system that implements bungalow-based
reservations.

This repository contains code that extends the BYCEPS_ LAN party
platform to provide said system, both as a user frontend and as an admin
UI to manage bungalow offerings and reservations.

Development on the bungalows system started in 2014. It has been
open-sourced in 2023 to serve as an example of how a larger extension to
BYCEPS can look like.

.. _LANresort: https://www.lanresort.de/
.. _BYCEPS: https://byceps.nwsnet.de/


Installation
============

To integrate this with BYCEPS:

- Drop the code into a BYCEPS installation.
- Register the blueprints (in ``byceps/blueprints/blueprints.py``):

  - site blueprint: ``site.bungalow`` to URL path ``/bungalows``

  - admin blueprint: ``admin.bungalow`` to URL path ``/admin/bungalows``

- Link to those URL paths in your party website's and the admin UI's
  respective navigations.


Author
======

The bungalows system was created, and is developed and maintained, by
Jochen Kupperschmidt.


License
=======

The bungalows system is licensed under the `BSD 3-Clause "New" or
"Revised" License <https://choosealicense.com/licenses/bsd-3-clause/>`_.

The license text is provided in the `LICENSE <LICENSE>`_ file.
