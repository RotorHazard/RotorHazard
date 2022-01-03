import React, { useState, useEffect } from 'react';
import TextField from '@mui/material/TextField';

export default function ValidatingTextField(props) {
  const {value: givenValue, validateChange} = props;
  const [value, setValue] = useState(givenValue ?? '');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    setValue(givenValue);
  }, [givenValue]);

  const changeValue = (evt) => {
    if (validateChange) {
      const msg = validateChange(evt.target.value);
      setErrorMsg(msg);
    }
    setValue(evt.target.value);
  };

  const tfProps = {...props};
  delete tfProps.validateChange;

  return <TextField {...tfProps} value={value} onChange={changeValue} error={errorMsg !== ''} helperText={errorMsg}/>;
}
