import React, { useState, useEffect } from 'react';
import TextField from '@mui/material/TextField';

export default function ValidatingTextField(props) {
  const [value, setValue] = useState(props.value ?? '');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    setValue(props.value);
  }, [props.value]);

  const changeValue = (evt) => {
    if (props.validateChange) {
      const msg = props.validateChange(evt.target.value);
      setErrorMsg(msg);
    }
    setValue(evt.target.value);
  };
  return <TextField label={props.label} value={value} onChange={changeValue} error={errorMsg !== ''} helperText={errorMsg} inputProps={props.inputProps}/>;
}
