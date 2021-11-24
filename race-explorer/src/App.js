import React, { useState } from 'react';
import './App.css';
import AppBar from '@mui/material/AppBar';
import Button from '@mui/material/Button';
import Toolbar from '@mui/material/Toolbar';
import Results from './Results';
import Event from './Event';
import Setup from './Setup';
import Sensors from './Sensors';

const AppBarOffset = () => <Toolbar/>;

export default function App(props) {
  const [page, setPage] = useState('results');

  let pages = {
    results: {
      button: <Button key="results" disabled={page==='results'} color="inherit" variant="outlined" onClick={() => {setPage('results')}}>Results</Button>,
      content: <Results/>
    },
    event: {
      button: <Button key="event" disabled={page==='event'} color="inherit" variant="outlined" onClick={() => {setPage('event')}}>Event</Button>,
      content: <Event/>
    },
    setup: {
      button: <Button key="setup" disabled={page==='setup'} color="inherit" variant="outlined" onClick={() => {setPage('setup')}}>Setup</Button>,
      content: <Setup/>
    },
    sensors: {
      button: <Button key="sensors" disabled={page==='sensors'} color="inherit" variant="outlined" onClick={() => {setPage('sensors')}}>Sensors</Button>,
      content: <Sensors/>
    }
  };
  let content = <div/>;
  if (page in pages) {
    content = pages[page].content;
  }

  return (
    <div className="App">
      <AppBar>
        <Toolbar>
          {Object.values(pages).map((value) => {
            return value.button;
          })}
        </Toolbar>
      </AppBar>
      <AppBarOffset/>
      {content}
    </div>
  );
}
