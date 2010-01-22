SauceREST for Python
====================

This is a Python library and some command line tools for interacting
with the SauceREST API.

Here are some useful command line tools:

tunnel.py
---------

This script is used to set up tunnel machines and open the tunnel from
your side. Run it with "-h" to get the parameters required. Example
run:

    $ python tunnel.py username api-key localhost 5000:80 exampleurl.com

This will make our computers masquerade exampleurl.com on port 80
through the tunnel you're about to open.


list_tunnels.py
---------------

Lists all the available tunnels for the user account given. Example run:

    $ python list_tunnels.py username api-key


close_tunnels.py
----------------

By this time you should know what this script does :). Example run:

    $ close_tunnel.py username access-key 234kj23l4k2j34k2lk234k3k3


saucerest.py
------------

This is a basic library for working with the SauceREST API.  If you
plan to write scripts that work with SauceREST in Python,
`saucerest.py` might be a good place to start.


daemon.py, sshtunnel.py
-----------------------

These provide useful commands the scripts above use, so you need to
keep them in the same folder.