import React, { useState, useEffect } from 'react';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ValidatingTextField from './ValidatingTextField.js';
import Pilot from './Pilot.js';
import { debounce } from 'lodash';
import {
  createPilotDataLoader, storePilotData
} from './rh-client.js';

const savePilotData = debounce(storePilotData, 2000);

let pilotCounter = 1;

function PilotPanel(props) {
  const [callsign, setCallsign] = useState('');
  const [pilotName, setPilotName] = useState('');

  useEffect(() => {
    setCallsign(props.pilot?.[0] ?? '');
    setPilotName(props.pilot?.[1]?.name ?? '');
  }, [props.pilot]);

  const changeCallsign = (callsign) => {
    setCallsign(callsign);
    if (props.onChange) {
      props.onChange(callsign, {});
    }
    return '';
  };
  const changeName = (newName) => {
    setPilotName(newName);
    if (props.onChange) {
      props.onChange(callsign, {name: newName});
    }
    return '';
  };
  return (
    <Stack>
    <ValidatingTextField label="Callsign" value={callsign} validateChange={changeCallsign}/>
    <ValidatingTextField label="Name" value={pilotName} validateChange={changeName}/>
    </Stack>
  );
}

export default function Pilots(props) {
  const [pilots, setPilots] = useState({});
  const [selectedPilot, setSelectedPilot] = useState();

  useEffect(() => {
    const loader = createPilotDataLoader();
    loader.load(null, (data) => {
      setPilots(data.pilots);
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    savePilotData({pilots: pilots})
  }, [pilots]);

  const updatePilot = (callsign, newVals) => {
    const oldCallsign = selectedPilot[0];
    const currentPilot = pilots[oldCallsign];
    delete pilots[oldCallsign];
    Object.assign(currentPilot, newVals);
    pilots[callsign] = currentPilot;
    setPilots({...pilots});
    setSelectedPilot([callsign, currentPilot]);
  };

  const addPilot = (evt) => {
    const callsign = 'New pilot ' + (pilotCounter++);
    const pilot = {name: ''};
    pilots[callsign] = pilot;
    setPilots({...pilots});
    setSelectedPilot([callsign, pilot]);
  };

  return (
    <Stack direction="row">
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
        <TableRow><TableCell/><TableCell>Callsign</TableCell></TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell>
              <IconButton onClick={addPilot}><AddIcon/></IconButton>
            </TableCell>
            <TableCell/>
          </TableRow>
        {
          pilots && Object.entries(pilots).map((entry) => {
            const callsign = entry[0];
            const selectPilot = (evt) => {
              setSelectedPilot([callsign, pilots[callsign]]);
            };
            const deletePilot = (evt) => {
              delete pilots[callsign];
              setPilots({...pilots});
              setSelectedPilot(null);
            };
            return (
              <TableRow key={callsign}>
              <TableCell>
                <IconButton onClick={deletePilot}><DeleteIcon/></IconButton>
              </TableCell>
              <TableCell>
                <Button onClick={selectPilot}><Pilot callsign={callsign}/></Button>
              </TableCell>
              </TableRow>
            );
          })
        }
        </TableBody>
      </Table>
    </TableContainer>
    <PilotPanel pilot={selectedPilot} onChange={updatePilot}/>
    </Stack>
  );
}