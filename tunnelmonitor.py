import time
import saucerest

from twisted.internet import reactor

def heartbeat(name, key, base_url, tunnel_id, update_callback):
    sauce = saucerest.SauceClient(name, key, base_url)
    healthy = sauce.healthy_tunnel(tunnel_id)
    if healthy: 
        reactor.callLater(5, heartbeat, name, key, base_url, tunnel_id, update_callback)
    if not healthy:
        print "Tunnel is down, booting new tunnel"
        tunnel_settings = sauce.get_tunnel(tunnel_id)
        sauce.delete_tunnel(tunnel_id)
        building_tunnel = True
        while building_tunnel: 
            new_tunnel = sauce.create_tunnel({'DomainNames': tunnel_settings['DomainNames']})
            while 'error' in new_tunnel:
                #if tunnels die when you try to create them (flakey tunnels)
                print "Error: %s" % new_tunnel['error']
                time.sleep(5)
                new_tunnel = sauce.create_tunnel({'DomainNames': tunnel_settings['DomainNames']})
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
        if update_callback:
            new_tunnel = sauce.get_tunnel(new_tunnel['id'])
            update_callback(new_tunnel)

def start_monitor():
    reactor.run()
