## Database 'vtx'

### Table 'setup'

| commsStatus | raceStatus | minLapTime |
| --- | --- | --- |

### Table 'nodes'

| node | i2cAddr | vtxNum | rssi | rssiTrig |
| --- | --- | --- | --- | --- |

### Table 'currentLaps'

| pilot | lap | min | sec | milliSec |
| --- | --- | --- | --- | --- |

### Table 'currentRace'

| pilot | place |
| --- | --- |

### Table 'pilots'

| pilot | callSign | firstName | lastName | rssiTrigger |
| --- | --- | --- | --- | --- |

### Table 'groups'

| group | pilot |
| --- | --- |

### Table 'savedraces'

| round | group | pilot | lap | min | sec | milliSec |
| --- | --- | --- | --- | --- | --- | --- |

### Table 'vtxReference'

| vtxNum | vtxChan | vtxFreq |
| --- | --- | --- |
