import React, { useState, useEffect, useRef } from 'react';
import './Track.css';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
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
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import GpsFixedIcon from '@mui/icons-material/GpsFixed';
import GpsNotFixedIcon from '@mui/icons-material/GpsNotFixed';
import ValidatingTextField from './ValidatingTextField.js';
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

const saveTrackData = debounce(storeTrackData, 2000);

function copyLocation(loc, newVals) {
  if (!loc.id) {
    throw Error("Location missing ID");
  }
  return {
    id: loc.id,
    name: loc.name,
    type: loc.type,
    location: loc.location,
    ...newVals
  };
}

function updateLocation(layout, locIdx, newVals) {
  const newLayout = [...layout];
  const newLoc = copyLocation(layout[locIdx], newVals);
  newLayout[locIdx] = newLoc;
  return newLayout;
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
  const [locTypes, setLocTypes] = useState({});
  const [flyTo, setFlyTo] = useState(null);
  const newGateRef = useRef();

  useEffect(() => {
    newGateRef.current = 1;
  }, []);

  useEffect(() => {
    const loader = createTrackDataLoader();
    loader.load(null, (data) => {
      for (const loc of data.layout) {
        loc.id = loc.id ?? nanoid();
      }
      setCRS(data.crs);
      if (data.units) {
        setUnits(data.units);
      }
      setLocTypes(data.types);
      setTrackLayout(data.layout);
      const startPos = data.layout?.[0]?.location ?? [0,0];
      setFlyTo(startPos);
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    if (trackLayout.length > 0) {
      const data = {crs: crs, layout: trackLayout, types: locTypes};
      if (crs === LOCAL_GRID) {
        data.units = units;
      }
      saveTrackData(data);
    }
  }, [crs, units, locTypes, trackLayout]);

  const addLocation = () => {
    setTrackLayout((old) => {
      const newLayout = [...old];
      const newLocation = {id: nanoid(), name: "Gate "+(newGateRef.current++), type: locTypes[0], location: [5*old.length,0]};
      if (old.length > 0) {
        newLocation.type = old[old.length-1].type;
      }
      newLayout.push(newLocation);
      return newLayout;
     })
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
                return updateLocation(old, idx, {name: n});
              });
              return '';
            };
            const selectLocationType = (t) => {
              setTrackLayout((old) => {
                return updateLocation(old, idx, {type: t});
              });
            };
            const changeXLocation = (x) => {
              if (!x) {
                return 'Missing/invalid value';
              }
              setTrackLayout((old) => {
                return updateLocation(old, idx, {location: [Number(x), old[idx].location[1]]});
              });
              return '';
            };
            const changeYLocation = (y) => {
              if (!y) {
                return 'Missing/invalid value';
              }
              setTrackLayout((old) => {
                return updateLocation(old, idx, {location: [old[idx].location[0], Number(y)]});
              });
              return '';
            };
            const getCurrentPosition = (evt) => {
              setTrackLayout((old) => {
                return updateLocation(old, idx, {location: [evt.latlng.lat, evt.latlng.lng]});
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
                  Object.keys(locTypes).map((t) => {
                    return <MenuItem key={t} value={t}>{t}</MenuItem>;
                  })
                }
                </Select>
                </TableCell>
                <TableCell>
                <ValidatingTextField value={loc.location[0]} validateChange={changeXLocation}
                  inputProps={{type: 'number'}}/>
                <ValidatingTextField value={loc.location[1]} validateChange={changeYLocation}
                  inputProps={{type: 'number'}}/>
                <GpsButton map={map} onClick={getCurrentPosition} locateOptions={{setView:true, enableHighAccuracy: true}}/>
                </TableCell>
              </TableRow>
            );
          })
        }
        <TableRow><TableCell colSpan="4"><IconButton onClick={addLocation}><AddIcon/></IconButton>
</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
    )}
    </TrackMapContainer>
    <Map id="map"/>
    </Stack>
  );
}
