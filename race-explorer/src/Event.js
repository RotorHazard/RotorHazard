import React, { useState, useEffect } from 'react';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
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
import TreeItem from '@mui/lab/TreeItem';
import TreeView from '@mui/lab/TreeView';
import Paper from '@mui/material/Paper';
import AddIcon from '@mui/icons-material/Add';
import ClearIcon from '@mui/icons-material/Clear';
import DeleteIcon from '@mui/icons-material/Delete';
import CloudSyncIcon from '@mui/icons-material/CloudSync';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { DndContext, DragOverlay, useDroppable } from '@dnd-kit/core';
import ValidatingTextField from './ValidatingTextField.js';
import Draggable, { useDnDSensors } from './Draggable.js';
import Frequency, { processVtxTable } from './Frequency.js';
import Pilot from './Pilot.js';
import RaceClass from './RaceClass.js';
import TreeNode from './TreeNode.js';
import { flattenTree } from './RaceClasses.js';
import { debounce } from 'lodash';
import { nanoid } from 'nanoid';
import {
  createVtxTableLoader,
  createEventDataLoader, storeEventData,
  createHeatGeneratorLoader, generateHeats,
  createRaceClassLoader,
  syncEvent
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
    type: r.type,
    leaderboards: {...r.leaderboards},
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
  const deleteRaces = () => {
    updateRaces((old) => []);
  }
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
          <TableCell><IconButton onClick={deleteRaces}>
          {races.length > 0 ? <DeleteIcon/> : <ClearIcon/>}
          </IconButton></TableCell>
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
              <TableCell>
                <IconButton onClick={deleteRace}><DeleteIcon/></IconButton>
              </TableCell>
              <TableCell component="th" scope="row">
                <ValidatingTextField value={race.name} sx={{minWidth: "5em"}} validateChange={changeRaceName}/>
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
        <TableRow><TableCell colSpan={(props.seats?.length ?? 0)+3}><IconButton onClick={addRace}><AddIcon/></IconButton></TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  );
}


function idifyRaces(races) {
  for (const race of races) {
    race.id = race.id ?? nanoid();
  }
  return races
}

function updateUiState(setUiState, param, v) {
  setUiState((old) => {return {...old, [param]: v};})
}

function buildUi(genDesc) {
  const renderers = [];
  genDesc.parameters.forEach((param) => {
    const paramName = param.name;
    if(param.label) {
      let renderer;
      switch (param.type) {
        case 'integer':
          renderer = (props, uiState, setUiState) => (
            <ValidatingTextField key={paramName} label={param.label} value={uiState[paramName]}
            validateChange={(v) => {
              updateUiState(setUiState, paramName, Number(v));
              return '';
            }}
            inputProps={{type: 'number', min: param.min, max: param.max}}/>
          );
          break;
        case 'class':
          renderer = (props, uiState, setUiState) => (
            <RaceClassSelector key={paramName} label={param.label} value={uiState[paramName]} raceClasses={props.raceClasses}
            onSelect={(raceClass) => {updateUiState(setUiState, paramName, raceClass);}}/>
          );
          break;
        case 'seats':
          renderer = (props, uiState, setUiState) => (
            <ValidatingTextField key={paramName} label={param.label} value={uiState[paramName]}
            validateChange={(v) => {
              updateUiState(setUiState, paramName, Number(v));
              return '';
            }}
            inputProps={{type: 'number', min: 1, max: props.seats.length}}/>
          );
          break;
        default:
          renderer = null;
          break;
      }
      if (renderer !== null) {
        renderers.push(renderer);
      }
    }
  });
  return function(props, uiState, setUiState) {
    return <>{
      renderers.map((renderer) => renderer(props, uiState, setUiState))
    }</>;
  };
}

function initiateUiState(genDesc, seats, raceClasses, setGeneratorUiState) {
  const state = {};
  genDesc.parameters.forEach((param) => {
    const paramName = param.name;
    if(param.label) {
      let value;
      switch (param.type) {
        case 'class':
          value = Object.keys(raceClasses)[0];
          break;
        case 'seats':
          value = seats.length;
          break;
        default:
          value = param.default ?? null;
          break;
      }
      state[paramName] = value;
    }
  });
  setGeneratorUiState(state);
}

function RaceStagePanel(props) {
  const [generator, setGenerator] = useState('');
  const [generatorDesc, setGeneratorDesc] = useState({parameters: []});
  const [generatorUi, setGeneratorUi] = useState({'render': ()=>null});
  const [generatorUiState, setGeneratorUiState] = useState({});

  useEffect(() => {
    setGenerator(Object.keys(props.generators)[0]);
  }, [props.generators]);

  useEffect(() => {
    const endpoint = props.generators[generator];
    const loader = createHeatGeneratorLoader(endpoint);
    loader.load(null, setGeneratorDesc);
    return () => loader.cancel();
  }, [props.generators, generator]);

  useEffect(() => {
    const ui = buildUi(generatorDesc);
    setGeneratorUi({'render': ui});
  }, [generatorDesc]);

  useEffect(() => {
    initiateUiState(generatorDesc, props.seats, props.raceClasses, setGeneratorUiState);
  }, [generatorDesc, props.seats, props.raceClasses]);

  const generate = () => {
    const endpoint = props.generators[generator];
    const data = Object.fromEntries(generatorDesc.parameters.map((param) => {
      const paramName = param.name;
      let value = null;
      switch (param.type) {
        case 'pilots':
          value = Object.keys(props.pilots);
          break;
        default:
          value = generatorUiState[paramName];
          break;
      }
      return [paramName, value];
    }));
    data.stage = props.stageIdx;
    generateHeats(endpoint, data, (stageData) => {
      const races = stageData.heats;
      idifyRaces(races);
      let newStageName = props.stage.name;
      if (newStageName !== 'Qualifying' && stageData.type) {
        newStageName = stageData.type;
      }
      props.onChange({...stageData, name: newStageName, heats: props.stage.heats.concat(races)});
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
    <RacesTable races={props.stage.heats} seats={props.seats}
      raceClasses={props.raceClasses} onChange={(races) => props.onChange({heats: races})}
    />
    </div>
  );
}

const QUALIFYING_GENS = {
  Random: "/heat-generators/random"
};

const MAINS_GENS = {
  "Ladder Mains": "/heat-generators/mains",
  "MultiGP Brackets": "/heat-generators/mgp-brackets",
  "FAI Single Brackets": "/heat-generators/fai-single-16",
  "FAI Double Brackets": "/heat-generators/fai-double-16",
  Random: "/heat-generators/random"
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


function PilotRooster(props) {
  const pilots = props.pilots;
  return (
    <div>
    <div>Pilots</div>
    <List>
    {
      pilots && Object.entries(pilots).map((entry) => {
        const callsign = entry[0];
        return <ListItem key={callsign}><DraggableEntry id={callsign} pilot={callsign}><Pilot callsign={callsign}/></DraggableEntry></ListItem>;
      })
    }
    </List>
    </div>
  );
}

function copyStage(stage, newVals) {
  return {
    name: stage.name,
    heats: stage.heats,
    ...newVals
  };
}

function updateStage(oldStages, stageIdx, newVals, setStageIndex) {
  const newStages = [...oldStages];
  if (stageIdx === -1) {
    newStages.push(newVals);
  } else if (newStages[stageIdx].heats.length === 0 && newVals.heats.length === 0) {
    // delete stage on 'double' delete
    newStages.splice(stageIdx, 1);
  } else {
    newStages[stageIdx] = copyStage(oldStages[stageIdx], newVals);
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
    const newRaces = stage.heats.map((race) => {
      const newRace = copyRace(race);
      updateRace(newRace);
      return newRace;
    });
    return {...stage, heats: newRaces};
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
  const [raceClassTree, setRaceClassTree] = useState({});

  const sensors = useDnDSensors();

  useEffect(() => {
    const loader = createVtxTableLoader();
    loader.load(processVtxTable, setVtxTable);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createRaceClassLoader();
    loader.load(null, (data) => {
      setRaceClassTree(data.classes);
    });
  }, []);

  const loadEvent = (data) => {
    data.stages.forEach((stage) => {idifyRaces(stage.heats)});
    setEventName(data.name);
    setEventDesc(data.description);
    setEventUrl(data.url);
    setPilots(data.pilots);
    setRaceClasses(data.classes);
    setSeats(data.seats);
    setStages(data.stages);
  };

  useEffect(() => {
    const loader = createEventDataLoader();
    loader.load(null, loadEvent);
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
    const onStageChange = (newVals) => {
      setStages((old) => updateStage(old, stageIdx, newVals, setStageIndex));
    };
    return {label: stage.name, content: (
      <RaceStagePanel pilots={pilots} stage={stage} stageIdx={stageIdx} seats={seats} raceClasses={raceClasses} generators={generators}
        onChange={onStageChange}
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

  const raceClassTreeRenderer = (raceClasses) => {
    return Object.entries(raceClasses).map((e) => {
      const raceClassName = e[0];
      const raceClass = e[1];
      const nodeRenderer = (props) => {
        return (
          <RaceClass name={props.label} className={props.classes.label}/>
        );
      };
      return (
        <TreeItem key={raceClassName} nodeId={raceClassName} label={raceClassName} sx={{textAlign: 'left'}}
        ContentComponent={TreeNode} ContentProps={{render: nodeRenderer}}>
          {raceClassTreeRenderer(raceClass.children)}
        </TreeItem>
      );
    });
  };

  const raceClassNodeSelected = (evt, nodeIds) => {
    const nodesByName = flattenTree(raceClassTree);
    let raceClasses = {};
    for (const nodeId of nodeIds) {
      const raceClass = {...nodesByName[nodeId].content}; // copy
      raceClass.children = Object.fromEntries(Object.entries(raceClass.children).map((e) => [e[0], {}]));
      raceClasses[nodeId] = raceClass;
    }
    
    setRaceClasses(raceClasses);
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
      setDraggingPilot(stages[stageIndex].heats[dragData.race].seats[dragData.seat]);
    }
  };
  const onDragCancel= (evt) => {
    setDraggingPilot(null);
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
      setStages((old) => updateStage(old, stageIndex, {heats: updater(old[stageIndex].heats)}, setStageIndex));
    }
  };

  return (
    <Stack>
    <ValidatingTextField label="Event name" value={eventName} validateChange={changeEventName}/>
    <ValidatingTextField label="Event description" multiline value={eventDesc} validateChange={changeEventDesc}/>
    <ValidatingTextField label="Event URL" value={eventUrl} validateChange={changeEventUrl} inputProps={{type: 'url'}}/>
    <IconButton onClick={(evt) => {syncEvent(loadEvent)}}><CloudSyncIcon/></IconButton>

    <TreeView multiSelect selected={Object.keys(raceClasses)} defaultCollapseIcon={<ExpandMoreIcon />} defaultExpandIcon={<ChevronRightIcon />} onNodeSelect={raceClassNodeSelected}>
    {raceClassTreeRenderer(raceClassTree)}
    </TreeView>

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

    <DndContext onDragStart={onDragStart} onDragCancel={onDragCancel} onDragEnd={onDragEnd} sensors={sensors}>
    <Stack direction="row">
      <PilotRooster pilots={pilots}/>
  
      <Stack>
        <Stack direction="row">
        {stageTab && (
          <Tabs sx={{borderBottom: 1, borderColor: 'divider'}} value={stageIndex}
          variant="scrollable" onChange={(evt,idx)=>{setStageIndex(idx);}}>
          {
            stageTabs.map((entry) => {
              return <Tab key={entry.label} label={entry.label}/>;
            })
          }
          </Tabs>)
        }
        <IconButton onClick={() => {
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
          setStages((old) => updateStage(old, -1, {name: name, heats: []}, setStageIndex));
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
