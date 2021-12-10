import React, { useState, useEffect } from 'react';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';

export function processVtxTable(data, vtxTable) {
  for (const band of data.vtx_table.bands_list) {
    vtxTable[band.letter] = {
      name: band.name,
      channels: band.frequencies.filter((f) => f > 0)
    };
  }
}

export default function Frequency(props) {
  const vtxTable = props.vtxTable;
  const [frequency, setFrequency] = useState(props.frequency);
  const [band, setBand] = useState(props.bandChannel?.[0] ?? '');
  const [channel, setChannel] = useState(props.bandChannel?.[1] ?? '');

  const frequencyChangesHook = props.frequencyChangesHook;
  useEffect(() => {
    if (frequencyChangesHook) {
      return frequencyChangesHook((freq) => {setFrequency(freq); setBand(''); setChannel('');});
    }
  }, [frequencyChangesHook]);

  const bandChannelChangesHook = props.bandChannelChangesHook;
  useEffect(() => {
    if (bandChannelChangesHook) {
      return bandChannelChangesHook((bandChannel) => {setBand(bandChannel[0]); setChannel(bandChannel[1]);});
    }
  }, [bandChannelChangesHook]);

  const changeFrequency = (frequency) => {
    setFrequency(frequency);
    setBand('');
    setChannel('');
    if (props.onChange) {
      props.onChange(frequency, '');
    }
  };

  const selectBand = (band) => {
    setBand(band);
    if (band !== '' && channel !== '') {
      const freq = vtxTable[band].channels[Number(channel)-1];
      setFrequency(freq)
      if (props.onChange) {
        props.onChange(freq, band+channel);
      }
    }
  };

  const selectChannel = (channel) => {
    setChannel(channel);
    if (band !== '' && channel !== '') {
      const freq = vtxTable[band].channels[Number(channel)-1];
      setFrequency(freq)
      if (props.onChange) {
        props.onChange(freq, band+channel);
      }
    }
  };

  return (
    <div>
    <FormControl>
    <InputLabel id="band-label">Band</InputLabel>
    <Select labelId="band-label" value={band} defaultValue=""
    onChange={(evt) => selectBand(evt.target.value)}>
    {Object.entries(vtxTable).map((entry) => {
      const band = entry[0];
      return (
        <Tooltip key={band} value={band} title={entry[1].name}>
        <MenuItem>{band}</MenuItem>
        </Tooltip>
      );
    })}
    </Select>
    </FormControl>
    <FormControl>
    <InputLabel id="channel-label">Channel</InputLabel>
    <Select labelId="channel-label" value={channel} defaultValue=""
    onChange={(evt) => selectChannel(evt.target.value)}>
    {band in vtxTable && vtxTable[band].channels.map((freq, idx) => {
      const chan = idx + 1;
      return (
        <Tooltip key={chan} value={chan} title={freq}>
        <MenuItem>{chan}</MenuItem>
        </Tooltip>
      );
    })}
    </Select>
    </FormControl>
    <TextField label="Frequency" helperText="0 to disable"
      value={frequency}
      onChange={(evt) => changeFrequency(evt.target.value)}
      inputProps={{
      step: 5,
      min: 5645,
      max: 5945,
      type: 'number',
      maxLength: 4
    }}/>
    </div>
  );
}
