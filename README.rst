==========================================
Postgresql search handler for Django-Oscar
==========================================

Careful: This is originally created inside a project not tested in a reusable environment, yet.

This creates a search handler without the need of any search backend.
It is designed for the e-commerce framework `Oscar`_.

.. _`Oscar`: https://github.com/django-oscar/django-oscar


It is implemented a little bit expensive but uses 4 annotated search vectors:
* upc
* title
* meta_description
* meta_title

This way the search can be manipulated through the meta fields.
This package is not testet against generic sites, yet.
It is running productive in a heavily customized env for many months now.
I think it should scale up to 5000 Products with 10 Attributes depending on how the products are loaded.
We use it fully lazy with endless scrolling.


To-Do
-----
* Dynamic creation of the filter fields
* Writing Tests


Features
--------

* Don't need to use some additional search backend like elastic
* Creates filters (facets) for:
	* Data that is directly attached to the Product model including foreign key choices
	* AttributeValues of the products
	* StockRecord entries


Installation
------------

Install using pip:

.. code-block:: bash

	pip install django-oscar-pg-search


.. code-block:: python

   # settings.py
   INSTALLED_APPS = [
       # ...
       'oscar_pg_search.apps.PgSearchConfig',
       # ...
   ]
   OSCAR_PRODUCT_SEARCH_HANDLER = 'oscar_pg_search.postgres_search_handler.PostgresSearchHandler'

Settings
--------

If you want to add some fields that are directly attached to the Product model:

.. code-block:: python

   # settings.py
   OSCAR_ATTACHED_PRODUCT_FIELDS = ['is_public', 'deposit', 'volume', 'weight',]
