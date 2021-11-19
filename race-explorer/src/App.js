import React, { useState } from 'react';
import './App.css';
import AppBar from '@mui/material/AppBar';
import Button from '@mui/material/Button';
import Toolbar from '@mui/material/Toolbar';
import Race from './Race';
import Setup from './Setup';

const AppBarOffset = () => <Toolbar/>;

export default function App(props) {
  const [page, setPage] = useState('results');

  let pageButtons = [];
  let content;
  switch (page) {
    case 'results':
      pageButtons.push(<Button key="setup" color="inherit" variant="outlined" onClick={() => {setPage('setup')}}>Setup</Button>);
      content = <Race/>;
      break;
    case 'setup':
      pageButtons.push(<Button key="results" color="inherit" variant="outlined" onClick={() => {setPage('results')}}>Results</Button>);
      content = <Setup/>;
      break;
    default:
      content = <div/>;
  }

  return (
    <div className="App">
      <AppBar>
        <Toolbar>
          {pageButtons}
        </Toolbar>
      </AppBar>
      <AppBarOffset/>
      {content}
    </div>
  );
}
