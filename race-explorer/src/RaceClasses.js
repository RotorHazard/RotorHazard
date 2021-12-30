import React, { useState, useEffect, forwardRef } from 'react';
import Stack from '@mui/material/Stack';
import TreeItem, { useTreeItem } from '@mui/lab/TreeItem';
import TreeView from '@mui/lab/TreeView';
import IconButton from '@mui/material/IconButton';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { DndContext, DragOverlay, useDroppable } from '@dnd-kit/core';
import clsx from 'clsx';
import ValidatingTextField from './ValidatingTextField.js';
import Draggable, { useDnDSensors } from './Draggable.js';
import { createRaceClassLoader, storeRaceClasses } from './rh-client.js';
import { debounce } from 'lodash';

let newClassCounter = 1;

const saveRaceClasses = debounce(storeRaceClasses, 2000);

function RaceClassPanel(props) {
  const [raceClassName, setRaceClassName] = useState('');
  const [raceClassDesc, setRaceClassDesc] = useState('');

  useEffect(() => {
    setRaceClassName(props.raceClass?.[0] ?? '');
    setRaceClassDesc(props.raceClass?.[1]?.description ?? '');
  }, [props.raceClass]);

  const changeName = (newName) => {
    setRaceClassName(newName);
    if (props.onChange) {
      props.onChange(newName, {});
    }
    return '';
  };
  const changeDesc = (newDesc) => {
    setRaceClassDesc(newDesc);
    if (props.onChange) {
      props.onChange(raceClassName, {description: newDesc});
    }
    return '';
  };
  return (
    <Stack>
    <ValidatingTextField label="Name" value={raceClassName} validateChange={changeName}/>
    <ValidatingTextField label="Description" multiline value={raceClassDesc} validateChange={changeDesc}/>
    </Stack>
  );
}

function RaceClass(props) {
  return <div className={props.className}>{props.name}</div>;
}

function DraggableNode(props) {
  const data = {};
  const style = {
    display: 'block',
    margin: '0 auto',
    minWidth: '5em',
    minHeight: '1em'
  };
  return <Draggable id={props.id} data={data} style={style}>{props.children}</Draggable>;
}

function DroppableNode(props) {
  const {isOver, setNodeRef} = useDroppable({
    id: props.id,
    data: {}
  });
  const style = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    border: isOver ? '1px solid red' : '1px solid black',
    borderTopLeftRadius: '5px', borderTopRightRadius: '5px',
    borderBottomLeftRadius: '5px', borderBottomRightRadius: '5px',
    minWidth: '5em',
    minHeight: isOver ? '4em' : '2em'
  };
  return (
    <div ref={setNodeRef} style={style}>{props.children}</div>
  );
}

const RootNode = forwardRef(function RootNode(props, ref) {
  const {
    classes,
    className,
    nodeId,
    icon: iconProp,
    expansionIcon,
    displayIcon
  } = props;
  const {
    disabled,
    expanded,
    selected,
    focused
  } = useTreeItem(nodeId);
  const icon = iconProp || expansionIcon || displayIcon;
  return (
    <div ref={ref}
     className={clsx(className, classes.root, {
        [classes.expanded]: expanded,
        [classes.selected]: selected,
        [classes.focused]: focused,
        [classes.disabled]: disabled,
      })}
    >
    <div className={classes.iconContainer}>
    {icon}
    </div>
    <DroppableNode id={nodeId}>
    </DroppableNode>
    </div>
  );
});

const RaceClassNode = forwardRef(function RaceClassNode(props, ref) {
  const {
    classes,
    className,
    label,
    nodeId,
    icon: iconProp,
    expansionIcon,
    displayIcon
  } = props;
  const {
    disabled,
    expanded,
    selected,
    focused,
    handleExpansion,
    handleSelection
  } = useTreeItem(nodeId);
  const icon = iconProp || expansionIcon || displayIcon;
  return (
    <div ref={ref}
     className={clsx(className, classes.root, {
        [classes.expanded]: expanded,
        [classes.selected]: selected,
        [classes.focused]: focused,
        [classes.disabled]: disabled,
      })}
    >
    <div onClick={handleExpansion} className={classes.iconContainer}>
    {icon}
    </div>
    <div onMouseDown={handleSelection}>
    <DroppableNode id={nodeId}>
    <DraggableNode id={nodeId}>
    <RaceClass name={label} className={classes.label}/>
    </DraggableNode>
    </DroppableNode>
    </div>
    <IconButton onClick={props.onDelete}><DeleteIcon/></IconButton>
    </div>
  );
});

export default function RaceClasses(props) {
  const [raceClasses, setRaceClasses] = useState({});
  const [selectedRaceClass, setSelectedRaceClass] = useState();
  const [draggingRaceClass, setDraggingRaceClass] = useState(null);

  const sensors = useDnDSensors();

  useEffect(() => {
    const loader = createRaceClassLoader();
    loader.load(null, (data) => {
      setRaceClasses(data.classes);}
    );
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    saveRaceClasses({classes: raceClasses});
  }, [raceClasses]);

  const nodesByName = {};
  const q = [];
  const rootRaceClassEntries = Object.entries(raceClasses);
  rootRaceClassEntries.forEach((e) => {
    nodesByName[e[0]] = {content: e[1], parent: null};
  });
  q.push(...rootRaceClassEntries);
  while (q.length > 0) {
    const raceClassEntry = q.pop();
    const raceClass = raceClassEntry[1];
    const childRaceClassEntries = Object.entries(raceClass.children);
    childRaceClassEntries.forEach((e) => {
      nodesByName[e[0]] = {content: e[1], parent: raceClassEntry};
    });
    q.push(...childRaceClassEntries);
  }

  const treeRenderer = (raceClasses) => {
    return Object.entries(raceClasses).map((e) => {
      const raceClassName = e[0];
      const raceClass = e[1];
      const deleteNode = (evt) => {
        const node = nodesByName[raceClassName];
        let parentMap;
        if (node.parent) {
          parentMap = node.parent[1].children;
        } else {
          parentMap = raceClasses;
        }
        delete parentMap[raceClassName];
        setRaceClasses((old) => {return {...old};});
        if (raceClassName === selectedRaceClass?.[0]) {
          setSelectedRaceClass(node.parent);
        }
      };
      return (
        <TreeItem key={raceClassName} nodeId={raceClassName} label={raceClassName} sx={{textAlign: 'left'}} ContentComponent={RaceClassNode} ContentProps={{onDelete: deleteNode}}>
          {treeRenderer(raceClass.children)}
          <TreeItem nodeId={raceClassName + '.add'} icon={<AddIcon/>}/>
        </TreeItem>
      );
    });
  };

  const nodeSelected = (evt, nodeId) => {
    if (nodeId.endsWith('.add')) {
      const raceClassName = nodeId.substring(0, nodeId.length-4);
      let parentMap;
      if (raceClassName.length > 0) {
        const parentRaceClass = nodesByName[raceClassName].content;
        parentMap = parentRaceClass.children;
      } else {
        parentMap = raceClasses;
      }
      const newRaceClassName = 'New class ' + (newClassCounter++);
      const newRaceClass = {description: '', children: {}};
      parentMap[newRaceClassName] = newRaceClass;
      setRaceClasses((old) => {return {...old};});
    } else if (!nodeId.startsWith('.')) {
      const raceClass = nodesByName[nodeId].content;
      setSelectedRaceClass([nodeId, raceClass]);
    }
  };

  const updateRaceClass = (raceClassName, newVals) => {
    const oldRaceClassName = selectedRaceClass[0];
    const parentEntry = nodesByName[oldRaceClassName].parent;
    let parentMap;
    if (parentEntry !== null) {
      parentMap = parentEntry[1].children;
    } else {
      parentMap = raceClasses;
    }
    const currentRaceClass = parentMap[oldRaceClassName];
    delete parentMap[oldRaceClassName];
    Object.assign(currentRaceClass, newVals);
    parentMap[raceClassName] = currentRaceClass;
    setRaceClasses((old) => {return {...old};});
    setSelectedRaceClass([raceClassName, currentRaceClass]);
  };

  const onDragStart = (evt) => {
    setDraggingRaceClass(evt.active.id);
  };
  const onDragCancel = (evt) => {
    setDraggingRaceClass(null);
  };
  const onDragEnd = (evt) => {
    setDraggingRaceClass(null);
    if (evt.over) {
      const srcRaceClassName = evt.active.id;
      const dstRaceClassName = evt.over.id;
      if (srcRaceClassName !== dstRaceClassName) {
        const srcNode = nodesByName[srcRaceClassName];
        let parentMap;
        if (srcNode.parent) {
          parentMap = srcNode.parent[1].children;
        } else {
          parentMap = raceClasses;
        }
        delete parentMap[srcRaceClassName];
        if (dstRaceClassName === '.root') {
          parentMap = raceClasses;
        } else {
          const dstNode = nodesByName[dstRaceClassName];
          parentMap = dstNode.content.children;
        }
        parentMap[srcRaceClassName] = srcNode.content;
        setRaceClasses((old) => {return {...old};});
      }
    }
  };
  return (
    <Stack direction="row">
    <DndContext onDragStart={onDragStart} onDragCancel={onDragCancel} onDragEnd={onDragEnd} sensors={sensors}>
    <TreeView defaultExpanded={['.root']} defaultCollapseIcon={<ExpandMoreIcon />} defaultExpandIcon={<ChevronRightIcon />} onNodeSelect={nodeSelected}>
    <TreeItem nodeId='.root' ContentComponent={RootNode}>
    {treeRenderer(raceClasses)}
    <TreeItem nodeId='.add' icon={<AddIcon/>}/>
    </TreeItem>
    </TreeView>
    <DragOverlay wrapperElement="button" dropAnimation={null}>
    {draggingRaceClass ? <RaceClass name={draggingRaceClass}/> : null}
    </DragOverlay>
    </DndContext>
    <RaceClassPanel raceClass={selectedRaceClass} onChange={updateRaceClass}/>
    </Stack>
  );
}