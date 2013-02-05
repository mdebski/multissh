#!/usr/bin/env python

import os
import re
import sys
import time
import socket
import select
import getpass
import argparse
import paramiko
import threading
import tty, termios

import host
import debug
import iputils

specialHelp="""
Entering an command starting with '@' may have special meaning:

@? or @help		display help
@list			list connected hosts
@-ID or @drop ID	disconnect and remove from list host with specified ID
@-- 			drop all disconnected hosts
@ID command		execute command only on host with specified ID
@i 			enter interactive mode (CAUTION: get to know how it works first)
@{} command		execute command substituting {ID} with id, {IP} with ip, {USER} with user, NOT substituting {PASS} with password :P
@scp local remote	copy file to all hosts
@n			exit interactive mode
@@			input @

In interactive mode only @?,@n,@@ does anything
"""

parser = argparse.ArgumentParser(description="""Connect via ssh to numerous hosts as to one. Use @? for help on special commands.""", epilog="""Host specification may be hostname, IP address, subnet in CIDR notation, or range (myhost1-5). Usage of '@', like in root@myhost, is not supported, sorry""")
parser.add_argument('hosts', type=str, nargs='*', help='List of space separated hosts')
parser.add_argument('--file', '-f', help="""Read hosts from file. (one per line: "host user password")""")
parser.add_argument('--command', '-c', help='Execute just this command and exit.')
parser.add_argument('--debug', '-d', default="3", help='Debug level from 0 to 4 (highest)')
parser.add_argument('--pool', '-p', default="20", help='Use up to that much threads for connecting and parallel execution.')
parser.add_argument('--username', '-U', help='Username for all hosts')
parser.add_argument('--password', '-P', help='Password for all hosts')
parser.add_argument('--hex', '-x', default=False, action="store_true", help='Interpret ranges as hex numbers')
args = parser.parse_args()

debug.debugLevel=int(args.debug)

# Hosts descriptions interpretation

hosts=[]

if(args.file): # Reading from file
 try: f=open(args.file, 'r')
 except: debug.mesgErr("Cannot open file %s" % args.file)
 for line in f:
  l=re.split('\s', line)
  for h in iputils.parseHostSpec(l[0], args.hex):
   hosts+=[host.Host(len(hosts), h, l[1], l[2])]
  
if(args.hosts): # Reading from cmdline
 if(not args.username):
  args.username=raw_input("Username: ")
 if(not args.password):
  args.password=getpass.getpass("Password: ")
 for s in args.hosts:
  for h in iputils.parseHostSpec(s, args.hex):
   hosts+=[host.Host(len(hosts), h, args.username, args.password)]

if(not hosts):
 debug.mesgErr("No host specified!")
 sys.exit(1)

# Connecting paralelly.

inPool=0
mutex=threading.Lock()
cEmpty=threading.Condition(mutex)
cNotFull=threading.Condition(mutex)

def threadWrapper(f):
 global inPool
 f()
 mutex.acquire()
 inPool-=1
 if(inPool<args.pool): cNotFull.notify()
 if(inPool==0): cEmpty.notify()
 mutex.release()

for h in hosts:
 cNotFull.acquire()
 while(inPool>=args.pool): cNotFull.wait()
 inPool+=1
 cNotFull.release()
 threading.Thread(target=threadWrapper, args=(lambda: h.connect(),)).start()

cEmpty.acquire()
while(inPool != 0): cEmpty.wait()
cEmpty.release()

debug.mesgInfo("Finished connecting.")

if(args.command): # Just single command
 host.allExecute(hosts, args.command) 
 sys.exit(0)

def startInteractive():
 if(not hosts[0].connected()):
  debug.mesgWarn("Can't start interactive, as first host is not connected!")
  return
 global interactive,locchar,oldSettings
 locchar='\n'
 interactive=True
 oldSettings = termios.tcgetattr(sys.stdin.fileno())
 tty.setraw(sys.stdin.fileno())
 tty.setcbreak(sys.stdin.fileno())
 for h in hosts: 
  if(h.connected()): h.interactiveStart()

def stopInteractive():
 global interactive
 interactive=False
 termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, oldSettings)
 for h in hosts: h.interactiveStop()

# Special interpretation

def parseSpecial(spec):
 """Parses special command (string after @) and returns command or char to be used instead, or None if none"""
 global hosts
 if(re.search("^(\?|help)\s*$",spec)): # @?, @help
  sys.stdout.write(str(specialHelp))
  sys.stdout.flush()
  return None
 if(re.search("^@\s*$",spec)): return '@' # @@
 if(re.search("^n\s*$",spec)): # @n
  stopInteractive()
  return None
 if(interactive): return spec
 if(re.search("^i\s*$",spec)): startInteractive() #i
 if(re.search("^list\s*$",spec)): # @list
  good, bad = 0,0
  for h in hosts:
   print h
   if(h.connected()): good+=1
   else: bad+=1
  print "Connected: %d, disconnected: %d" % (good,bad)
 m=re.search("^(-|drop )(\d+)\s*$",spec) # @-, @drop
 if(m):
  debug.mesgInfo("Dropping %d..." % int(m.group(2)))
  for h in hosts:
   if(h.id==int(m.group(2))): h.disconnect()
  hosts=filter((lambda h: h.id!=int(m.group(2))), hosts)
 m=re.search("^--\s*$",spec) # @--
 if(m):
  hosts=filter((lambda h: h.connected()), hosts)
 m=re.search("^(\d+) (.*)\s*$",spec) # @1
 if(m):
  for h in hosts:
   if(h.id==int(m.group(1))):
    if(h.connected() and h.execute(m.group(2))):
     debug.mesgInfo("Host %d OK." % h.id)
    else: 
     debug.mesgErr("Host %d FAILED." % h.id)
 m=re.search("^{} (.*)\s*$",spec) # @{}
 if(m):
  good, bad = 0, 0
  for h in hosts:
   cmd=m.group(1)
   cmd=re.sub('{ID}', str(h.id), cmd)
   cmd=re.sub('{USER}', str(h.username), cmd)
   cmd=re.sub('{IP}', str(h.host), cmd)
   if(h.connected() and h.execute(cmd)): good+=1
   else: bad+=1
  if(not bad): debug.mesgWarn("All %d hosts OK." % good)
  else: debug.mesgErr("%d hosts OK, %d hosts failed." % (good,bad))
 m=re.search("^scp (\S*) (\S*)\s*$",spec) # @scp
 if(m): debug.mesgErr("Not implemepted yet :(")
 return None

# Main loop

interactive=False

try:
 while True:
  if(interactive):
   r, w, e = select.select([hosts[0].channel, sys.stdin], [], [])
   if hosts[0].channel in r:
    try:
     remchar=hosts[0].channel.recv(1024)
     if(not remchar):
      debug.mesgErr("Error occurred while in interactive mode, dropping to normal")
      stopInteractive()
     sys.stdout.write(remchar)
     sys.stdout.flush()
    except socket.timeout: pass
   if sys.stdin in r:
    prevlocchar=locchar
    locchar=os.read(sys.stdin.fileno(),1)
    if(not locchar):
     debug.mesgErr("Error occurred while in interactive mode, dropping to normal")
     stopInteractive()
    if((prevlocchar=='\n' or prevlocchar=='\r') and locchar=='@'):
     locchar=os.read(sys.stdin.fileno(),1)
     locchar=parseSpecial(locchar)
    if(locchar):
     for h in hosts:
      if(h.isInteractive()): h.channel.send(locchar)
  else:
   command=raw_input("multissh# ")
   if(re.search('^@', command)):
    command=parseSpecial(command[1:])
   if(command):
    host.allExecute(hosts, command)
except (KeyboardInterrupt, EOFError):
 if(interactive): stopInteractive()
 for h in hosts:
  h.disconnect()
 print ""
 sys.exit(1)
