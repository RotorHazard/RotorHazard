import React, { useState, useEffect, useRef } from 'react';
import './Track.css';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import AddLocationIcon from '@mui/icons-material/AddLocation';
import DeleteIcon from '@mui/icons-material/Delete';
import GpsFixedIcon from '@mui/icons-material/GpsFixed';
import GpsNotFixedIcon from '@mui/icons-material/GpsNotFixed';
import { TrackMapContainer, Map } from './TrackMap.js';
import { debounce } from 'lodash';
import { nanoid } from 'nanoid';
import { createTrackDataLoader, storeTrackData } from './rh-client.js';


const LOCAL_GRID = 'Local grid';

const CRSS = [
  LOCAL_GRID,
  "Lat/Long"
];

const UNITS = [
  "m",
  "ft"
];

const LOCATION_TYPES = [
  "Arch gate",
  "Square gate",
  "Flag"
];

const saveTrackData = debounce(storeTrackData, 2000);


function ValidatingTextField(props) {
  const [value, setValue] = useState(props?.value ?? '');
  const [errorMsg, setErrorMsg] = useState('');

  const changeValue = (evt) => {
    if (props?.validateChange) {
      const msg = props.validateChange(evt.target.value);
      setErrorMsg(msg);
    }
    setValue(evt.target.value);
  };
  return <TextField value={value} onChange={changeValue} error={errorMsg !== ''} helperText={errorMsg}/>;
}

function GpsButton(props) {
  const [state, setState] = useState('Not fixed');
  const map = props.map;
  const getCurrentPosition = () => {
    setState('Fixing');
    map.once('locationfound', (evt) => {
      if (props?.onClick) {
        setState('Fixed');
        props.onClick(evt);
      }
    });
    map.locate(props?.locateOptions ?? {});
  };
  const icon = (state === 'Fixed') ? <GpsFixedIcon/> : <GpsNotFixedIcon/>;
  const disabled = (state === 'Fixing');
  return (
    <Button startIcon={icon} disabled={disabled} onClick={getCurrentPosition}>Get position</Button>
  );
}


export default function Tracks(props) {
  const [trackLayout, setTrackLayout] = useState([]);
  const [crs, setCRS] = useState(CRSS[0]);
  const [units, setUnits] = useState(UNITS[0]);
  const [flyTo, setFlyTo] = useState(null);
  const newGateRef = useRef();

  useEffect(() => {
    newGateRef.current = 1;
  }, []);

  useEffect(() => {
    const loader = createTrackDataLoader();
    loader.load(null, (data) => {
      for (const loc of data.layout) {
        loc.id = loc?.id ?? nanoid();
      }
      setCRS(data.crs);
      if (data?.units) {
        setUnits(data?.units);
      }
      setTrackLayout(data.layout);
      const startPos = data?.layout?.[0]?.location ?? [0,0];
      setFlyTo(startPos);
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const data = {crs: crs, layout: trackLayout};
    if (crs === LOCAL_GRID) {
      data.units = units;
    }
    saveTrackData(data);
  }, [crs, units, trackLayout]);

  const addLocation = () => {
    setTrackLayout((old) => {return [...old, {id: nanoid(), name: "Gate "+(newGateRef.current++), type: LOCATION_TYPES[0], location: [5*old.length,0]}]})
  };

  const selectCRS = (newCrs) => {
    setCRS(newCrs);
  };

  let unitSelector = null;
  if (crs === LOCAL_GRID) {
    const selectUnits = (newUnits) => {
      setUnits(newUnits);
    };

    unitSelector = (
      <FormControl>
      <InputLabel id="units-label">Units</InputLabel>
      <Select labelId="units-label" value={units} onChange={(evt) => selectUnits(evt.target.value)}>
      {
        UNITS.map((units) => {
          return <MenuItem key={units} value={units}>{units}</MenuItem>
        })
      }
      </Select>
      </FormControl>
    );
  }

  return (
    <Stack>
    <Stack direction="row">
    <Button startIcon={<AddLocationIcon/>} onClick={addLocation}>Add</Button>
    <FormControl>
    <InputLabel id="crs-label">CRS</InputLabel>
    <Select labelId="crs-label" value={crs} onChange={(evt) => selectCRS(evt.target.value)}>
    {
      CRSS.map((crs) => {
        return <MenuItem key={crs} value={crs}>{crs}</MenuItem>
      })
    }
    </Select>
    </FormControl>
    {unitSelector}
    </Stack>
    <TrackMapContainer id="map" crs={crs} trackLayout={trackLayout} flyTo={flyTo}>
    {(map) => (
      <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell/>
            <TableCell>Name</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Location</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
        {
          trackLayout.map((loc, idx) => {
            const deleteLocation = () => {
              setTrackLayout((old) => {
                return old.filter((item,i) => i !== idx);
              });
            };
            let deleteControl;
            if (idx > 0) {
              deleteControl = <IconButton onClick={deleteLocation}><DeleteIcon/></IconButton>;
            } else {
              deleteControl = null;
            }
            const changeName = (n) => {
              if (n.trim() !== n) {
                return "Excess whitespace";
              }
              const existingIndex = trackLayout.findIndex((l) => l.name === n);
              if (existingIndex !== -1 && existingIndex !== idx) {
                return "Duplicate name";
              }
              setTrackLayout((old) => {
                const newData = [...old];
                newData[idx].name = n;
                return newData;
              });
              return '';
            };
            const selectLocationType = (t) => {
              setTrackLayout((old) => {
                const newData = [...old];
                newData[idx].type = t;
                return newData;
              });
            };
            const changeXLocation = (x) => {
              setTrackLayout((old) => {
                const newData = [...old];
                newData[idx].location[0] = x;
                return newData;
              });
            };
            const changeYLocation = (y) => {
              setTrackLayout((old) => {
                const newData = [...old];
                newData[idx].location[1] = y;
                return newData;
              });
            };
            const getCurrentPosition = (evt) => {
              setTrackLayout((old) => {
                const newData = [...old];
                newData[idx].location[0] = evt.latlng.lat;
                newData[idx].location[1] = evt.latlng.lng;
                return newData;
              });
            };
            return (
              <TableRow key={loc.id}>
                <TableCell>
                {deleteControl}
                </TableCell>
                <TableCell>
                <ValidatingTextField value={loc.name} validateChange={changeName}/>
                </TableCell>
                <TableCell>
                <Select value={loc.type} onChange={(evt) => selectLocationType(evt.target.value)}>
                {
                  LOCATION_TYPES.map((t) => {
                    return <MenuItem key={t} value={t}>{t}</MenuItem>;
                  })
                }
                </Select>
                </TableCell>
                <TableCell>
                <TextField value={loc.location[0]} onChange={(evt) => changeXLocation(evt.target.valueAsNumber)}
                  inputProps={{type: 'number'}}/>
                <TextField value={loc.location[1]} onChange={(evt) => changeYLocation(evt.target.valueAsNumber)}
                  inputProps={{type: 'number'}}/>
                <GpsButton map={map} onClick={getCurrentPosition} locateOptions={{setView:true, enableHighAccuracy: true}}/>
                </TableCell>
              </TableRow>
            );
          })
        }
        </TableBody>
      </Table>
    </TableContainer>
    )}
    </TrackMapContainer>
    <Map id="map"/>
    </Stack>
  );
}
