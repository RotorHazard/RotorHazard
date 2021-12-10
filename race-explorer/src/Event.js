import React, { useState, useEffect } from 'react';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import Frequency, { processVtxTable } from './Frequency.js';
import { debounce } from 'lodash';
import { nanoid } from 'nanoid';
import { createVtxTableLoader, createEventDataLoader, storeEventData } from './rh-client.js';

const saveEventData = debounce(storeEventData, 2000);

function RaceRoundTable(props) {
  const [races, setRaces] = useState(props.races ?? []);
  useEffect(() => {
    setRaces(props.races);
  }, [props.races]);
  const onChangeCallback = props.onChange;
  useEffect(() => {
    if (onChangeCallback) {
      onChangeCallback(races);
    }
  }, [onChangeCallback, races]);
  const addRace = () => {
    setRaces((old) => {
      const newRaces = [...old];
      const raceClasses = Object.keys(props.classes);
      const newRace = {class: raceClasses[0], name: 'New race', seats: []};
      for (let i=0; i<props.seats.length; i++) {
        newRace.seats[i] = null;
      }
      if (old.length > 0) {
        newRace.class = old[old.length-1].class;
      }
      newRaces.push(newRace);
      return newRaces;
    });
  };
  return (
    <div>
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
          <TableCell>{props.title}</TableCell>
          <TableCell>Class</TableCell>
          {props.seats?.map((fbc, idx) => {
            return <TableCell key={idx}>Seat {idx+1}</TableCell>;
          })}
          </TableRow>
        </TableHead>
        <TableBody>
        {
          races.map((race, raceIdx) => {
            const deleteRace = () => {
              setRaces((old) => {
                const newRaces = [...old];
                newRaces.splice(raceIdx, 1);
                return newRaces;
              });
            };
            const deleteButton = raceIdx > 0 ? <IconButton onClick={deleteRace}><DeleteIcon/></IconButton> : null;
            const changeRaceName = (name) => {
              setRaces((old) => {
                const newRaces = [...old];
                newRaces[raceIdx].name = name;
                return newRaces;
              });
            };
            const changeRaceClass = (cls) => {
              setRaces((old) => {
                const newRaces = [...old];
                newRaces[raceIdx].class = cls;
                return newRaces;
              });
            };
            return (
              <TableRow key={race.id}>
              <TableCell component="th" scope="row">
                {deleteButton}
                <TextField value={race.name} onChange={(evt) => changeRaceName(evt.target.value)}/>
              </TableCell>
              <TableCell>
                <FormControl>
                <Select value={race.class} onChange={(evt) => changeRaceClass(evt.target.value)}>
                {
                  Object.keys(props.classes).map((cls) => {
                    return <MenuItem key={cls} value={cls}>{cls}</MenuItem>;
                  })
                }
                </Select>
                </FormControl>
              </TableCell>
              {
                race.seats.map((pilot, seatIdx) => {
                  return (
                    <TableCell key={seatIdx}>
                    <FormControl>
                    <Select value={pilot??''}>
                    {
                      Object.keys(props.pilots).map((p) => {
                        return <MenuItem key={p} value={p}>{p}</MenuItem>;
                      })
                    }
                    </Select>
                    </FormControl>
                    </TableCell>
                  );
                })
              }
              </TableRow>
            );
          })
        }
        <TableRow><TableCell colSpan={(props.seats?.length ?? 0)+2}><IconButton onClick={addRace}><AddIcon/></IconButton></TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    </div>
  );
}

function RaceRoundPanel(props) {
  return (
    <div>
    <FormControl>
    <InputLabel id="method-label">Method</InputLabel>
    <Select labelId="method-label" value={props.generators[0]}>
    {
      props.generators.map((gen) => {
        return <MenuItem key={gen} value={gen}>{gen}</MenuItem>
      })
    }
    </Select>
    </FormControl>
    <Button>Generate</Button>
    <RaceRoundTable title={props.title} seats={props.seats} races={props.races}
      pilots={props.pilots} classes={props.classes}
      onChange={props.onChange}
    />
    </div>
  );
}

const HEAT_GEN = [
  "Random"
];

const MAIN_GEN = [
  "Triples"
];

function copyRace(r) {
  return {
    id: r.id,
    name: r.name,
    class: r.class,
    seats: [...r.seats]
  };
}

export default function Event(props) {
  const [vtxTable, setVtxTable] = useState({});
  const [eventName, setEventName] = useState('');
  const [eventDesc, setEventDesc] = useState('');
  const [eventUrl, setEventUrl] = useState('');
  const [pilots, setPilots] = useState({});
  const [raceClasses, setRaceClasses] = useState({});
  const [seats, setSeats] = useState([]);
  const [heats, setHeats] = useState([]);
  const [mains, setMains] = useState([]);
  const [tabIndex, setTabIndex] = useState(0);

  useEffect(() => {
    const loader = createVtxTableLoader();
    loader.load(processVtxTable, setVtxTable);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createEventDataLoader();
    loader.load(null, (data) => {
      for (const race of data.heats) {
        race.id = race.id ?? nanoid();
      }
      if (data.mains) {
        for (const race of data.mains) {
          race.id = race.id ?? nanoid();
        }
      }
      setEventName(data.name);
      setEventDesc(data.description);
      setEventUrl(data.url);
      setPilots(data.pilots);
      setRaceClasses(data.classes);
      setSeats(data.seats);
      setHeats(data.heats);
      setMains(data.mains ?? [])
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    saveEventData({
      name: eventName,
      description: eventDesc,
      url: eventUrl,
      pilots: pilots,
      classes: raceClasses,
      seats: seats,
      heats: heats,
      mains: mains
    });
  }, [eventName, eventDesc, eventUrl, pilots, raceClasses, seats, heats, mains]);

  const tabs = [
    {label: "Heats", content: (
      <RaceRoundPanel title="Heats" seats={seats} races={heats} pilots={pilots} classes={raceClasses} generators={HEAT_GEN}
      onChange={setHeats}/>
    )},
    {label: "Mains", content: (
      <RaceRoundPanel title="Mains" seats={seats} races={mains} pilots={pilots} classes={raceClasses} generators={MAIN_GEN}
      onChange={setMains}/>
    )}
  ];
  const tab = tabs[tabIndex];

  const changeEventName = (v) => {
    setEventName(v);
  };

  const changeEventDesc = (v) => {
    setEventDesc(v);
  };

  const changeEventUrl = (v) => {
    setEventUrl(v);
  };

  const addRaceSeats = (races) => {
    return races.map((race) => {
      const newRace = copyRace(race);
      newRace.seats.push(null);
      return newRace;
    });
  };
  const addSeat = () => {
    setSeats((old) => {
      const newSeats = [...old];
      newSeats.push({frequency: 0});
      return newSeats;
    });
    setHeats(addRaceSeats);
    setMains(addRaceSeats);
  };

  return (
    <Stack>
    <TextField label="Event name" value={eventName} onChange={(evt) => changeEventName(evt.target.value)}/>
    <TextField label="Event description" multiline value={eventDesc} onChange={(evt) => changeEventDesc(evt.target.value)}/>
    <TextField label="Event URL" value={eventUrl} onChange={(evt) => changeEventUrl(evt.target.value)}/>
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
          {seats.map((fbc, idx) => {
            const deleteRaceSeats = (races) => {
              return races.map((race) => {
                const newRace = copyRace(race);
                newRace.seats.splice(idx, 1);
                return newRace;
              });
            };
            const deleteSeat = () => {
              setSeats((old) => {
                const newSeats = [...old];
                newSeats.splice(idx, 1);
                return newSeats;
              });
              setHeats(deleteRaceSeats);
              setMains(deleteRaceSeats);
            };
            const deleteButton = idx > 0 ? <IconButton onClick={deleteSeat}><DeleteIcon/></IconButton> : null;
            return <TableCell key={idx}>{deleteButton} Seat {idx+1}</TableCell>;
          })}
          <TableCell><IconButton onClick={addSeat}><AddIcon/></IconButton></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
          {seats.map((fbc, idx) => {
            const selectSeatFrequency = (freq, bc) => {
              setSeats((old) => {
                const newSeats = [...old];
                newSeats[idx] = {frequency: freq};
                if (bc) {
                  newSeats[idx].bandChannel = bc;
                }
                return newSeats;
              });
            };
            return (
              <TableCell key={idx}>
              <Frequency frequency={fbc.frequency.toString()} bandChannel={fbc?.bandChannel} vtxTable={vtxTable}
              onChange={selectSeatFrequency}/>
              </TableCell>
            );
          })}
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    <Stack direction="row">
    <div>
    <div>Pilots</div>
    <List sx={{maxHeight: '500px', overflow: 'auto'}}>
    {
      pilots && Object.entries(pilots).map((entry) => {
        return <ListItem key={entry[0]}>
        <ListItemText>{entry[0]}</ListItemText>
        </ListItem>;
      })
    }
    </List>
    </div>
    <Stack>
    <Tabs sx={{borderBottom: 1, borderColor: 'divider'}} value={tabIndex} onChange={(evt,idx)=>{setTabIndex(idx)}}>
    {
      tabs.map((entry) => {
        return <Tab key={entry.label} label={entry.label}/>;
      })
    }
    </Tabs>
    {tab.content}
    </Stack>
    </Stack>
    </Stack>
  );
}
