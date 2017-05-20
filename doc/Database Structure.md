## Database 'vtx'

### Table 'config'

| commsStatus | raceStatus | minLapTime |
| --- | --- | --- |

### Table 'status' (MEMORY)

| commsStatus | raceStatus |
| --- | --- |

### Table 'nodes'

| node | i2cAddr | vtxFreq | vtxChan | rssiTrig |
| --- | --- | --- | --- | --- |

### Table 'nodesMem' (MEMORY)

| node | rssi | lapCount |
| --- | --- | --- |

### Table 'currentLaps'

| pilot | lap | min | sec | milliSec |
| --- | --- | --- | --- | --- |

### Table 'pilots'

| pilot | callSign | firstName | lastName | rssiTrigger | group |
| --- | --- | --- | --- | --- | --- |

### Table 'savedraces'

| round | group | pilot | lap | min | sec | milliSec |
| --- | --- | --- | --- | --- | --- | --- |

### Table 'vtxReference'

| vtxChan | vtxFreq |
| --- | --- |
