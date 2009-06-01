#! /usr/bin/python
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

usage = "usage: %prog [options] <username> <access key> <local host> <local port> <remote port> <remote domain> [<remote domain>...]"
op = OptionParser(usage=usage)
op.add_option("-d", "--daemonize",
              action="store_true", dest="daemonize",
              help="background the process once the tunnel is established")
op.add_option("-p", "--pidfile", dest="pidfile",
              help="when used with --daemonize, write backgrounded Process ID to FILE [default: %default]", metavar="FILE")
op.add_option("-s", "--shutdown",
              action="store_true", dest="shutdown",
              help="shutdown any existing tunnel machines using one or more requested domain names")
op.set_defaults(daemonize=False)
op.set_defaults(pidfile="tunnel.pid")
op.set_defaults(shutdown=False)
(options, args) = op.parse_args()
num_missing = 6 - len(args)
if num_missing > 0:
  op.error("missing %d required argument(s)" % num_missing)

username = args[0]
access_key = args[1]
local_host = args[2]
local_port = int(args[3])
remote_port = int(args[4])
domains = args[5:]

sauce = saucerest.SauceClient(name=username, access_key=access_key)


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
  interval = 10
  timeout = 600
  t = 0
  while t < timeout:
    tunnel = sauce.get_tunnel(tunnel_id)
    print "Status: %s" % tunnel['Status']
    if tunnel['Status'] == 'running':
      break

    time.sleep(interval)
    t += interval


  connected_callback = None
  if options.daemonize:
    def handler(signum, frame):
      print "Aborted -- shutting down tunnel machine"
      sauce.delete_tunnel(tunnel_id)
      raise Exception("asked to die")

    def daemonize():
      daemon.daemonize(options.pidfile)
      signal.signal(signal.SIGINT, handler)
      signal.signal(signal.SIGTERM, handler)

    connected_callback = daemonize

  sshtunnel.connect_tunnel(username, access_key,
                           local_port, local_host, remote_port,
                           tunnel['Host'],
                           connected_callback)

finally:
  print "Aborted -- shutting down tunnel machine"
  sauce.delete_tunnel(tunnel_id)
