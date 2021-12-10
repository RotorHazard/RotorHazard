import React, { useState } from 'react';
import './App.css';
import AppBar from '@mui/material/AppBar';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Results from './Results';
import Event from './Event';
import RaceClasses from './RaceClasses';
import Pilots from './Pilots';
import Track from './Track';
import Setup from './Setup';
import Sensors from './Sensors';

const AppBarOffset = () => <Tabs/>;

export default function App(props) {
  const [tabIndex, setTabIndex] = useState(0);

  const tabs = [
    {label: "Results", content: <Results/>},
    {label: "Event", content: <Event/>},
    {label: "Classes", content: <RaceClasses/>},
    {label: "Pilots", content: <Pilots/>},
    {label: "Track", content: <Track/>},
    {label: "Setup", content: <Setup/>},
    {label: "Sensors", content: <Sensors/>}
  ];

  const tab = tabs[tabIndex];

  return (
    <div className="App">
      <AppBar>
        <Tabs value={tabIndex} textColor="inherit" indicatorColor="secondary" onChange={(evt,idx)=>{setTabIndex(idx)}}>
        {
          tabs.map((entry) => {
            return <Tab key={entry.label} label={entry.label}/>;
          })
        }
        </Tabs>
      </AppBar>
      <AppBarOffset/>
      {tab.content}
    </div>
  );
}
