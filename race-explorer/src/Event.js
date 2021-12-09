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
import { createVtxTableLoader, createEventDataLoader, storeEventData } from './rh-client.js';

const saveEventData = debounce(storeEventData, 2000);

function RaceRoundTable(props) {
  return (
    <div>
    <div>{props.title}</div>
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
          props.races?.map((race, raceIdx) => {
            const deleteButton = raceIdx > 0 ? <IconButton><DeleteIcon/></IconButton> : null;
            return (
              <TableRow key={race.name}>
              <TableCell component="th" scope="row">
                {deleteButton}
                <TextField value={race.name}/>
              </TableCell>
              <TableCell>
                <FormControl>
                <Select value={race.class}>
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
        <TableRow><TableCell colSpan={(props.seats?.length ?? 0)+2}><IconButton><AddIcon/></IconButton></TableCell></TableRow>
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
    <RaceRoundTable title={props.title} seats={props.seats} races={props.races} pilots={props.pilots} classes={props.classes}/>
    </div>
  );
}

const HEAT_GEN = [
  "Random"
];

const MAIN_GEN = [
  "Triples"
];

export default function Event(props) {
  const [vtxTable, setVtxTable] = useState({});
  const [eventData, setEventData] = useState({});
  const [tabIndex, setTabIndex] = useState(0);

  useEffect(() => {
    const loader = createVtxTableLoader();
    loader.load(processVtxTable, setVtxTable);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createEventDataLoader();
    loader.load(null, setEventData);
    return () => loader.cancel();
  }, []);

  const tabs = [
    {label: "Heats", content: (
      <RaceRoundPanel title="Heats" seats={eventData?.seats} races={eventData?.heats} pilots={eventData?.pilots} classes={eventData?.classes} generators={HEAT_GEN}/>
    )},
    {label: "Mains", content: (
      <RaceRoundPanel title="Mains" seats={eventData?.seats} races={eventData?.mains} pilots={eventData?.pilots} classes={eventData?.classes} generators={MAIN_GEN}/>
    )}
  ];
  const tab = tabs[tabIndex];

  return (
    <Stack>
    <TextField label="Event name"/>
    <TextField label="Event description" multiline/>
    <TextField label="Event URL"/>
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
          {eventData?.seats?.map((fbc, idx) => {
            const deleteButton = idx > 0 ? <IconButton><DeleteIcon/></IconButton> : null;
            return <TableCell key={idx}>{deleteButton} Seat {idx+1}</TableCell>;
          })}
          <TableCell><IconButton><AddIcon/></IconButton></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
          {eventData?.seats?.map((fbc, idx) => {
            return <TableCell key={idx}><Frequency frequency={fbc.frequency.toString()} bandChannel={fbc?.bandChannel} vtxTable={vtxTable}/></TableCell>;
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
      eventData?.pilots && Object.entries(eventData.pilots).map((entry) => {
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
