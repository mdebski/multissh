""" Some utils to deal with ip addresses"""

import re
import socket

import debug

def ipToInt(s):
 """Converts string representing IP Address to 32bit int"""
 m = re.search('\b?(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b?', s)
 if(not m): return -1
 try:
  a,b,c,d = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
 except:
  return -1
 if(a>255 or a<0 or b>255 or b<0 or c>255 or c<0 or d>255 or d<0):
  return -1
 return (a<<24)|(b<<16)|(c<<8)|d

def intToIp(i):
 """Converts 32bit int to string representing IP Address"""
 return "%d.%d.%d.%d" % ((i>>24)%256, (i>>16)%256, (i>>8)%256, i%256)

def isIp(s):
 """Checks if string describes valid IP Address"""
 return (ipToInt(s) != -1)

def cidr(net, mask):
 """Generates list of IP Addresses belonging to network given as IP and mask (0-32)"""
 list=[]
 hostmask = ((1<<(32-mask))-1)
 netmask = (((1<<32)-1)^hostmask)
 for ip in range(net&netmask, (net|hostmask)+1):
  list+=[intToIp(ip)]
 return list

def parseHostSpec(s, hexadecim=False):
 """Interpretes string as host(s) specification, returning list of IP addresses.
    Takes care of:
     CIDR notation (10.1.1.0/24, myhosts-net/27)
     hostname ranges (myhost00-10)
     ip ranges (10.1.1.4-8)
 """
 if(re.search('/', s)):
  m = re.split('/', s)
  net, mask = m[0], m[1]
  try: mask = int(mask)
  except: debug.mesgWarn("Invalid host specification (mask is not int): %s" % s); return []
  if(not isIp(net)):
   try: net=socket.gethostbyname(net)
   except: debug.mesgWarn("Invalid host specification (can't resolve hostname): %s" % s); return []
  if(not isIp(net) or mask>32 or mask<0):
   debug.mesgWarn("Invalid host specification (mask is not in <0,32>): %s" % s); return []
  return cidr(ipToInt(net), mask)
 elif(re.search('[0-9a-f]-[0-9a-f]', s)):
  if(hexadecim): m=re.search('(\d[0-9a-f]+)-([0-9a-f]+)', s)
  else: m=re.search('(\d+)-(\d+)', s)
  all, st, nd = m.group(0), m.group(1), m.group(2)
  ret=[]
  for i in range(int(m.group(1), 16 if(hexadecim) else 10), int(m.group(2), 16 if(hexadecim) else 10)+1):
   stri = ("%0"+str(len(m.group(1)))+("x" if(hexadecim) else "d")) % i
   h=re.sub(m.group(0), stri, s)
   if(not isIp(h)):
    try: h = socket.gethostbyname(h)
    except: debug.mesgWarn("Invalid host specification (can't resolve hostname): %s" % s); return []
   ret+=[h]
  return ret
 else:
  if(not isIp(s)):
   sp=""
   try: sp=socket.gethostbyname(s)
   except: debug.mesgWarn("Invalid host specification: %s" % s); return []
   s=sp
  return [s]
