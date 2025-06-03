"""

Configuration for i22 PandA beamline

"""

BL = "i22"


#GUI Elements

PULSEBLOCKS = 4
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["FS", "DETS/TETS","OAV","Fluro"]
THEME_NAME = "clam" #--> ('clam', 'alt', 'default', 'classic')

#PandA Wiring connections

TTLIN = {1: "TFG Det", 
        2: "TFG FS",
     	3: None, 
   		4: None, 
    	5: None, 
   		6: None}

TTLOUT = {1: "it",
  2: "FS",
  3: "oav",
  4: "User Tet",
  5: "waxs",
  6: "i0",
  7: "saxs",
  8: "Fluores",
  9: "User1",
  10: "User2"}


LVDSIN = {1: None,
  		2: None}


LVDSOUT = {1: None,
  		2: None}

PULSE_CONNECTIONS = {1: [TTLOUT[2]],
					 2: [TTLOUT[1], TTLOUT[4], TTLOUT[5], TTLOUT[6], TTLOUT[7]],
					 3: [TTLOUT[3]],
					 4:[TTLOUT[8]] }


### ncd plan parameters

DEADTIME_BUFFER = 20e-6 #Buffer added to deadtime to handle minor discrepencies between detector and panda clocks
DEFAULT_SEQ = 1 #default sequencer is this one, pandas can have 2
GENERAL_TIMEOUT = 30 #seconds before each wait times out
CONFIG_NAME = "PandaTrigger"
