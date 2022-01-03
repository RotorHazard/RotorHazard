import React, { useEffect, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import iconRetina from 'leaflet/dist/images/marker-icon-2x.png';

import droneIcon from './drone.png';

L.Marker.prototype.options.icon = L.icon({
  ...L.Icon.Default.prototype.options,
  iconUrl: icon,
  iconRetinaUrl: iconRetina,
  shadowUrl: iconShadow
});

const DRONE_ICON = L.icon({
  iconUrl: droneIcon,
  iconSize: [24,24],
  iconAnchor: [24,12]
});

const LAT_LONG = 'Lat/Long';

export function TrackMapContainer(props) {
  const {id, crs, units, trackLayout, pilotPositions, flyTo, children} = props;
  const [map, setMap] = useState(null);

  useEffect(() => {
    let map;
    if (crs === LAT_LONG) {
      map = L.map(id, {
        center: [0,0],
        zoom: 16,
        layers: [
          L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
            attribution:
              '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
          }),
        ]
      });
    } else {
      map = L.map(id, {
        crs: L.CRS.Simple,
        center: [0,0],
        zoom: 4
       });
       const grid_5m = L.featureGroup();
       const spacing = (units === 'ft') ? 16.4 : 5;
       for (let i=0; i<51; i++) {
         L.polyline([[spacing*(i-25), -25*spacing], [spacing*(i-25), 25*spacing]], {color: 'gray', weight: 1}).addTo(grid_5m);
         L.polyline([[-25*spacing, spacing*(i-25)], [25*spacing, spacing*(i-25)]], {color: 'gray', weight: 1}).addTo(grid_5m);
       }
       grid_5m.addTo(map);
    }
    map.trackLayer = L.featureGroup();
    map.trackLayer.addTo(map);
    map.pilotLayer = L.featureGroup();
    map.pilotLayer.addTo(map);
    setMap(map);
    return () => {
      map.remove();
    }
  }, [id, crs, units]);

  useEffect(() => {
      if (map && trackLayout) {
        for (const loc of trackLayout) {
          L.marker(loc.location, {title: loc.name}).addTo(map.trackLayer);
        }
        return () => {map.trackLayer.clearLayers()};
      }
  }, [map, trackLayout]);

  useEffect(() => {
      if (map && trackLayout && pilotPositions) {
        Object.entries(pilotPositions).forEach((entry) => {
          L.marker(entry[1], {title: entry[0], icon: DRONE_ICON, pane: 'tooltipPane'}).addTo(map.pilotLayer);
        });
        return () => {map.pilotLayer.clearLayers()};
      }
  }, [map, trackLayout, pilotPositions]);

  useEffect(() => {
    if (map && flyTo) {
      map.flyTo(flyTo);
    }
  }, [map, flyTo]);

  return children ? children(map) : <></>;
}

export function Map(props) {
  return <div id={props.id}/>
}
