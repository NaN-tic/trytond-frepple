Installing frePPLe from sources
===============================

Using a stable release
----------------------

$ tar xvf frepple.tgz
$ cd frepple
$ ./configure
$ make -j 2


Using unstable release or from git repository
---------------------------------------------

$ sudo apt-get install libtool automake autoconf
$ sudo pip install django
$ tar xvf frepple.tgz
$ cd frepple
$ cp /usr/share/libtool/config/ltmain.sh .
$ automake --add-misssing
$ autoreconf
$ ./configure
$ make -j 2

django interface
----------------

$ sudo pip install cherrypy
$ cd contrib/django

Using sqlite:

$ ./frepplectl.py syncdb
$ ./frepplectl.py frepple_runserver

Using PostgreSQL:

- Edit djangosettings.py:

      'default': {
              'ENGINE': 'django.db.backends.postgresql_psycopg2',
              'NAME': 'frepple',
              'USER': '',     # If empty 'frepple' will be used
              'PASSWORD': '',
              'HOST': '',     # Set to empty string for localhost. Not used with sqlite3.
              'OPTIONS': {},  # Backend specific configuration parameters.
              'PORT': '',     # Set to empty string for default. Not used with sqlite3.
              },

$ createdb frepple
$ ./frepplectl.py syncdb
$ ./frepplectl.py frepple_runserver



$ xdg-open http://127.0.1.1:8000

From the user interface "Admin / Execute" -> "Empty the database"

frePPLe - Tryton integration
============================

For the integration to work you'll have to download frePPLe from sources and
compile it. There are currently some patches to apply for things to work.

Although it is not required for the planning itself it is necessary for seeing
the reports to following these steps: From the frePPLe user interface go to
"Admin / Execute" -> "Generate buckets". You should give it reasonable start
and end dates and then push "Launch". Afterwards you'll be able to see the
reports for the latest simulation or you can run the simulation again.

Technical Details
=================

frePPLe has a very good python integration but it requires to execute the
frepple binary and pass the python file as a parameter. That's what the frepple
module for tryton does. It executes the frepple binary looking for it in the
path the user has configured it from the GUI and passes the 'frepple-tryton.py'
script as a parameter.

The module also tries to ensure that the binary libraries of frepple are
available by initializing the LD_LIBRARY_PATH=. and changing the current
directory where the frepple binary is before running it. It also adds the
required django contrib libraries frepple distribution to the PYTHONPATH
environment variable.

frePPLe and Tryton have very different data structures. frePPLe tries to be very
simple and flexible so it can be adapted to many scenarios. That means that one
Tryton object is usually converted into two, three or more objects in the
frePPLe world. All this conversion happens in the 'frepple-tryton.py' script.

frePPLe does almost everyting with just three classes:

- Operation: which is not a running operation but more (though not exactly) a
  BOM. An Operation is a rule that the engine can use to produce a product that
  is needed.
- Buffer: Buffer is the combination of a location and a product.
- Flow: A flow links a buffer and an operation together. Two buffers cannot be
  connected together directly and neither can operations be connected between
  them.

There are also some other important classes:

- Demand: which models the demand of a product by a customer
- Other classes which we're still not using for planning capacities

frePPLe has pretty good documentation and it is a good thing to have a look at
it. It is also good to take a look at frepple-tryton.py to see how both objects
of both systems are related.


Troubleshooting
===============


- Not filling in the "size_multiple" field in "operations" can result in an
  infinte loop and eventually a segmentation fault because the field is 0 by
  default.

- If USER is empty in djangosettings.py, the django interface may still be able to
  read stuff from the database but not writing, so take care.

- Buckets need to be created for the reports (inventory, etc) to work. See:
  https://groups.google.com/forum/#!topic/frepple-users/5UiUOnGCSw4
