import React, { useState, useEffect } from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import { createMqttConfigLoader, getMqttClient } from './rh-client.js';


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
    const loader = createMqttConfigLoader();
    loader.load(null, setMqttConfig);
    return () => loader.cancel();
  }, []);

  let mqttSubscriber = null;
  if (mqttConfig?.sensorAnnTopic) {
    mqttSubscriber = (setSensors) => {
      const listener = getSensorListener(setSensors);
      const mqttClient = getMqttClient();
      mqttClient.on('message', listener);
      mqttClient.subscribe(mqttConfig.sensorAnnTopic+'/#');
      return () => {
        mqttClient.unsubscribe(mqttConfig.sensorAnnTopic+'/#');
        mqttClient.off('message', listener);
      };
    };
  }

  useEffect(() => {
    if (mqttSubscriber) {
      return mqttSubscriber(setSensors);
    }
  }, [mqttSubscriber]);

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
              const value = readingData.value;
              const units = readingData?.units ?? '';
              let displayValue;
              switch (readingName) {
                case 'voltage':
                  displayValue = Number(value).toFixed(2) + units;
                  break;
                case 'current':
                  displayValue = Number(value).toFixed(0) + units;
                  break;
                case 'power':
                  displayValue = Number(value).toFixed(0) + units;
                  break;
                case 'temperature':
                  displayValue = Number(value).toFixed(1) + units;
                  break;
                case 'humidity':
                  displayValue = Number(value).toFixed(1) + units;
                  break;
                case 'pressure':
                  displayValue = Number(value).toFixed(1) + units;
                  break;
                case 'capacity':
                  displayValue = Number(value).toFixed(0) + units;
                  break;
                default:
                  displayValue = value + units;
              }

              const firstCell = sensorCell;
              sensorCell = null;
              return (
                <TableRow>
                {firstCell}
                <TableCell>{readingName}</TableCell>
                <TableCell>{displayValue}</TableCell>
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