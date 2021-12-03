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
import { debounce } from 'lodash';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { createTrackDataLoader, storeTrackData } from './rh-client.js';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import iconRetina from 'leaflet/dist/images/marker-icon-2x.png';
L.Marker.prototype.options.icon = L.icon({
  ...L.Icon.Default.prototype.options,
  iconUrl: icon,
  iconRetinaUrl: iconRetina,
  shadowUrl: iconShadow
});

const LOCAL_GRID = 'Local grid';

const CRSS = [
  LOCAL_GRID,
  "Lat/Long"
];

const UNITS = [
  "m",
  "ft"
];

const ELEMENT_TYPES = [
  "Arch gate",
  "Square gate",
  "Flag"
];

const saveTrackData = debounce(storeTrackData, 2000);

export default function Tracks(props) {
  const [trackLayout, setTrackLayout] = useState([]);
  const [crs, setCRS] = useState(CRSS[0]);
  const [units, setUnits] = useState(UNITS[0]);
  const mapRef = useRef();
  const newGateRef = useRef();

  useEffect(() => {
    newGateRef.current = 1;
  }, []);

  useEffect(() => {
    let map;
    if (crs === LOCAL_GRID) {
      map = L.map('map', {
        crs: L.CRS.Simple,
        center: [0,0],
        zoom: 4
       });
    } else {
      map = L.map('map', {
        center: [0,0],
        zoom: 16,
        layers: [
          L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
            attribution:
              '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
          }),
        ]
      });
    }
    map.trackLayer = L.featureGroup();
    map.trackLayer.addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
    }
  }, [crs]);

  useEffect(() => {
    const loader = createTrackDataLoader();
    loader.load(null, (data) => {
      if (mapRef.current) {
        const center = data?.layout?.[0]?.location ?? [0,0];
        mapRef.current.flyTo(center);
      }
      setCRS(data.crs);
      setUnits(data?.units ?? '');
      setTrackLayout(data.layout);
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (map) {
      for (const loc of trackLayout) {
        L.marker(loc.location, {title: loc.name}).addTo(map.trackLayer);
      }
    }
    return () => {if (map) {map.trackLayer.clearLayers()}};
  }, [trackLayout]);

  useEffect(() => {
    const data = {crs: crs, layout: trackLayout};
    if (crs === LOCAL_GRID) {
      data.units = units;
    }
    saveTrackData(data);
  }, [crs, units, trackLayout]);

  const addLocation = () => {
    setTrackLayout((old) => {return [...old, {name: "Gate "+(newGateRef.current++), type: ELEMENT_TYPES[0], location: [5*old.length,0]}]})
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
            const changeName = (n) => {
              setTrackLayout((old) => {
                const newData = [...old];
                newData[idx].name = n;
                return newData;
              });
            };
            const selectElementType = (t) => {
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
            let deleteControl;
            if (idx > 0) {
              deleteControl = <IconButton onClick={deleteLocation}><DeleteIcon/></IconButton>;
            } else {
              deleteControl = null;
            }
            return (
              <TableRow key={loc.name}>
                <TableCell>
                {deleteControl}
                </TableCell>
                <TableCell><TextField value={loc.name} onChange={(evt) => changeName(evt.target.value)}/></TableCell>
                <TableCell>
                <Select value={loc.type} onChange={(evt) => selectElementType(evt.target.value)}>
                {
                  ELEMENT_TYPES.map((t) => {
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
                </TableCell>
              </TableRow>
            );
          })
        }
        </TableBody>
      </Table>
    </TableContainer>
    <div id="map"/>
    </Stack>
  );
}