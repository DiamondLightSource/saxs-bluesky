"""

Configuration for b21 PandA beamline

"""

BL = "b21"


#GUI Elements

PULSEBLOCKS = 6
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["FS", "SAXS/WAXS","LED1","LED2", "LED3", "LED4"]
THEME_NAME = "clam" #--> ('clam', 'alt', 'default', 'classic')

#PandA Wiring connections

TTLIN = {1: "Beamstop V2F", 
        2: None,
     	3: None, 
   		4: "TFG WAXS", 
    	5: "TFG FS", 
   		6: "TFG SAXS"}

TTLOUT = {1: "FS",
  2: "SAXS",
  3: "WAXS",
  4: "LED1",
  5: "LED2",
  6: "LED3",
  7: "LED4",
  8: None,
  9: None,
  10: "V2F Relay"}


LVDSIN = {1: None,
  		2: None}


LVDSOUT = {1: "SAXS LVDS Out",
  		2: "WAXS LVDS Out"}

PULSE_CONNECTIONS = {1: [TTLOUT[1]],
					 2: [TTLOUT[2], TTLOUT[3]],
					 3: [TTLOUT[4]],
					 4: [TTLOUT[5]],
					 5: [TTLOUT[6]],
					 6: [TTLOUT[7]]}


### ncd plan parameters

DEADTIME_BUFFER = 20e-6 #Buffer added to deadtime to handle minor discrepencies between detector and panda clocks
DEFAULT_SEQ = 2 #default sequencer is this one, b21 currently uses seq 1 for somthing else
GENERAL_TIMEOUT = 30 #seconds before each wait times out

CONFIG_NAME = "PandaTriggerWithCounterAndPCAP"
