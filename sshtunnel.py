import struct, sys, getpass, os

from twisted.conch.ssh import transport, userauth, connection, common, keys, channel, forwarding
from twisted.internet import defer, protocol, reactor

class TunnelTransport(transport.SSHClientTransport):
  def __init__(self, user, password, forward_host, forward_port, forward_remote_port):
    try:
      transport.SSHClientTransport.__init__(self)
    except AttributeError:
      pass
    self.user = user
    self.password = password
    self.forward_host = forward_host
    self.forward_port = forward_port
    self.forward_remote_port = forward_remote_port

  def verifyHostKey(self, hostKey, fingerprint):
    print 'host key fingerprint: %s' % fingerprint
    return defer.succeed(1)

  def connectionSecure(self):
    self.requestService(
      TunnelUserAuth(self.user,
                     TunnelConnection(self.forward_host,
                                      self.forward_port,
                                      self.forward_remote_port),
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
  def __init__(self, forward_host, forward_port, forward_remote_port):
    try:
      connection.SSHConnection.__init__(self)
    except AttributeError:
      pass

    self.forward_host = forward_host
    self.forward_port = forward_port
    self.forward_remote_port = forward_remote_port

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
    print(repr(self.remoteForwards))

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
    print(repr(self.remoteForwards))

  def channel_forwarded_tcpip(self, windowSize, maxPacket, data):
    print('%s %s' % ('FTCP', repr(data)))
    remoteHP, origHP = forwarding.unpackOpen_forwarded_tcpip(data)
    print(self.remoteForwards)
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
    print 'echo failed', reason

  def channelOpen(self, ignoredData):
    return

  def closeReceived(self):
    print('remote side closed %s' % self)
    self.conn.sendClose(self)

  def closed(self):
    global old
    print('closed %s' % self)
    print(repr(self.conn.channels))


def connect_tunnel(username, access_key, local_port, local_host, remote_port, remote_host):
  protocol.ClientCreator(reactor, TunnelTransport, username, access_key, local_host, local_port, remote_port).connectTCP(remote_host, 22)
  reactor.run()
