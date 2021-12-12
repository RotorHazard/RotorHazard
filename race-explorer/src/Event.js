import React, { useState, useEffect } from 'react';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
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
import { DndContext, DragOverlay, useDroppable, useDraggable } from '@dnd-kit/core';
import ValidatingTextField from './ValidatingTextField.js';
import Frequency, { processVtxTable } from './Frequency.js';
import { debounce } from 'lodash';
import { nanoid } from 'nanoid';
import {
  createVtxTableLoader,
  createEventDataLoader, storeEventData,
  createRaceGeneratorLoader, generateRace
} from './rh-client.js';

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


function Draggable(props) {
  const {attributes, listeners, setNodeRef} = useDraggable({
    id: props.id,
    data: props.data
  });
  const style = {
    touchAction: 'none',
    ...props.style
  };

  return <button ref={setNodeRef} style={style} {...listeners} {...attributes}>{props.children}</button>;
}


function Pilot(props) {
  return <div>{props.callsign}</div>;
}


function DraggableSeat(props) {
  const data = {
    race: props.race, seat: props.seat,
    source: 'seat'
  };
  const style = {
    display: 'block',
    margin: '0 auto',
    minWidth: '5em',
    minHeight: '1em'
  };
  return <Draggable id={props.id} data={data} style={style}>{props.children}</Draggable>;
}


function DroppableSeat(props) {
  const {isOver, setNodeRef} = useDroppable({
    id: props.id,
    data: {
      race: props.race, seat: props.seat
    }
  });
  const style = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    border: isOver ? '1px solid red' : '1px solid black',
    borderTopLeftRadius: '5px', borderTopRightRadius: '5px',
    borderBottomLeftRadius: '5px', borderBottomRightRadius: '5px',
    minWidth: '5em',
    minHeight: isOver ? '4em' : '2em'
  };
  return (
    <div ref={setNodeRef} style={style}>{props.children}</div>
  );
}


function createRace(raceClasses, seats) {
  const newSeats = [];
  for (let i=0; i<seats.length; i++) {
    newSeats[i] = null;
  }
  const classNames = Object.keys(raceClasses);
  return {id: nanoid(), class: classNames[0], name: 'New race', seats: newSeats};
}


function RaceClassSelector(props) {
  const labelId = nanoid()+"-raceclass-label";
  return (
    <FormControl>
    {props.label && <InputLabel id={labelId}>{props.label}</InputLabel>}
    <Select labelId={props.label ? labelId : null} value={props.value} onChange={(evt) => props.onSelect(evt.target.value)}>
    {
      Object.keys(props.raceClasses).map((cls) => {
        return <MenuItem key={cls} value={cls}>{cls}</MenuItem>;
      })
    }
    </Select>
    </FormControl>
  );
}

function RacesTable(props) {
  const [races, setRaces] = useState([]);

  useEffect(() => {
    setRaces(props.races);
  }, [props.races]);

  const updateRaces = (updater) => {
    const newRaces = updater(races);
    setRaces(newRaces);
    if (props.onChange) {
      props.onChange(newRaces);
    }
  };

  const addRace = () => {
    updateRaces((old) => {
      const newRaces = [...old];
      const newRace = createRace(props.raceClasses, props.seats);
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
          <TableCell>Race</TableCell>
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
              updateRaces((old) => {
                const newRaces = [...old];
                newRaces.splice(raceIdx, 1);
                return newRaces;
              });
            };
            const changeRaceName = (name) => {
              updateRaces((old) => {
                return updateRace(old, raceIdx, {name: name});
              });
              return '';
            };
            const selectRaceClass = (cls) => {
              updateRaces((old) => {
                return updateRace(old, raceIdx, {class: cls});
              });
            };
            return (
              <TableRow key={race.id}>
              <TableCell component="th" scope="row">
                <IconButton onClick={deleteRace}><DeleteIcon/></IconButton>
                <ValidatingTextField value={race.name} validateChange={changeRaceName}/>
              </TableCell>
              <TableCell>
                <RaceClassSelector value={race.class} raceClasses={props.raceClasses} onSelect={selectRaceClass}/>
              </TableCell>
              {
                race.seats.map((pilot, seatIdx) => {
                  const id = race.id+'/'+seatIdx;
                  return (
                    <TableCell key={seatIdx}>
                    <DroppableSeat id={id} race={raceIdx} seat={seatIdx}>
                    {pilot &&
                    <DraggableSeat id={id} race={raceIdx} seat={seatIdx}><Pilot callsign={pilot}/></DraggableSeat>
                    }
                    </DroppableSeat>
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


function idifyRaces(races) {
  for (const race of races) {
    race.id = race.id ?? nanoid();
  }
  return races
}

function buildUi(uiDesc) {
  const renderers = [];
  Object.entries(uiDesc).forEach((entry) => {
    const param = entry[0];
    const desc = entry[1];
    if(desc.label) {
      switch (desc.type) {
        case 'class':
          const renderer = (props, uiState, setUiState) => (
            <RaceClassSelector key={param} label={desc.label} value={uiState[param]} raceClasses={props.raceClasses}
            onSelect={(raceClass) => {setUiState((old) => {return {...old, [param]: raceClass};});}}/>
          );
          renderers.push(renderer);
          break;
        default:
          break;
      }
    }
  });
  return function(props, uiState, setUiState) {
    return <>{
      renderers.map((renderer) => renderer(props, uiState, setUiState))
    }</>;
  };
}

function initiateUiState(uiDesc, raceClasses, setGeneratorUiState) {
  const state = {};
  Object.entries(uiDesc).forEach((entry) => {
    const param = entry[0];
    const desc = entry[1];
    if(desc.label) {
      switch (desc.type) {
        case 'class':
          state[param] = Object.keys(raceClasses)[0];
          break;
        default:
          break;
      }
    }
  });
  setGeneratorUiState(state);
}

function RaceStagePanel(props) {
  const [generator, setGenerator] = useState('');
  const [generatorParams, setGeneratorParams] = useState({});
  const [generatorUi, setGeneratorUi] = useState({'render': ()=>null});
  const [generatorUiState, setGeneratorUiState] = useState({});

  useEffect(() => {
    setGenerator(Object.keys(props.generators)[0]);
  }, [props.generators]);

  useEffect(() => {
    const endpoint = props.generators[generator];
    const loader = createRaceGeneratorLoader(endpoint);
    loader.load(null, setGeneratorParams);
    return () => loader.cancel();
  }, [props.generators, generator]);

  useEffect(() => {
    const ui = buildUi(generatorParams);
    setGeneratorUi({'render': ui});
  }, [generatorParams]);

  useEffect(() => {
    initiateUiState(generatorParams, props.raceClasses, setGeneratorUiState);
  }, [generatorParams, props.raceClasses]);

  const generate = () => {
    const endpoint = props.generators[generator];
    const data = Object.fromEntries(Object.entries(generatorParams).map((entry) => {
      const param = entry[0];
      const desc = entry[1];
      let value = null;
      switch (desc.type) {
        case 'pilots':
          value = Object.keys(props.pilots);
          break;
        case 'seats':
          value = props.seats.length;
          break;
        default:
          value = generatorUiState[param];
          break;
      }
      return [param, value];
    }));
    generateRace(endpoint, data, (races) => {
      idifyRaces(races);
      props.onChange(races);
    });
  };

  return (
    <div>
    <FormControl>
    <InputLabel id="method-label">Method</InputLabel>
    <Select labelId="method-label" value={generator} onChange={(evt) => setGenerator(evt.target.value)}>
    {
      Object.keys(props.generators).map((gen) => {
        return <MenuItem key={gen} value={gen}>{gen}</MenuItem>
      })
    }
    </Select>
    </FormControl>
    {generatorUi.render(props, generatorUiState, setGeneratorUiState)}
    <Button onClick={generate}>Generate</Button>
    <RacesTable races={props.stage.races} seats={props.seats}
      raceClasses={props.raceClasses} onChange={props.onChange}
    />
    </div>
  );
}

const QUALIFYING_GENS = {
  Random: "/race-generators/random"
};

const MAINS_GENS = {
  Random: "/race-generators/random"
};

function DraggableEntry(props) {
  const data = {pilot: props.pilot, source: 'rooster'};
  const style = {
    display: 'block',
    minWidth: '5em',
    minHeight: '1em'
  };
  return <Draggable id={props.id} data={data} style={style}>{props.children}</Draggable>;
}


function copyStage(stage, newVals) {
  return {
    name: stage.name,
    races: stage.races,
    ...newVals
  };
}

function updateStage(oldStages, stageIdx, newVals, setStageIndex) {
  const newStages = [...oldStages];
  if (stageIdx === -1) {
    newStages.push(newVals);
  } else if (newVals.races.length > 0) {
    newStages[stageIdx] = copyStage(oldStages[stageIdx], newVals);
  } else {
    newStages.splice(stageIdx, 1);
  }
  setStageIndex((oldIdx) => {
    if (stageIdx === -1 || oldIdx >= newStages.length) {
      return newStages.length - 1;
    } else if (newStages.length === 1) {
      return 0;
    } else {
      return oldIdx;
    }
  });
  return newStages;
}

function mutateRaces(oldStages, updateRace) {
  return oldStages.map((stage) => {
    const newRaces = stage.races.map((race) => {
      const newRace = copyRace(race);
      updateRace(newRace);
      return newRace;
    });
    return {...stage, races: newRaces};
  });
}

export default function Event(props) {
  const [vtxTable, setVtxTable] = useState({});
  const [eventName, setEventName] = useState('');
  const [eventDesc, setEventDesc] = useState('');
  const [eventUrl, setEventUrl] = useState('');
  const [pilots, setPilots] = useState({});
  const [raceClasses, setRaceClasses] = useState({});
  const [seats, setSeats] = useState([]);
  const [stages, setStages] = useState([]);
  const [stageIndex, setStageIndex] = useState(0);
  const [draggingPilot, setDraggingPilot] = useState(null);

  useEffect(() => {
    const loader = createVtxTableLoader();
    loader.load(processVtxTable, setVtxTable);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createEventDataLoader();
    loader.load(null, (data) => {
      data.stages.forEach((stage) => {idifyRaces(stage.races)});
      setEventName(data.name);
      setEventDesc(data.description);
      setEventUrl(data.url);
      setPilots(data.pilots);
      setRaceClasses(data.classes);
      setSeats(data.seats);
      setStages(data.stages);
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
      stages: stages,
    });
  }, [eventName, eventDesc, eventUrl, pilots, raceClasses, seats, stages]);

  const stageTabs = stages.map((stage, stageIdx) => {
    const generators = (stageIdx > 0) ? MAINS_GENS : QUALIFYING_GENS;
    return {label: stage.name, content: (
      <RaceStagePanel pilots={pilots} stage={stage} seats={seats} raceClasses={raceClasses} generators={generators}
        onChange={(races) => {setStages((old) => updateStage(old, stageIdx, {races: races}, setStageIndex));}}
      />
    )};
  });

  const stageTab = (stageIndex >= 0 && stageIndex < stageTabs.length) ? stageTabs[stageIndex] : null;

  const changeEventName = (v) => {
    setEventName(v);
    return '';
  };

  const changeEventDesc = (v) => {
    setEventDesc(v);
    return '';
  };

  const changeEventUrl = (v) => {
    setEventUrl(v);
    return '';
  };

  const addSeat = () => {
    setSeats((old) => {
      const newSeats = [...old];
      newSeats.push({frequency: 0});
      return newSeats;
    });
    setStages((old) => mutateRaces(old, (race) => {race.seats.push(null)}));
  };

  const onDragStart = (evt) => {
    const dragData = evt.active.data.current;
    if (dragData.source === 'rooster') {
      setDraggingPilot(dragData.pilot);
    } else if (dragData.source === 'seat') {
      setDraggingPilot(stages[stageIndex].races[dragData.race].seats[dragData.seat]);
    }
  };
  const onDragEnd = (evt) => {
    setDraggingPilot(null);
    const dragData = evt.active.data.current;
    let updater = null;
    if (evt.over && dragData.source === 'rooster') {
      const dropData = evt.over.data.current;
      updater = (oldRaces) => {
        const newRaces = [...oldRaces];
        const newRace = copyRace(newRaces[dropData.race]);
        newRace.seats[dropData.seat] = dragData.pilot;
        newRaces[dropData.race] = newRace;
        return newRaces;
      };
    } else if (evt.over && dragData.source === 'seat') {
      const dropData = evt.over.data.current;
      updater = (oldRaces) => {
        const newRaces = [...oldRaces];
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
      updater = (oldRaces) => {
        const newRaces = [...oldRaces];
        const fromRace = copyRace(newRaces[dragData.race]);
        newRaces[dragData.race] = fromRace;
        fromRace.seats[dragData.seat] = null;
        return newRaces;
      };
    }
    if (updater) {
      setStages((old) => updateStage(old, stageIndex, {races: updater(old[stageIndex].races)}, setStageIndex));
    }
  };

  return (
    <Stack>
    <ValidatingTextField label="Event name" value={eventName} validateChange={changeEventName}/>
    <ValidatingTextField label="Event description" multiline value={eventDesc} validateChange={changeEventDesc}/>
    <ValidatingTextField label="Event URL" value={eventUrl} validateChange={changeEventUrl} inputProps={{type: 'url'}}/>
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
          {seats.map((fbc, idx) => {
            const deleteSeat = () => {
              setSeats((old) => {
                const newSeats = [...old];
                newSeats.splice(idx, 1);
                return newSeats;
              });
              setStages((old) => mutateRaces(old, (race) => {race.seats.splice(idx, 1)}));
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

    <DndContext onDragStart={onDragStart} onDragEnd={onDragEnd} autoScroll={true}>
    <Stack direction="row">
    <div>
    <div>Pilots</div>
    <div>
    {
      pilots && Object.entries(pilots).map((entry) => {
        const callsign = entry[0];
        return <DraggableEntry key={callsign} id={callsign} pilot={callsign}><Pilot callsign={callsign}/></DraggableEntry>;
      })
    }
    </div>
    </div>
    <Stack>
    <Stack direction="row">
    {stageTab && (
      <Tabs sx={{borderBottom: 1, borderColor: 'divider'}} value={stageIndex}
      onChange={(evt,idx)=>{setStageIndex(idx);}}>
      {
        stageTabs.map((entry) => {
          return <Tab key={entry.label} label={entry.label}/>;
        })
      }
      </Tabs>)
    }
    <IconButton onClick={() => {
      const newRace = createRace(raceClasses, seats);
      let name;
      switch (stageTabs.length) {
        case 0:
          name = "Qualifying";
          break;
        case 1:
          name = "Mains";
          break;
        default:
          name = "New stage "+(stageTabs.length+1);
          break;
      }
      setStages((old) => updateStage(old, -1, {name: name, races: [newRace]}, setStageIndex));
    }}><AddIcon/></IconButton>
    </Stack>
    {stageTab?.content}
    </Stack>
    </Stack>
    <DragOverlay wrapperElement="button" dropAnimation={null}>
    {draggingPilot ? <Pilot callsign={draggingPilot}/> : null}
    </DragOverlay>
    </DndContext>

    </Stack>
  );
}
