import React, { useState, useEffect } from 'react';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import { loadEventData } from './rh-client.js';

export default function Event(props) {
  const [eventData, setEventData] = useState({});
  const heats = [1];
  const seats = [1, 2, 3, 4, 5, 6];

  useEffect(() => {
    loadEventData(setEventData);
  }, []);

  return (
    <Stack direction="row">
    <div>
    <div>Pilots</div>
    <List>
    {
      Object.entries(eventData).map((entry) => {
        return <ListItem key={entry[0]}>
        <ListItemText>{entry[0]}</ListItemText>
        </ListItem>;
      })
    }
    </List>
    </div>
    <div>
    <div>Heats</div>
    <List>
    {
      heats.map((heat) => {
        return (
          <div>
          Heat {heat}
          <List component={Stack} direction="row">
          {
            seats.map((seat) => {
              return <ListItemText>Seat {seat}</ListItemText>;
            })
          }
          </List>
          </div>
        );
      })
    }
    </List>
    </div>
    </Stack>
  );
}
