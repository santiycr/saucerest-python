#! /usr/bin/python
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

import struct, sys, os

from twisted.conch.ssh import transport, userauth, connection, common, keys, channel, forwarding
from twisted.internet import defer, protocol, reactor

class TunnelTransport(transport.SSHClientTransport):
  def __init__(self, user, password, forward_host, forward_port, forward_remote_port, connected_callback=None):
    try:
      transport.SSHClientTransport.__init__(self)
    except AttributeError:
      pass
    self.user = user
    self.password = password
    self.forward_host = forward_host
    self.forward_port = forward_port
    self.forward_remote_port = forward_remote_port
    self.connected_callback = connected_callback

  def verifyHostKey(self, hostKey, fingerprint):
    return defer.succeed(1)

  def connectionSecure(self):
    self.requestService(
      TunnelUserAuth(self.user,
                     TunnelConnection(self.forward_host,
                                      self.forward_port,
                                      self.forward_remote_port,
                                      self.connected_callback),
                     self.password))

class TunnelUserAuth(userauth.SSHUserAuthClient):
  def __init__(self, user, connection, password):
    userauth.SSHUserAuthClient.__init__(self, user, connection)
    self.password = password

  def getPassword(self):
    return defer.succeed(self.password)

  def getGenericAnswers(self, name, instruction, questions):
    print "name:", name
    print "instruction:", instruction
    print "questions:", questions
    answers = []
    for prompt, echo in questions:
      answer = self.password
      answers.append(answer)
    return defer.succeed(answers)

    def getPublicKey(self):
        return

    def getPrivateKey(self):
        return

class TunnelConnection(connection.SSHConnection):
  def __init__(self, forward_host, forward_port, forward_remote_port, connected_callback=None):
    try:
      connection.SSHConnection.__init__(self)
    except AttributeError:
      pass

    self.forward_host = forward_host
    self.forward_port = forward_port
    self.forward_remote_port = forward_remote_port
    self.connected_callback = connected_callback

  def serviceStarted(self):
    self.remoteForwards = {}
    self.requestRemoteForwarding(self.forward_remote_port, (self.forward_host, self.forward_port))
    self.openChannel(NullChannel())

  def requestRemoteForwarding(self, remotePort, hostport):
    data = forwarding.packGlobal_tcpip_forward(('0.0.0.0', remotePort))
    d = self.sendGlobalRequest('tcpip-forward', data,
                               wantReply=1)
    print('requesting remote forwarding %s:%s' %(remotePort, hostport))
    d.addCallback(self._cbRemoteForwarding, remotePort, hostport)
    d.addErrback(self._ebRemoteForwarding, remotePort, hostport)

  def _cbRemoteForwarding(self, result, remotePort, hostport):
    print('accepted remote forwarding %s:%s' % (remotePort, hostport))
    self.remoteForwards[remotePort] = hostport
    if self.connected_callback:
      self.connected_callback()

  def _ebRemoteForwarding(self, f, remotePort, hostport):
    print('remote forwarding %s:%s failed' % (remotePort, hostport))
    print(f)

  def cancelRemoteForwarding(self, remotePort):
    data = forwarding.packGlobal_tcpip_forward(('0.0.0.0', remotePort))
    self.sendGlobalRequest('cancel-tcpip-forward', data)
    print('cancelling remote forwarding %s' % remotePort)
    try:
      del self.remoteForwards[remotePort]
    except:
      pass

  def channel_forwarded_tcpip(self, windowSize, maxPacket, data):
    print('%s %s' % ('FTCP', repr(data)))
    remoteHP, origHP = forwarding.unpackOpen_forwarded_tcpip(data)
    print(remoteHP)
    if self.remoteForwards.has_key(remoteHP[1]):
      connectHP = self.remoteForwards[remoteHP[1]]
      print('connect forwarding %s' % (connectHP,))
      return forwarding.SSHConnectForwardingChannel(connectHP,
                                                    remoteWindow = windowSize,
                                                    remoteMaxPacket = maxPacket,
                                                    conn = self)
    else:
      raise ConchError(connection.OPEN_CONNECT_FAILED, "don't know about that port")

  def channelClosed(self, channel):
    print('connection closing %s' % channel)
    print(self.channels)
    if len(self.channels) == 1: # just us left
      print('stopping connection')
      try:
          reactor.stop()
      except:
          pass
    else:
      # because of the unix thing
      self.__class__.__bases__[0].channelClosed(self, channel)


class NullChannel(channel.SSHChannel):
  name = 'session'

  def openFailed(self, reason):
    print 'NullChannel open failed', reason

  def channelOpen(self, ignoredData):
    return

  def closeReceived(self):
    print('remote side closed %s' % self)
    self.conn.sendClose(self)

  def closed(self):
    global old
    print('closed %s' % self)
    print(repr(self.conn.channels))


def connect_tunnel(username, access_key, local_port, local_host, remote_port, remote_host, connected_callback=None):
  d = protocol.ClientCreator(reactor, TunnelTransport, username, access_key, local_host, local_port, remote_port, connected_callback).connectTCP(remote_host, 22)
  reactor.run()
