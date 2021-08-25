==========================================
Welcome to jntajis-python's documentation!
==========================================

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: API reference

   /api

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: License

   /license

What is JNTAJIS?
================

.. image:: https://www.houjin-bangou.nta.go.jp/download/images/moji-code.jpg

--------
Synopsis
--------

.. code-block:: python

    import jntajis
    
    print(jntajis.jnta_shrink_translit("麴町"))  # outputs "麹町"
    print(jntajis.mj_shrink_candidates("髙島屋"))  # outputs ["高島屋", "髙島屋"]


---------
Reference
---------

* :doc:`API reference </api>`

-------
License
-------

* :doc:`License </license>`
