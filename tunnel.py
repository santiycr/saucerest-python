#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Sauce Labs Inc
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# 'Software'), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import time
import signal
import saucerest
import sshtunnel
import daemon

from optparse import OptionParser

usage = "usage: %prog [options] <username> <access key> <local host> <local \
port>:<remote port>[,<local port>:<remote port>] <remote domain>[,<remote \
domain>...]"
op = OptionParser(usage=usage)
op.add_option("-d",
              "--daemonize",
              action="store_true",
              dest="daemonize",
              default=False,
              help="background the process once the tunnel is established")
op.add_option("-p",
              "--pidfile",
              dest="pidfile",
              default="tunnel.pid",
              help="when used with --daemonize, write backgrounded Process ID \
to FILE [default: %default]",
              metavar="FILE")
op.add_option("-r",
              "--readyfile",
              dest="readyfile",
              default=False,
              help="create FILE when the tunnel is ready",
              metavar="FILE")
op.add_option("-s",
              "--shutdown",
              action="store_true",
              dest="shutdown",
              default=False,
              help="shutdown any existing tunnel machines using one or more \
requested domain names")
op.add_option("--diagnostic",
              action="store_true",
              dest="diagnostic",
              default=False,
              help="using this option, we will run a set of tests to make sure\
 the arguments given are correct. If all works, will open the tunnels in debug\
 mode")
op.add_option("-b", "--baseurl",
              dest="base_url",
              default="https://saucelabs.com",
              help="use an alternate base URL for the saucelabs service")

(options, args) = op.parse_args()

num_missing = 5 - len(args)
if num_missing > 0:
    op.error("missing %d required argument(s)" % num_missing)

username = args[0]
access_key = args[1]
local_host = args[2]
ports = []
for pair in args[3].split(","):
    if ":" not in pair:
        op.error("incorrect port syntax: %s" % pair)
    ports.append([int(port) for port in pair.split(":", 1)])
domains = ",".join(args[4:]).split(",")

if options.diagnostic:
    errors = []
    # Checking domains to forward
    import re
    for domain in domains:
        if not re.search("^([\\da-z\\.-]+)\\.([a-z\\.]{2,8})$", domain):
            errors.append("Incorrect domain given: %s" % domain)

    # Checking if host is accessible
    import socket
    for pair in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((local_host, pair[0]))
        except socket.gaierror:
            errors.append("Local host %s is not accessible" % local_host)
            break
        except socket.error, (_, port_error):
            errors.append("Problem connecting to %s:%s: %s" % (local_host,
                                                               pair[0],
                                                               port_error))

    if len(errors):
        print "Errors found:"
        for error in errors:
            print "\t%s" % error
        sys.exit(0)
    else:
        print "No errors found, proceeding"

sauce = saucerest.SauceClient(name=username, access_key=access_key,
                              base_url=options.base_url)

if sauce.get_tunnel("test-authorized")['error'] == 'Unauthorized':
    print "Error: User/access-key combination is incorrect"
    sys.exit(0)

if options.shutdown:
    print "Searching for existing tunnels using requested domains..."
    tunnels = sauce.list_tunnels()
    for tunnel in tunnels:
        for domain in domains:
            if domain in tunnel['DomainNames']:
                print "tunnel %s is currenty using requested domain %s" % (
                    tunnel['_id'],
                    domain)
                print "shutting down tunnel %s" % tunnel['_id']
                sauce.delete_tunnel(tunnel['_id'])


print "Launching tunnel machine..."
response = sauce.create_tunnel({'DomainNames': domains})
if 'error' in response:
    print "Error: %s" % response['error']
    sys.exit(0)
tunnel_id = response['id']
print "Tunnel ID: %s" % tunnel_id


try:
    interval = 5
    timeout = 600
    t = 0
    last_st = ""
    while t < timeout:
        tunnel = sauce.get_tunnel(tunnel_id)
        if tunnel['Status'] != last_st:
            last_st = tunnel['Status']
            print "Status: %s" % tunnel['Status']
        if tunnel['Status'] == 'running':
            break
        time.sleep(interval)
        t += interval
    else:
        raise Exception("Timed out")

    def shutdown_callback():
        sauce.delete_tunnel(tunnel_id)

    def tunnel_change_callback(new_tunnel):
        print "New tunnel:"
        print new_tunnel
        global tunnel_id
        tunnel_id = new_tunnel['id']
        print "New tunnel ID: %s" % tunnel_id
        connect_to_tunnel()

    drop_readyfile = None
    if options.readyfile:

        def d():
            open(options.readyfile, 'wb').write("ready")
        drop_readyfile = d

    connected_callback = None
    if options.daemonize:

        def daemonize():
            daemon.daemonize(options.pidfile)
            if drop_readyfile:
                drop_readyfile()
        connected_callback = daemonize
    elif drop_readyfile:
        connected_callback = drop_readyfile

    def tunnel_change_callback(new_tunnel):
        global tunnel_id
        global options
        drop_readyfile = None
        if options.readyfile:

            def d():
                open(options.readyfile, 'wb').write("ready")
        connected_callback = None
        if options.daemonize:

            def daemonize():
                daemon.daemonize(options.pidfile)
                if drop_readyfile:
                    drop_readyfile()
            connected_callback = daemonize
        elif drop_readyfile:
            connected_callback = drop_readyfile

        print "New tunnel:"
        print new_tunnel
        tunnel_id = new_tunnel['id']
        print "New tunnel ID: %s" % tunnel_id
        sshtunnel.tunnel_setup(tunnel_id,
                               sauce.base_url,
                               username,
                               access_key,
                               local_host,
                               tunnel['Host'],
                               ports,
                               connected_callback,
                               tunnel_change_callback,
                               shutdown_callback(tunnel_id),
                               options.diagnostic)

    sshtunnel.connect_tunnel(tunnel_id,
                               sauce.base_url,
                               username,
                               access_key,
                               local_host,
                               tunnel['Host'],
                               ports,
                               connected_callback,
                               tunnel_change_callback,
                               shutdown_callback,
                               options.diagnostic)

finally:
    print "Aborted -- shutting down tunnel machine"
    sauce.delete_tunnel(tunnel_id)
