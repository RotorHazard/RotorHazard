import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import Demo from './Demo';
import './App.css';

const Root = window.location.pathname === '/demo' ? Demo : App;

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
