tsquare - Georgia Tech TSquare API
===================

TSquare is a fork of Sakai's student management system. While it has a
REST API, it is unfortunately somewhat lacking. This module was created
initially to give a Django web app a viable interface to TSquare - that
project is still under develpment at swgillespie/tsquare-webapp .

Many thanks to Nirav Bhatia and Cameron Guthrie for their help and insight
in developing this API!

Installation
--------------

To install, clone this repository and run
```
python setup.py install
```
voila! You can also install this via pip:

```
pip install tsquare
```

Example
---------------
```
>>> from tsquare.core import TSquareAPI
>>> api = TSquareAPI('myusername', 'mypassword')
>>> user_sites = api.get_sites()
>>> print user_sites[0].description
u'Barcelona Architecture'
>>> print api.get_announcements(user_sites[0], num=10, age=360)
[] # unfortunately this class I picked has no announcements ;)
```
Full documentation is on the to-do list. You can see example usage in the unit tests.


Future directions
-------------------
I will continue developing this API by taking stories from the above
repo's sprint backlog.





