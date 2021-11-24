import React, { useState, useEffect } from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import { loadMqttConfig, getMqttClient } from './rh-client.js';


function getSensorListener(setSensors) {
  return (topic, payload) => {
    const parts = topic.split('/');
    const sensorName = parts[parts.length-2];
    const readingName = parts[parts.length-1];
    const value = new TextDecoder('UTF-8').decode(payload);
    const unitSep = value.lastIndexOf(' ');
    let reading = {};
    if (unitSep >= 0) {
      reading.value = value.substring(0, unitSep);
      reading.units = value.substring(unitSep+1);
    } else {
      reading.value = value;
    }
    const newData = {[sensorName]: {[readingName]: reading}};
    setSensors((prevData) => {return {...prevData, ...newData};});
  };
}

export default function Sensors(props) {
  const [mqttConfig, setMqttConfig] = useState({});
  const [sensors, setSensors] = useState({});

  useEffect(() => {
    loadMqttConfig(setMqttConfig);
  }, []);

  useEffect(() => {
    if (mqttConfig?.sensorAnnTopic) {
      const listener = getSensorListener(setSensors);
      const mqttClient = getMqttClient();
      mqttClient.on('message', listener);
      mqttClient.subscribe(mqttConfig.sensorAnnTopic+'/#');
      return () => {
        mqttClient.unsubscribe(mqttConfig.sensorAnnTopic+'/#');
        mqttClient.off('message', listener);
      };
    }
  }, [mqttConfig, sensors]);

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Sensor</TableCell>
            <TableCell>Reading</TableCell>
            <TableCell>Value</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
        {
          Object.entries(sensors).map((sensorEntry) => {
            const sensorName = sensorEntry[0];
            const readings = Object.entries(sensorEntry[1]);
            let sensorCell = <TableCell rowSpan={readings.length}>{sensorName}</TableCell>;
            return readings.map((readingEntry) => {
              const readingName = readingEntry[0];
              const readingData = readingEntry[1];
              let value = readingData.value;
              if ('units' in readingData) {
                value  += readingData.units;
              }
              const firstCell = sensorCell;
              sensorCell = null;
              return (
                <TableRow>
                {firstCell}
                <TableCell>{readingName}</TableCell>
                <TableCell>{value}</TableCell>
                </TableRow>
              );
            });
          })
        }
        </TableBody>
      </Table>
    </TableContainer>
  );
}