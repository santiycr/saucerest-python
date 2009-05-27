import time
import saucerest
import sshtunnel

username = ""
access_key = ""
domains = ['www.1234.dev']
local_port = 5000
local_host = "localhost"
remote_port = 80

sauce = saucerest.SauceClient(name=username, access_key=access_key)

response = sauce.create_tunnel({'DomainNames': domains})
print response
tunnel_id = response['id']

try:
  interval = 10
  timeout = 600
  t = 0
  while t < timeout:
    tunnel = sauce.get_tunnel(tunnel_id)
    print tunnel
    if tunnel['Status'] == 'running':
      break

    print "sleeping..."
    time.sleep(interval)
    t += interval

  sshtunnel.connect_tunnel(username, access_key, local_port, local_host, remote_port, tunnel['Host'])
finally:
  print "Aborted -- shutting down tunnel"
  sauce.delete_tunnel(tunnel_id)
