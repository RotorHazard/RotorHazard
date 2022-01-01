import React, { forwardRef } from 'react';
import { useTreeItem } from '@mui/lab/TreeItem';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import clsx from 'clsx';

const TreeNode = forwardRef(function TreeNode(props, ref) {
  const {
    classes,
    className,
    nodeId,
    icon: iconProp,
    expansionIcon,
    displayIcon,
    render,
    onDelete,
    disableExpansion,
    disableSelection
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
  const noAction = () => {};
  const expandAction = disableExpansion ? noAction : handleExpansion;
  const selectAction = disableSelection ? noAction : handleSelection;
  return (
    <div ref={ref}
     className={clsx(className, classes.root, {
        [classes.expanded]: expanded,
        [classes.selected]: selected,
        [classes.focused]: focused,
        [classes.disabled]: disabled,
      })}
    >
    <div onClick={expandAction} className={classes.iconContainer}>
    {icon}
    </div>
    <div onMouseDown={selectAction}>
    {render(props)}
    </div>
    {onDelete && <IconButton onClick={onDelete}><DeleteIcon/></IconButton>}
    </div>
  );
});

export default TreeNode;
