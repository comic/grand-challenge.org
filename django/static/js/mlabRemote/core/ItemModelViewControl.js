//=============================================================================
// MLABMLItemModelViewControl
//=============================================================================
function MLABMLItemModelViewControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);

  this.setup = function(parentControl) {
    self.setupWidgetControl("MLABMLItemModelViewControl", parentControl);
    
    self._idAttribute = self.getMDLAttribute("idAttribute", null);
    self._idAsFullPath = mlabIsTrue(self.getMDLAttribute("idAsFullPath", "false"));
    self._idPathSeparator = self.getMDLAttribute("idPathSeparator", "/");
    self._idSeperator = self.getMDLAttribute("idSeparator", ";");
    self._showHeader = mlabIsTrue(self.getMDLAttribute("header", "true"));
    
    // these fields may be null if not specified
    self._currentField = self.getMDLFieldAttribute("currentField");    
    self._selectionField = self.getMDLFieldAttribute("selectionField");
    
    // store a map of which columns to update when an attribute changes -
    // the object stores a map from attribute names to bitsets (stored as numbers)
    // (this restricts the number of columns to a probably small number)
    self._columnUpdateMap = new Object();
    
    // store derived attributes information
    self._derivedAttributes = new Object();
    self._parseDerivedAttributes();
    
    self._createTable();  // sets self._columns, self._table and self._tableBody

    // sorting   
    self._sortAttributes = new Array(); // this will be set when the sort column changes
    self._sortColumn = -1;  // -1 means unsorted
    self._sortInverted = 1; // this is just a multiplicator, 1 means not inverted, -1 is inverted
    
    var sortByColumn = self.getMDLAttribute("sortByColumn", "-1");  // -1 means unsorted
    var sortAscending = self.getMDLAttribute("sortAscending", "true");
    self._setSorting(new Number(sortByColumn), mlabIsTrue(sortAscending) ? 1 : -1);
    
    // item model will be null initially (implementation will be provided by ItemModelHandler)
    self._model = null;
    
    // update field value
    self.fieldChanged(self._field);
  };

  this.setupTypicalTags = function() {
    self._width = self.getMDLAttribute("w", null);
    if (self._width) { self._domElement.style.width = self._width + "px"; }
    self._height = self.getMDLAttribute("h", null);
    if (self._height) { self._domElement.style.height = self._height + "px"; }
  };
  
  // check if an attribute even exists:
  this._checkAttributeName = function(attrName) {
    if (attrName && attrName !== true && !self._model.hasAttribute(attrName) &&
        !(attrName in self._derivedAttributes))
    {
      self._moduleContext.logError("MLABMLItemModelViewControl: " +
                                   "no such attribute in model: '" + attrName + "'"); 
    }
  }
  
  // warn about unknown attribute when the model changes:
  this._checkTable = function() {
    for (var i=0; i<self._columns.length; i++) {
      var column = self._columns[i];
      self._checkAttributeName(column.displayAttribute);
      self._checkAttributeName(column.checkboxAttribute);
      self._checkAttributeName(column.iconAttribute);
    }
    for (var derivedAttribute in self._derivedAttributes) {
      self._checkAttributeName(derivedAttribute.sourceAttribute);
    }
  }
  
  this.fieldChanged = function(field) {
    if (self._model) {
      self._model.removeListener(self)
      // remove everything unter the root item:
      self._removeSubRowsOf(null, true)
    }
      
    if (field && field.isBaseField()) {
      self._model = field.getValue();
    } else {
      // this should rarely happen - but we handle it, too
      self._model = null;
    }
    
    // remember in a map which items have been expanded
    self._expandedIDs = new Object();

    // remember in a map which items have been expanded
    self._selectedIDs = new Object();

    // mapping of item ids to row elements
    self._rowMap = new Object();
    
    if (self._model) {
      self._checkTable();
      self._model.addListener(self)
      // add all direct children of the root item:
      self._populateRow(null)
    }
  }
  
  this._columnUsesAttribute = function(column, attributeName) {
    if (attributeName in self._derivedAttributes) {
      var derivedAttribute = self._derivedAttributes[attributeName];
      self._columnUsesAttribute(column, derivedAttribute.sourceAttribute);
    } else if (attributeName) {
      var columns = (attributeName in self._columnUpdateMap) ? self._columnUpdateMap[attributeName] : 0;
      columns = columns & (1 << column);
      self._columnUpdateMap[attributeName] = columns;
    }
  }
  
  this._parseDerivedAttributes = function() {
    var derivedAttributeTrees = mlabGetMDLChildren(self._mdlTree, "DerivedAttribute");
    for (var i=0; i<derivedAttributeTrees.length; i++) {
      var childTree = derivedAttributeTrees[i];
      var derivedAttribute = new Object();
      derivedAttribute.name = childTree.value;
      derivedAttribute.sourceAttribute = mlabGetMDLChildValue(childTree, "sourceAttribute", null);
      derivedAttribute.defaultValue = mlabGetMDLChildValue(childTree, "defaultValue", null);
      derivedAttribute.mappedValues = new Object();
      var caseTrees = mlabGetMDLChildren(childTree, "Case");
      for (var j=0;j<caseTrees.length;j++) {
        var caseTree = caseTrees[j];
        var key = caseTree.value;
        var value = mlabGetMDLChildValue(caseTree, "value", mlabGetMDLChildValue(caseTree, "pathValue", ""));
        derivedAttribute.mappedValues[key] = value;
      }
      self._derivedAttributes[derivedAttribute.name] = derivedAttribute;
    } 
  }
  
  this._synchronizeHeader = function() {
    var headerRow = self._headerRow;
    var totalWidth = 0;
    if (self._tableBody.rows.length > 0) {
      var firstRow = self._tableBody.rows[0];
      for (var i=0;i<headerRow.cells.length;i++) {
        var w = firstRow.cells[i].clientWidth;
        //var headerElem = headerRow.cells[i];
        totalWidth += w;
        //headerElem.style.width = w;
        //headerElem.style.minWidth = w;
        //headerElem.style.maxWidth = w;
      }
    } else {
      for (var i=0;i<headerRow.length;i++) {
        var headerElem = headerRow.cells[i];
        delete headerElem.style.width;
        delete headerElem.style.minWidth;
        delete headerElem.style.maxWidth;
      }
    }
    if (totalWidth < self._width) {
      var dif = self._width - totalWidth;
      if (self._tableBody.rows.length > 0) {
        var firstRow = self._tableBody.rows[0];
        var add = dif / firstRow.cells.length;
        for (var i=0;i<headerRow.cells.length;i++) {
          var w = firstRow.cells[i].clientWidth;
          firstRow.cells[i].style.width = w + add;
          var headerElem = headerRow.cells[i];
          headerElem.style.width =  w + add;
          //headerElem.style.minWidth = firstWidth + dif;
          headerElem.style.maxWidth = w + add;
        }
      } 
    } 
    self._synchronizeHeaderPos();
  }
  
  this._synchronizeHeaderPos = function() {
    self._header.style.left = -self._tableBody.scrollLeft;
    delete self._header.style.width;
    self._header.style.width = self._tableBody.offsetWidth + self._tableBody.scrollLeft;
  }
  
  // setup columns, create table header and empty table body
  this._createTable = function() {
    self._columns = [];    
    self._table = document.createElement("table");
    self._header = self._table.createTHead();
    if (!self._showHeader) {
      self._header.style.visibility = "collapse";
      self._header.style.height = "0px";
    }
    self._headerRow = self._header.insertRow(0);
    self._headerRow.setAttribute("class", "MLABMLItemModelViewControl_HeaderRow");
    var columnTrees = mlabGetMDLChildren(self._mdlTree, "column");
    for (var i=0; i<columnTrees.length; i++) {
      var childTree = columnTrees[i];
      var column = new Object();
      column.name = childTree.value;
      column.displayAttribute = mlabGetMDLChildValue(childTree, "displayAttribute", column.name);
      if (column.displayAttribute.toLowerCase() === "none") {
        column.displayAttribute = null;
      }
      column.iconAttribute = mlabGetMDLChildValue(childTree, "iconAttribute");
      column.checkboxAttribute = mlabGetMDLChildValue(childTree, "checkboxAttribute");
      column.checkboxEditableAttribute = mlabGetMDLChildValue(childTree, "checkboxEditableAttribute");
      self._columnUsesAttribute(i, column.displayAttribute);
      self._columnUsesAttribute(i, column.iconAttribute);
      self._columnUsesAttribute(i, column.checkboxAttribute);
      self._columnUsesAttribute(i, column.checkboxEditableAttribute);
      column.alignment = mlabGetMDLChildValue(childTree, "align");
      column.sortAttributes = new Array();
      var sortAttributeString = mlabGetMDLChildValue(childTree, "sortAttributes", column.displayAttribute);
      if (sortAttributeString) {
        // the string is a list of attribute names, possibly prefixed with "!" to indicate reversed sort order
        var sortAttributes = sortAttributeString.split(",");
        for (var j=0;j<sortAttributes.length; j++) {
          var sortAttribute = sortAttributes[j];
          var sortAttributeEntry = new Object();
          if (sortAttribute.charAt(0) === "!") {
            sortAttribute = sortAttribute.substring(1);
            // this is just a multiplier for the sort function result:
            sortAttributeEntry.inverted = -1;
          } else {
            sortAttributeEntry.inverted = 1;
          }
          sortAttributeEntry.attribute = sortAttribute;
          column.sortAttributes.push(sortAttributeEntry);
        }
      }
      self._columns.push(column)
      var cell = document.createElement("th");
      var cellLabel = document.createElement("div");
      cellLabel.innerHTML = column.name;
      cellLabel.setAttribute("class", "MLABMLItemModelViewControl_HeaderLabel");
      cell.appendChild(cellLabel);
      cell.onclick = self._handleColumnHeaderClick;
      self._headerRow.appendChild(cell);
    }
    
    self._tableBody = document.createElement("tbody");
    self._tableBody.onscroll = self._synchronizeHeaderPos;
    self._table.appendChild(self._tableBody);
    self._domElement.appendChild(self._table);
  }
  
  // listener callback
  this.itemChanged = function(item, before) {
    var itemID = item.getID();
    var row = self._rowMap[itemID];
    var isExpanded = (itemID in self._expandedIDs);
    if ((row && isExpanded) || item.isRoot()) {
      // visible
      if (before) {
        self._removeSubRowsOf(row, true);
      } else {
        self._populateRow(row);
      }
    }
    if (row && !before && !self._model.isFlat()) {
      // update hasChildren state:
      if (!item.hasChildren()) {
        delete self._expandedIDs[itemID];
        self._markRowUnexpandable(row);
      } else {
        self._markRowExpanded(row, isExpanded);
      }
    }
    self._synchronizeHeader();
  }
  
  // listener callback
  this.itemsInserted = function(parentItem, at, amount, before) {
    if (!before) {
      var itemID = parentItem.getID();
      var parentRow = self._rowMap[itemID]
      if ((parentRow && self._expandedIDs[itemID]) || parentItem.isRoot()) {
        // visible
        self._addRows(parentRow, parentItem, at, amount);
      }
    }
    self._synchronizeHeader();
  }
  
  // listener callback
  this.itemsRemoved = function(parentItem, at, amount, before) {
    if (before) {
      for (var i=0;i<amount;i++) {
        var item = parentItem.getChild(at+i);
        var row = self._rowMap[item.getID()];
        if (row) {
          self._removeRow(row, true);
        }
      }
    } 
    self._synchronizeHeader();
  }
  
  this.dataChanged = function(items, attributes) {
    // which columns must be updated when the given attributes have changed:
    var columns = 0;
    for (var i=0;i<attributes.length;i++) {
      if (attributes[i] in self._columnUpdateMap) {
        columns = columns | self._columnUpdateMap[attributes[i]];
      }
    }
    // iterate over items:
    var columnCount = self._columns.length;
    for (var i=0;i<items.length;i++) {
      var item = items[i];
      var row = self._rowMap[item.getID()];
      if (row) {
        for (var col=0;col<columnCount;col++) {
          if (((1 << col) & columns) != 0) {
            // update cell:
            self._updateContent(row.cells[col], self._columns[col], item);
          }
        }
      }
    }
    self._synchronizeHeader();
  }
  
  // get attribute value from item
  this._getAttribute = function(item, attributeName) {
    var result = '';
    if (attributeName) {
      if (attributeName in self._derivedAttributes) {
        var derivedAttribute = self._derivedAttributes[attributeName];
        var key = self._getAttribute(item, derivedAttribute.sourceAttribute);
        if (key in derivedAttribute.mappedValues) {
          result = derivedAttribute.mappedValues[key];
        } else {
          result = derivedAttribute.defaultValue;
        }
      } else if (attributeName == "true") {
        result = true;
      } else if (attributeName == "false") {
        result = false;
      } else if (attributeName == "none") {
        result = null;
      } else {
        result = item.getAttribute(attributeName);
        if (result === null) {
          result = '';
        }
      }
    }
    return result;
  };
  
  // returns the id attribute value of the item
  this._getItemID = function(item) {
    return self._getAttribute(item, self._idAttribute);
  };
  
  // get ID string of an item as specified with the idXxx tags
  this._getID = function(item) {
    var id = self._getItemID(item);
    if (self._idAsFullPath) {
      // create id as a path
      while ((item = item.getParent()) && !item.isRoot()) {
        id = self._getItemID(item) + self._idPathSeparator + id;
      }
    }
    return id;
  };
  
  // sort function for comparing two items according to current sort column;
  // this should only be applied to child-items of the same parent
  this._sortFuncItems = function(item1, item2) {
    for (var i=0;i<self._sortAttributes.length;i++) {
      var sortAttribute = self._sortAttributes[i];
      var value1 = self._getAttribute(item1, sortAttribute.attribute);
      var value2 = self._getAttribute(item2, sortAttribute.attribute);
      if (value1 < value2) {
        return sortAttribute.inverted * self._sortInverted * -1;
      } else if (value1 > value2) {
        return sortAttribute.inverted * self._sortInverted;
      }
      // values seem to be identical, try next attribute (if specified)
    }
    return 0;
  }
  
  // sort function for comparing two table (HTML) rows according to current sort column;
  // this can be used to sort the whole visible table at once
  this._sortFuncRows = function(row1, row2) {
    if (row1.mevis_treeDepth < row2.mevis_treeDepth) {
      // traverse hierarchy from row2 until we are on the same level:
      while (row1.mevis_treeDepth < row2.mevis_treeDepth) {
        row2 = self._rowMap[row2.mevis_item.getParent()];
      }
      // if now the row are the same, row2 was a child of row1;
      // this means row2 must come behind row1
      if (row1 === row2) {
        return -1;
      }
    } else if (row1.mevis_treeDepth > row2.mevis_treeDepth) {
      // traverse hierarchy from row1 until we are on the same level:
      while (row1.mevis_treeDepth > row2.mevis_treeDepth) {
        row1 = self._rowMap[row1.mevis_item.getParent()];
      }
      // if now the row are the same, row1 was a child of row2;
      // this means row1 must come behind row2
      if (row1 === row2) {
        return 1;
      }
    }
    // now we have two rows of the same depth,
    // but we don't start comparing until we have the same parent:
    while (row1.mevis_item.getParent() !== row2.mevis_item.getParent()) {
      row1 = self._rowMap[row1.mevis_item.getParent()];
      row2 = self._rowMap[row2.mevis_item.getParent()];
    }
    // (note that we automatically stop at the root item)
    // now we have two rows with the same parent - compare their items according to the current sort criteria:
    return self._sortFuncItems(row1.mevis_item, row2.mevis_item);
  }
  
  // used in event handling
  this._getParentRowOfElement = function(target) {
    if (target.tagName.toLowerCase() === "tr") {
      return target;
    } else {
      return self._getParentRowOfElement(target.parentNode);
    }
  }
  
  this._getParentCellOfElement = function(target) {
    var tagName = target.tagName.toLowerCase();
    if (tagName === "td" || tagName === "th") {
      return target;
    } else {
      return self._getParentCellOfElement(target.parentNode);
    }
  }
  
  // mark table row as selected/deselected
  this._markRowSelected = function(tableRow, select) {
    if (select) {
      mlabAddCSSClass(tableRow, "MLABMLItemModelViewControl_SelectedRow")
    } else {
      mlabRemoveCSSClass(tableRow, "MLABMLItemModelViewControl_SelectedRow");
    }
  }
  
  // select/deselect table row, independently from the selection mode:
  this._setRowSelected = function(tableRow, select) {
    if (tableRow) {
      var itemID = tableRow.mevis_item.getID();
      if ((itemID in self._selectedIDs) !== select) {
        self._markRowSelected(tableRow, select);
        if (select) {
          self._selectedIDs[itemID] = true;
        } else {
          delete self._selectedIDs[itemID];
        }
      }
    }
  }
  
  // select the given row, deselecting the previous row first
  this._selectTableRow = function(tableRow) {
    if (self._lastSelectedTableRow !== tableRow) {
      self._setRowSelected(self._lastSelectedTableRow, false);
      self._lastSelectedTableRow = tableRow;
      self._setRowSelected(self._lastSelectedTableRow, true);
      if (self._currentField || self._selectionField) {
        var value = tableRow ? ('' + self._getID(tableRow.mevis_item)) : '';
        if (self._currentField) {
          self._currentField.setValue(value);
        }
        if (self._selectionField) {
          self._selectionField.setValue(value);
        }
      }
    }
  };
  
  // mark row as not expanded (i.e. remove the expander handle in the first column)
  this._markRowUnexpandable = function(tableRow) {
    var expander = tableRow.mevis_expander;
    expander.setAttribute("class", "MLABMLItemModelViewControl_EmptyHandle");
  }
  
  // mark row as expanded/collapsed (i.e. set the expander handle in the first column)
  this._markRowExpanded = function(tableRow, expanded) {
    var expander = tableRow.mevis_expander;
    expander.setAttribute("class", 
      expanded ? "MLABMLItemModelViewControl_ExpandedHandle" :
                 "MLABMLItemModelViewControl_CollapsedHandle");
  }
  
  // switch between expanded states of row when clicking on the expander handle
  this._toggleExpandedState = function(tableRow) {
    var item = tableRow.mevis_item;
    if (item.hasChildren()) {
      // get current state
      var itemID = item.getID();
      var isExpanded = self._expandedIDs[itemID];
      // invert:
      self._markRowExpanded(tableRow, !isExpanded)
      if (isExpanded) {
        delete self._expandedIDs[itemID];
        self._removeSubRowsOf(tableRow, false);
      } else {
        self._expandedIDs[itemID] = true;
        self._populateRow(tableRow);
      }
      self._synchronizeHeader();
    }
  }
  
  // change sorting of table
  this._setSorting = function(column, inverted) {
    if (column < self._columns.length &&
        (column !== self._sortColumn || (column >= 0 && inverted !== self._sortInverted)))
    {
      if (self._sortColumn >= 0) {
        // remove old sort marker
        var oldHeader = self._headerRow.cells[self._sortColumn];
        mlabRemoveCSSClass(oldHeader, "MLABMLItemModelViewControl_AscendingOrder");
        mlabRemoveCSSClass(oldHeader, "MLABMLItemModelViewControl_DescendingOrder");
      }
      self._sortColumn = column;
      self._sortInverted = inverted;
      if (column >= 0) {
        self._sortAttributes = self._columns[column].sortAttributes;
        // set new sort marker
        var newHeader = self._headerRow.cells[self._sortColumn];
        mlabAddCSSClass(newHeader,
          (self._sortInverted > 0) ? "MLABMLItemModelViewControl_AscendingOrder"
                                   : "MLABMLItemModelViewControl_DescendingOrder");
        // get rows into an array and sort it:
        var n = self._tableBody.rows.length;
        var sortedRows = new Array();
        for (var i=0;i<n;i++) {
          sortedRows.push(self._tableBody.rows[i]);
        }
        sortedRows.sort(self._sortFuncRows);
        // now rearrange the rows accordingly:
        for (var i=0;i<n;i++) {
          // only do this if the row isn't at the right place already:
          var row = sortedRows[i];
          if (self._tableBody.rows[i] !== row) {
            self._tableBody.removeChild(row);
            self._tableBody.insertBefore(row, self._tableBody.rows[i]);
          }
        }
        // ready!
      } else if (self._model) {
        self._sortAttributes = new Array();
        // we can't easily write a compare function for non-sorting, so we just
        // re-create the table:
        self._removeSubRowsOf(null, false);
        self._populateRow(null);
      }
    }
  }
  
  // handle clicking on a column header:
  this._handleColumnHeaderClick = function(ev) {
    var cell = self._getParentCellOfElement(ev.target);
    var column = cell.cellIndex;
    if (self._sortColumn >= 0) {
      // if a table starts unsorted, it stays that way
      if (column == self._sortColumn) {
        self._setSorting(column, -self._sortInverted);
      } else {
        self._setSorting(column, 1);
      }
    }
  }
  
  // display all child items of the given row, e.g. when expanding a row
  this._populateRow = function(parentRow) {
    var parentItem = parentRow ? parentRow.mevis_item : self._model.getRootItem();
    self._addRows(parentRow, parentItem, 0, parentItem.getChildCount());
  }
  
  // get row index where to insert child row for given parentRow and child index;
  // parentRow may be null, which means the root item
  this._getRowIndex = function(parentRow, index) {
    var rowIndex = parentRow ? parentRow.sectionRowIndex+1 : 0;
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0;
    // iterate over child rows until we find the index (or run out of child rows)
    while (rowIndex < self._tableBody.rows.length) {
      var row = self._tableBody.rows[rowIndex];
      if (row.mevis_treeDepth < depth) {
        break;
      } else if (row.mevis_treeDepth === depth) {
        if (index === 0) {
          return rowIndex;
        } else {
          index--;
        }
      }
      rowIndex++;
    }
    return rowIndex;
  }
  
  // add new rows to the table for the given parentRow element at childIndex index,
  // derived from the given modelItem;
  // parentRow may be null, which means the root item;
  // returns the next rowIndex
  this._addRows = function(parentRow, parentItem, at, amount) {
    if (self._sortColumn === -1) {
      var rowIndex = self._addRowsIndexed(parentRow, parentItem, at, amount);
    } else {
      var rowIndex = self._addRowsSorted(parentRow, parentItem, at, amount);
    }
    return rowIndex
  }

  // same as above, but for when sorting is not activate:
  this._addRowsIndexed = function(parentRow, parentItem, at, amount) {
    // TODO: implement sorting here !!!
    var rowIndex = self._getRowIndex(parentRow, at);
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0;
    for (var i=0;i<amount;i++) {
      rowIndex = self._addRowAt(parentItem.getChild(at+i), rowIndex, depth);
    }
    return rowIndex
  }

  // same as above, but for when sorting is activated:
  this._addRowsSorted = function(parentRow, parentItem, at, amount) {
    var rowIndex = parentRow ? parentRow.sectionRowIndex+1 : 0;
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0;
    // get sorted list of items to insert:
    var items = new Array();
    for (var i=0;i<amount;i++) {
      items.push(parentItem.getChild(at+i));
    }
    items.sort(self._sortFuncItems);
    for (var i=0;i<items.length;i++) {
      var item = items[i];
      // find insert index:
      while (rowIndex < self._tableBody.rows.length) {
        var row = self._tableBody.rows[rowIndex];
        if (row.mevis_treeDepth < depth) {
          break;
        } else if (row.mevis_treeDepth === depth && self._sortFuncItems(row.mevis_item, item) >= 0) {
          break;
        }
        rowIndex++;
      }
      // insert item:
      rowIndex = self._addRowAt(item, rowIndex, depth);
    }
    return rowIndex
  }
  
  // create an element that can contain the expander handle (or serve as indentation element)
  this._createExpanderElement = function() {
    var div = document.createElement("div");
    div.innerHtml = "&nbsp;";
    div.setAttribute("class", "MLABMLItemModelViewControl_EmptyHandle");
    return div;
  }
  
  this._handleExpanderClick = function(ev) {
    self._toggleExpandedState(self._getParentRowOfElement(ev.target));
    ev.stopPropagation();
  }
  
  this._handleRowClick = function(ev) {
    // TODO: implement different selection modes
    self._selectTableRow(self._getParentRowOfElement(ev.target));
  }
  
  this._handleCheckboxChange = function(ev) {
    var cell = self._getParentCellOfElement(ev.target);
    var column = self._columns[cell.cellIndex];
    var row = cell.parentNode;
    var item = row.mevis_item;
    item.setAttribute(column.checkboxAttribute, cell.mevis_checkbox.checked);
  }

  this._handleCheckboxClick = function(ev) {
    ev.stopPropagation();
  }
  
  // add a new row to the table at the given rowIndex, and with the given tree depth,
  // derived from the given modelItem;
  // parentRow may be null, which means the root item;
  // returns the next rowIndex
  this._addRowAt = function(modelItem, rowIndex, depth) {
    var row = self._tableBody.insertRow(rowIndex);
    row.setAttribute("class", "MLABMLItemModelViewControl_TableRow");
    row.mevis_treeDepth = depth;
    row.mevis_item = modelItem;
    var itemID = modelItem.getID();
    self._rowMap[itemID] = row;
    var isExpanded = (itemID in self._expandedIDs);
    var isSelected = (itemID in self._selectedIDs);
    if (isSelected) {
      // row was previously selected
      self._markRowSelected(row, true);
    }
    for (var i=0;i<self._columns.length;i++) {
      var column = self._columns[i];
      var cell = row.insertCell(i);
      if (i == 0 && !self._model.isFlat()) {
        // flat models don't show indentation in first column
        for (var j=0;j<depth;j++) {
          // add empty expander elements
          cell.appendChild(self._createExpanderElement());
        }
        var expander = self._createExpanderElement();
        expander.style.verticalAlign = "middle";
        expander.onclick = self._handleExpanderClick;
        row.mevis_expander = expander;
        if (modelItem.hasChildren()) {
          self._markRowExpanded(row, isExpanded);
        } else {
          self._markRowUnexpandable(row);
        }
        cell.appendChild(expander);
      }
      content = document.createElement("div");
      content.setAttribute("class", "MLABMLItemModelViewControl_CellContent");
      content.style.verticalAlign = "middle";
      if (column.alignment) {
        content.setAttribute("align", column.alignment.toLowerCase());
      }
      cell.mevis_content = content;
      cell.appendChild(content);
      
      // update the dynamic content
      self._updateContent(cell, column, modelItem);
      
      cell.onclick = self._handleRowClick;
    }
    rowIndex++;
    if (isExpanded) {
      // if item was expanded, expand again!
      rowIndex = self._addRows(row, modelItem, 0, modelItem.getChildCount());
    }
    return rowIndex;
  }
  
  this._updateContent = function(cell, column, modelItem) {
    // actual content:
    var content = cell.mevis_content;
    var previousElement = content;
    if (content.firstChild) {
      // purge the old content:
      content.removeChild(content.firstChild);
    }
    value = self._getAttribute(modelItem, column.displayAttribute);
    if (value) {
      content.appendChild(document.createTextNode(value));
    }
    // icon?
    if (column.iconAttribute) {
      var iconValue = self._getAttribute(modelItem, column.iconAttribute);
      if (iconValue) {
        var icon;
        if ("mevis_icon" in cell) {
          icon = cell.mevis_icon;
        } else {
          icon = document.createElement("img");
          // ako: add class to be able to style that
          //icon.style.verticalAlign = "middle";
          //icon.style.paddingRight = "3px";
          cell.mevis_icon = icon;
          cell.insertBefore(icon, previousElement);
        }
        previousElement = icon;
        if (typeof(iconValue) == "object") {
          if (iconValue.type == "PngImageData") {
            icon.src = "data:image/png;base64," + iconValue.data;
          } else if (iconValue.type == "JpgImageData") {
            icon.src = "data:image/jpeg;base64," + iconValue.data;
          } else if (iconValue.type == "FilePath") {
            icon.src = mlabTranslatePath(iconValue.data)
          }
        } else {
          icon.src = mlabTranslatePath(iconValue)
        }
      } else if ("mevis_icon" in cell) {
        // remove icon
        cell.removeChild(cell.mevis_icon);
        delete cell.mevis_icon;
      }
    }
    // checkbox?
    if (column.checkboxAttribute) {
      var checkboxValue = self._getAttribute(modelItem, column.checkboxAttribute);
      if (checkboxValue !== null && checkboxValue !== undefined) {
        var checkbox;
        if ("mevis_checkbox" in cell) {
          checkbox = cell.mevis_checkbox;
        } else {
          checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.onchange = self._handleCheckboxChange;
          checkbox.onclick = self._handleCheckboxClick;
          cell.mevis_checkbox = checkbox;
          cell.insertBefore(checkbox, previousElement);
        }
        previousElement = checkbox;
        checkbox.checked = checkboxValue;
        checkbox.disabled = !self._getAttribute(modelItem, column.checkboxEditableAttribute);
      } else if ("mevis_checkbox" in cell) {
        // remove checkbox
        cell.removeChild(cell.mevis_checkbox);
        delete cell.mevis_checkbox;
      }
    }
  }

  // do cleanup when an item is fully removed:
  this._removeItem = function(row, itemID) {
    // TODO: we will miss selected/expanded IDs if these have been folded away
    // when they are removed, but this will not be much of a problem - we can remove
    // these when we notice that these IDs aren't valid anymore
    delete self._selectedIDs[itemID];
    delete self._expandedIDs[itemID];
    if (row === self._lastSelectedTableRow) {
      // automatically deselect row
      self._selectTableRow(null);
    }
  }
  
  // remove the given row; if fully is false, the rows are just collapsed
  this._removeRow = function(row, fully) {
    var item = row.mevis_item;
    var itemID = item.getID();
    if (fully) {
      self._removeItem(row, itemID);
    }
    delete self._rowMap[itemID];
    self._removeSubRowsOf(row, fully);
    self._tableBody.deleteRow(row.sectionRowIndex)
  }
  
  // remove all sub-rows of the given row,;if fully is false, the rows are just collapsed
  this._removeSubRowsOf = function(parentRow, fully) {
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0;
    var nextRowIndex = parentRow ? parentRow.sectionRowIndex+1 : 0; 
    while (true) {
      var subRow = self._tableBody.rows[nextRowIndex];
      if (!(subRow) || (subRow.mevis_treeDepth < depth)) {
        // stop at next item that has the same or higher depth in the hierarchy
        // (or if there are no more items):
        break;
      }
      var itemID = subRow.mevis_item.getID()
      if (fully) {
        self._removeItem(subRow, itemID);
      }
      delete self._rowMap[itemID];
      self._tableBody.deleteRow(nextRowIndex)
    }
  }
  
}

