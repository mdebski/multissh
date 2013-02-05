"""Some functions making debug output consistent"""

debugLevel=0 # Default debug level

def mesgDebug(s):
 if(debugLevel>3): print s
def mesgInfo(s):
 if(debugLevel>2): print s
def mesgWarn(s):
 if(debugLevel>1): print s
def mesgErr(s):
 if(debugLevel>0): print s

