import React, { useState, useEffect } from 'react';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
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
import { DndContext, useDroppable, useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import Frequency, { processVtxTable } from './Frequency.js';
import { debounce } from 'lodash';
import { nanoid } from 'nanoid';
import { createVtxTableLoader, createEventDataLoader, storeEventData } from './rh-client.js';

const saveEventData = debounce(storeEventData, 2000);

function copyRace(r, newVals) {
  if (!r.id) {
    throw Error("Race missing ID");
  }
  return {
    id: r.id,
    name: r.name,
    class: r.class,
    seats: [...r.seats],
    ...newVals
  };
}

function updateRace(races, idx, newVals) {
  const newRaces = [...races];
  const newRace = copyRace(races[idx], newVals);
  newRaces[idx] = newRace;
  return newRaces;
}


function RacePilot(props) {
  const {attributes, listeners, setNodeRef, transform} = useDraggable({
    id: props.id,
    data: {
      stage: props.stage, race: props.race, seat: props.seat,
      source: 'seat'
    }
  });
  const style = {
    transform: transform ? CSS.Translate.toString(transform) : null,
    display: 'block',
    margin: '0 auto',
    minWidth: '5em',
    minHeight: '1em'
  };

  return <button ref={setNodeRef} style={style} {...listeners} {...attributes}>{props.pilot}</button>;
}


function RaceSeat(props) {
  const {isOver, setNodeRef} = useDroppable({
    id: props.id,
    data: {
      stage: props.stage, race: props.race, seat: props.seat
    }
  });
  const scale = isOver ? 2 : 1;
  const style = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    border: '1px solid black',
    borderTopLeftRadius: '5px', borderTopRightRadius: '5px',
    borderBottomLeftRadius: '5px', borderBottomRightRadius: '5px',
    minWidth: '5em',
    minHeight: (scale*2)+'em'
  };
  const contents = isOver ? (props.seat+1) : props.children;
  return (
    <div ref={setNodeRef} style={style}>{contents}</div>
  );
}


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
      const newRace = {id: nanoid(), class: raceClasses[0], name: 'New race', seats: []};
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
                return updateRace(old, raceIdx, {name: name});
              });
            };
            const changeRaceClass = (cls) => {
              setRaces((old) => {
                return updateRace(old, raceIdx, {class: cls});
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
                    <RaceSeat id={race.id+'/'+seatIdx} stage={props.title} race={raceIdx} seat={seatIdx}>
                    {pilot &&
                    <RacePilot id={race.id+'/'+seatIdx} stage={props.title} race={raceIdx} seat={seatIdx} pilot={pilot}/>
                    }
                    </RaceSeat>
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
      classes={props.classes} onChange={props.onChange}
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

function Pilot(props) {
  const {attributes, listeners, setNodeRef, transform} = useDraggable({
    id: props.pilot,
    data: {pilot: props.pilot, source: 'rooster'}
  });
  const style = {
    transform: transform ? CSS.Translate.toString(transform) : null,
    display: 'block',
    minWidth: '5em',
    minHeight: '1em'
  };

  return <button ref={setNodeRef} style={style} {...listeners} {...attributes}>{props.pilot}</button>;
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
      <RaceRoundPanel title="Heats" seats={seats} races={heats} classes={raceClasses} generators={HEAT_GEN}
      onChange={setHeats}/>
    )},
    {label: "Mains", content: (
      <RaceRoundPanel title="Mains" seats={seats} races={mains} classes={raceClasses} generators={MAIN_GEN}
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

  const onDragEnd = (evt) => {
    const dragData = evt.active.data.current;
    let updater = null;
    let stage = null;
    if (evt.over && dragData.source === 'rooster') {
      const dropData = evt.over.data.current;
      stage = dropData.stage;
      updater = (old) => {
        const newRaces = [...old];
        const newRace = copyRace(newRaces[dropData.race]);
        newRace.seats[dropData.seat] = dragData.pilot;
        newRaces[dropData.race] = newRace;
        return newRaces;
      };
    } else if (evt.over && dragData.source === 'seat') {
      const dropData = evt.over.data.current;
      stage = dropData.stage;
      updater = (old) => {
        const newRaces = [...old];
        const fromRace = copyRace(newRaces[dragData.race]);
        newRaces[dragData.race] = fromRace;
        let toRace;
        if (dragData.race !== dropData.race) {
          toRace = copyRace(newRaces[dropData.race]);
          newRaces[dropData.race] = toRace;
        } else {
          toRace = fromRace;
        }
        const newPilot = fromRace.seats[dragData.seat];
        const oldPilot = toRace.seats[dropData.seat];
        toRace.seats[dropData.seat] = newPilot;
        fromRace.seats[dragData.seat] = oldPilot;
        return newRaces;
      };
    } else if (!evt.over && dragData.source === 'seat') {
      stage = dragData.stage;
      updater = (old) => {
        const newRaces = [...old];
        const fromRace = copyRace(newRaces[dragData.race]);
        newRaces[dragData.race] = fromRace;
        fromRace.seats[dragData.seat] = null;
        return newRaces;
      };
    }
    if (updater) {
      if (stage === 'Heats') {
        setHeats(updater);
      } else if (stage === 'Mains') {
        setMains(updater);
      }
    }
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

    <DndContext onDragEnd={onDragEnd}>
    <Stack direction="row">
    <div>
    <div>Pilots</div>
    <div>
    {
      pilots && Object.entries(pilots).map((entry) => {
        return <Pilot key={entry[0]} pilot={entry[0]}/>;
      })
    }
    </div>
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
    </DndContext>

    </Stack>
  );
}
