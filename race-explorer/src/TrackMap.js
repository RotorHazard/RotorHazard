import React, { useEffect, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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

export function TrackMapContainer(props) {
  const [map, setMap] = useState(null);

  useEffect(() => {
    let map;
    if (props.crs === LOCAL_GRID) {
      map = L.map(props.id, {
        crs: L.CRS.Simple,
        center: [0,0],
        zoom: 4
       });
    } else {
      map = L.map(props.id, {
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
    setMap(map);
    return () => {
      map.remove();
    }
  }, [props.id, props.crs]);

  useEffect(() => {
      if (map) {
        for (const loc of props.trackLayout) {
          L.marker(loc.location, {title: loc.name}).addTo(map.trackLayer);
        }
        return () => {map.trackLayer.clearLayers()};
      }
  }, [map, props.trackLayout]);

  useEffect(() => {
    if (map && props?.flyTo) {
      map.flyTo(props.flyTo);
    }
  }, [map, props.flyTo]);

  return props.children(map);
}

export function Map(props) {
  return <div id={props.id}/>
}
