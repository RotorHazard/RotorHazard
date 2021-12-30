import React from 'react';
import { useDraggable, useSensors, useSensor, MouseSensor, TouchSensor, KeyboardSensor } from '@dnd-kit/core';

export function useDnDSensors() {
  return useSensors(
    useSensor(MouseSensor),
    useSensor(TouchSensor),
    useSensor(KeyboardSensor)
  );
}

export default function Draggable(props) {
  const {attributes, listeners, setNodeRef} = useDraggable({
    id: props.id,
    data: props.data
  });
  const style = {
    touchAction: 'none',
    ...props.style
  };

  return <button ref={setNodeRef} style={style} {...listeners} {...attributes}>{props.children}</button>;
}
