#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2010 Sauce Labs Inc
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

import time
import saucerest

from twisted.internet import reactor

def heartbeat(name, key, base_url, tunnel_id, update_callback):
    sauce = saucerest.SauceClient(name, key, base_url)
    healthy = sauce.healthy_tunnel(tunnel_id)
    if healthy:
        reactor.callLater(5, heartbeat, name, key, base_url, tunnel_id, update_callback)
    else:
        tunnel_settings = sauce.get_tunnel(tunnel_id)
        if tunnel_settings.get('UserShutDown'):
                print "Tunnel shutting down on user request"
                return
        print "Tunnel is down, booting new tunnel"
        sauce.delete_tunnel(tunnel_id)
        building_tunnel = True
        while building_tunnel:
            new_tunnel = sauce.create_tunnel({'DomainNames': tunnel_settings['DomainNames']})
            while 'error' in new_tunnel:
                #if tunnels die when you try to create them (flakey tunnels)
                print "Error: %s" % new_tunnel['error']
                time.sleep(5)
                new_tunnel = sauce.create_tunnel({'DomainNames': tunnel_settings['DomainNames']})
            try:
                interval = 5
                timeout = 600
                t = 0
                last_st = ""
                while t < timeout:
                    #wait for tunnel to be useable
                    tunnel = sauce.get_tunnel(new_tunnel['id'])
                    if tunnel['Status'] != last_st:
                        last_st = tunnel['Status']
                        print "Status: %s" % tunnel['Status']
                    if tunnel['Status'] == 'terminated':
                        #if the tunnel flakes out
                        sauce.delete_tunnel(new_tunnel['id'])
                        break
                    if tunnel['Status'] == 'running':
                        building_tunnel = False
                        break
                    time.sleep(interval)
                    t += interval
                else:
                    raise Exception("Timed out")
            finally:
                print "replacement aborted -- shutting down replacement tunnel machine"
                sauce.delete_tunnel(new_tunnel['id'])

        if update_callback:
            new_tunnel = sauce.get_tunnel(new_tunnel['id'])
            update_callback(new_tunnel)
