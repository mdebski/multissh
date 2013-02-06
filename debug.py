"""Some functions making debug output consistent"""

debugLevel=0 # Default debug level

from sys import stdout

# Using sys.stdout.write for thread safety.
def mesgDebug(s):
 if(debugLevel>3): stdout.write(s + "\n")
def mesgInfo(s):
 if(debugLevel>2): stdout.write(s + "\n")
def mesgWarn(s):
 if(debugLevel>1): stdout.write(s + "\n")
def mesgErr(s):
 if(debugLevel>0): stdout.write(s + "\n")

