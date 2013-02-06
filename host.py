import paramiko

import debug

class NotInteractive(Exception):
 pass

class Host:
 """Class containing host to connect to, along with open session"""
 def __init__(self, id, host, username, password):
  self.id, self.host, self.username, self.password = id, host, username, password
  self.id=id
  self.session = paramiko.SSHClient()
  self.session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  self.status = 1
  self.channel = None # Used in interactive
  self.lastOk = False
 def __str__(self):
  return "%s:	%s@%s	(%s)" % (self.id, self.username, self.host, "Connected" if self.connected() else "Disconnected")
 def connect(self):
  debug.mesgDebug("Connecting to %s... " % self.host)
  try:
   self.session.connect(self.host, username=self.username, password=self.password, timeout=20)
   debug.mesgInfo("Connection to %s successful!" % self.host)
   self.status = 0
  except:  
   debug.mesgWarn("FAILED: %s" % self.host)
 def disconnect(self):
  if(self.connected()):
   self.session.close()
   self.status=1
 def connected(self):
  return (self.status==0 and self.session)
 def execute(self, command):
  """ Execute single command. Return: true-> ok, false-> error"""
  sshin, sshout, ssherr = self.session.exec_command(command)
  sshoutdata = sshout.readlines()
  ssherrdata = ssherr.readlines() 
  for line in sshoutdata: debug.mesgWarn(line[:-1])
  if(len(ssherrdata) != 0): debug.mesgErr("Host %s error: " % self.host)
  for line in ssherrdata: debug.mesgErr(" "+line[:-1])
  self.lastOk = not ssherrdata
 def lastStatus(self):
  return self.connected() and self.lastOk
 def isInteractive(self):
  return (self.channel and (not self.channel.closed))
 def interactiveStart(self):
  self.channel = self.session.invoke_shell(term='xterm')
  self.channel.settimeout(0.0)
 def interactiveStop(self):
  self.channel = None

def printHostsStatus(hosts):
 good = len([h.lastStatus() for h in hosts if h.lastStatus()])
 bad = len([h.lastStatus() for h in hosts if not h.lastStatus()])
 if(not bad): debug.mesgInfo("All %d hosts OK." % good)
 else: debug.mesgErr("%d hosts OK, %d hosts failed." % (good,bad))
