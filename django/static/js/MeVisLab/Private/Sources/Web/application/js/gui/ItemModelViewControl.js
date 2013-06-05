/** \class MLAB.GUI.MLItemModelViewControl
 * 
 */
MLAB.GUI.deriveClass("MLItemModelViewControl", MLAB.GUI.WidgetControl, {
  MLItemModelViewControl: function(mdlTree, module) {
    MLAB.GUI.MLItemModelViewControl.super.constructor.call(this, mdlTree, module)
  },

  setup: function(parentControl) {
    MLAB.GUI.MLItemModelViewControl.super.setup.call(this, parentControl)
    
    // Decide if all editable fields should show the editors by default
    this._alwaysShowAllEditors = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("alwaysShowAllEditors", "false"))

    this._idAttribute = this.getMDLAttribute("idAttribute", null)
    this._idAsFullPath = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("idAsFullPath", "false"))
    this._idPathSeparator = this.getMDLAttribute("idPathSeparator", "/")
    this._idSeperator = this.getMDLAttribute("idSeparator", ";")
    this._showHeader = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("header", "true"))
    
    // these fields may be null if not specified
    this._currentField = this.getMDLFieldAttribute("currentField")
    this._selectionField = this.getMDLFieldAttribute("selectionField")
    this._selectionMode = this.getMDLAttribute("selectionMode")
    if (this._selectionField) {
      this._selectionField.addListener(this)
    }
    this._selectionFieldLock = false
    this._pendingSelection = false
    this._addingRows = 0  // recursion counter
    
    // store a map of which columns to update when an attribute changes -
    // the object stores a map from attribute names to bitsets (stored as numbers)
    // (this restricts the number of columns to a probably small number)
    this._columnUpdateMap = new Object()
    
    // store a reference to the cell that is currently edited
    this._editingCell = null
    
    // store derived attributes information
    this._derivedAttributes = new Object()
    this._parseDerivedAttributes()
    
    this._createTable()  // sets this._columns, this._table and this._tableBody

    // sorting   
    this._sortAttributes = new Array() // this will be set when the sort column changes
    this._sortColumn = -1  // -1 means unsorted
    this._sortInverted = 1 // this is just a multiplicator, 1 means not inverted, -1 is inverted
    
    var sortByColumn = this.getMDLAttribute("sortByColumn", "-1")  // -1 means unsorted
    var sortAscending = this.getMDLAttribute("sortAscending", "true")
    this._setSorting(new Number(sortByColumn), MLAB.Core.convertMDLValueToBool(sortAscending) ? 1 : -1)
    
    // item model will be null initially (implementation will be provided by ItemModelHandler)
    this._model = null
    
    // update field value
    this._baseFieldChanged()
    if (this._selectionField) {
      this._selectionFieldChanged()
    }
  },

  setupTypicalTags: function() {
    var w = this.getMDLAttribute("w", null)
    if (w) { this._widget.getStyle().width = w + "px" }
    var h = this.getMDLAttribute("h", null)
    if (h) { this._widget.getStyle().height = h + "px" }
  },
  
  // check if an attribute even exists:
  _checkAttributeName: function(attrName) {
    if (attrName && attrName !== true && !this._model.hasAttribute(attrName) &&
        !(attrName in this._derivedAttributes))
    {
      this.getModule().logError("MLAB.GUI.MLItemModelViewControl: " +
                                    "no such attribute in model: '" + attrName + "'")
    }
  },
  
  // warn about unknown attribute when the model changes:
  _checkTable: function() {
    for (var i=0; i<this._columns.length; i++) {
      var column = this._columns[i]
      this._checkAttributeName(column.displayAttribute)
      this._checkAttributeName(column.checkboxAttribute)
      this._checkAttributeName(column.iconAttribute)
      this._checkAttributeName(column.tooltipAttribute);
    }
    for (var derivedAttribute in this._derivedAttributes) {
      this._checkAttributeName(derivedAttribute.sourceAttribute)
    }
  },

  fieldChanged: function(field) {
    if (field == this._field) {
      this._baseFieldChanged()
    } else if (field == this._selectionField) {
      this._selectionFieldChanged()
    }
  },

  _baseFieldChanged: function() {
    if (this._model) {
      this._model.removeListener(this)
      // remove everything unter the root item:
      this._removeSubRowsOf(null, true)
    }

    if (this._field && this._field.isBaseField()) {
      this._model = this._field.getValue()
    } else {
      // this should rarely happen - but we handle it, too
      this._model = null
    }
    
    // remember in a map which items have been expanded
    this._expandedIDs = new Object()

    // remember in a map which items have been expanded
    this._selectedIDs = new Object()

    // mapping of item ids to row elements
    this._rowMap = new Object()
    
    if (this._model) {
      this._checkTable()
      this._model.addListener(this)
      // add all direct children of the root item:
      this._populateRow(null)
    }
  },

  _selectionFieldChanged: function() {
    if (!this._selectionFieldLock) {
      this._selectionFieldLock = true
      // try to support multiple selections, even if the remaining code does not - yet!
      var ids = (''+this._selectionField.getValue()).split(this._idSeperator)
      var selectionIds = new Object()
      var selectionCount = 0
      for (var i=0;i<ids.length;i++) {
        // ignore empty IDs:
        if (ids[i].length > 0) {
          selectionCount += 1
          selectionIds[ids[i]] = 1
        }
      }
      // modify selection
      var rows = this._tableBody.rows
      var selectedRowsFound = 0
      for (var i=0;i<rows.length;i++) {
        var row = rows[i]
        var id = this._getID(row.mevis_item)
        var selected = id in selectionIds
        this._setRowSelected(row, selected)
        if (selected) {
          selectedRowsFound += 1
          this._lastSelectedTableRow = row
        }
      }
      // if not all selected items could be found, the corresponding items
      // might not be received yet - we need to check again after items have been received:
      this._pendingSelection = (selectedRowsFound < selectionCount)
      if (selectedRowsFound == 0) {
        this._lastSelectedTableRow = null
      } else if (!this._pendingSelection) {
        // TODO: scroll to last selected element
      }
      this._selectionFieldLock = false
    }
  },
  
  _columnUsesAttribute: function(column, attributeName) {
    if (attributeName in this._derivedAttributes) {
      var derivedAttribute = this._derivedAttributes[attributeName]
      this._columnUsesAttribute(column, derivedAttribute.sourceAttribute)
    } else if (attributeName) {
      var columns = (attributeName in this._columnUpdateMap) ? this._columnUpdateMap[attributeName] : 0
      columns = columns | (1 << column)
      this._columnUpdateMap[attributeName] = columns
    }
  },
  
  _parseDerivedAttributes: function() {
    var derivedAttributeTrees = this._mdlTree.getAll("DerivedAttribute")
    for (var i=0; i<derivedAttributeTrees.length; i++) {
      var childTree = derivedAttributeTrees[i]
      var derivedAttribute = new Object()
      derivedAttribute.name = childTree.getValue()
      derivedAttribute.sourceAttribute = childTree.childValue("sourceAttribute", null)
      derivedAttribute.defaultValue = childTree.childValue("defaultValue", null)
      derivedAttribute.mappedValues = new Object()
      var caseTrees = childTree.getAll("Case")
      for (var j=0;j<caseTrees.length;j++) {
        var caseTree = caseTrees[j]
        var key = caseTree.getValue()
        var value = caseTree.childValue("value", caseTree.childValue("pathValue"))
        derivedAttribute.mappedValues[key] = value
      }
      this._derivedAttributes[derivedAttribute.name] = derivedAttribute
    } 
  },
  
  _synchronizeHeader: function() {
    var headerRow = this._headerRow
    if (this._tableBody.rows.length > 0) {
      var firstRow = this._tableBody.rows[0]
      for (var i=0;i<headerRow.cells.length;i++) {
        var w = firstRow.cells[i].clientWidth
        var headerElem = headerRow.cells[i]
        headerElem.style.width = w
        headerElem.style.minWidth = w
        headerElem.style.maxWidth = w
      }
    } else {
      for (var i=0;i<headerRow.length;i++) {
        var headerElem = headerRow.cells[i]
        delete headerElem.style.width
        delete headerElem.style.minWidth
        delete headerElem.style.maxWidth
      }
    }
    this._synchronizeHeaderPos()
  },
  
  _synchronizeHeaderPos: function() {
    this._header.style.left = -this._tableBody.scrollLeft
    delete this._header.style.width
    this._header.style.width = this._tableBody.offsetWidth + this._tableBody.scrollLeft
  },
  
  _getCommonColumnAttribute: function(childTree, name) {
    attribute = childTree.childValue(name, null)
    if (attribute === null) {
      attribute = this._mdlTree.childValue(name, null)
    }
    return attribute
  },
  
  // setup columns, create table header and empty table body
  _createTable: function() {
    this._columns = []
    this._table = document.createElement("table")
    this._header = this._table.createTHead()
    if (!this._showHeader) {
      this._header.style.visibility = "collapse"
      this._header.style.height = "0px"
    }
    this._headerRow = this._header.insertRow(0)
    this._headerRow.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_HeaderRow")
    var columnTrees = this._mdlTree.getAll("Column")
    for (var i=0; i<columnTrees.length; i++) {
      var childTree = columnTrees[i]
      var column = new Object()
      column.name = childTree.getValue()
      column.displayAttribute = childTree.childValue("displayAttribute", column.name)
      if (column.displayAttribute.toLowerCase() === "none") {
        column.displayAttribute = null
      }
      column.editAttribute = childTree.childValue("editAttribute", column.displayAttribute)
      column.iconAttribute = childTree.childValue("iconAttribute", null)
      column.tooltipAttribute = this._getCommonColumnAttribute(childTree, "tooltipAttribute")
      column.checkboxAttribute = childTree.childValue("checkboxAttribute", null)
      column.checkboxEditableAttribute = this._getCommonColumnAttribute(childTree, "checkboxEditableAttribute")
      this._columnUsesAttribute(i, column.displayAttribute)
      this._columnUsesAttribute(i, column.iconAttribute)
      this._columnUsesAttribute(i, column.tooltipAttribute);
      this._columnUsesAttribute(i, column.checkboxAttribute)
      this._columnUsesAttribute(i, column.checkboxEditableAttribute)
      column.editableAttribute = this._getCommonColumnAttribute(childTree, "editableAttribute")
      column.comboboxAttribute = childTree.childValue("comboboxAttribute", null)
      column.comboboxTooltipsAttribute = childTree.childValue("comboboxTooltipsAttribute", null)
      column.comboboxItemDelimiter = childTree.childValue("comboboxItemDelimiter", "|")
      column.alignment = childTree.childValue("align", null)
      column.sortAttributes = new Array()
      var sortAttributeString = childTree.childValue("sortAttributes", column.displayAttribute)
      if (sortAttributeString) {
        // the string is a list of attribute names, possibly prefixed with "!" to indicate reversed sort order
        var sortAttributes = sortAttributeString.split(",")
        for (var j=0;j<sortAttributes.length; j++) {
          var sortAttribute = sortAttributes[j]
          var sortAttributeEntry = new Object()
          if (sortAttribute.charAt(0) === "!") {
            sortAttribute = sortAttribute.substring(1)
            // this is just a multiplier for the sort function result:
            sortAttributeEntry.inverted = -1
          } else {
            sortAttributeEntry.inverted = 1
          }
          sortAttributeEntry.attribute = sortAttribute
          column.sortAttributes.push(sortAttributeEntry)
        }
      }
      this._columns.push(column)
      var cell = document.createElement("th")
      var cellLabel = document.createElement("div")
      cellLabel.innerHTML = column.name
      cellLabel.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_HeaderLabel")
      cell.appendChild(cellLabel)
      cell.onclick = this.callback("_handleColumnHeaderClick")
      this._headerRow.appendChild(cell)
    }
    
    this._tableBody = document.createElement("tbody")
    this._tableBody.onscroll = this.callback("_synchronizeHeaderPos")
    this._table.appendChild(this._tableBody)
    this._widget.appendChild(this._table)
  },
  
  // listener callback
  itemChanged: function(item, before) {
    var itemID = item.getID()
    var row = this._rowMap[itemID]
    var isExpanded = (itemID in this._expandedIDs)
    if ((row && isExpanded) || item.isRoot()) {
      // visible
      if (before) {
        this._removeSubRowsOf(row, true)
      } else {
        this._populateRow(row)
      }
    }
    if (row && !before && !this._model.isFlat()) {
      // update hasChildren state:
      if (!item.hasChildren()) {
        delete this._expandedIDs[itemID]
        this._markRowUnexpandable(row)
      } else {
        this._markRowExpanded(row, isExpanded)
      }
    }
    this._synchronizeHeader()
  },
  
  // listener callback
  itemsInserted: function(parentItem, at, amount, before) {
    if (!before) {
      var itemID = parentItem.getID()
      var parentRow = this._rowMap[itemID]
      if ((parentRow && this._expandedIDs[itemID]) || parentItem.isRoot()) {
        // visible
        this._addRows(parentRow, parentItem, at, amount)
      }
    }
    this._synchronizeHeader()
  },
  
  // listener callback
  itemsRemoved: function(parentItem, at, amount, before) {
    if (before) {
      for (var i=0;i<amount;i++) {
        var item = parentItem.getChild(at+i)
        var row = this._rowMap[item.getID()]
        if (row) {
          this._removeRow(row, true)
        }
      }
    } 
    this._synchronizeHeader()
  },
  
  dataChanged: function(items, attributes) {
    // which columns must be updated when the given attributes have changed:
    var columns = 0
    for (var i=0;i<attributes.length;i++) {
      if (attributes[i] in this._columnUpdateMap) {
        columns = columns | this._columnUpdateMap[attributes[i]]
      }
    }
    // iterate over items:
    var columnCount = this._columns.length
    for (var i=0;i<items.length;i++) {
      var item = items[i]
      var row = this._rowMap[item.getID()]
      if (row) {
        for (var col=0;col<columnCount;col++) {
          if (((1 << col) & columns) !== 0) {
            // update cell:
            this._updateContent(row.cells[col], this._columns[col], item)
          }
        }
      }
    }
    this._synchronizeHeader()
  },
  
  // get attribute value from item
  _getAttribute: function(item, attributeName) {
    var result = ''
    if (attributeName) {
      if (attributeName in this._derivedAttributes) {
        var derivedAttribute = this._derivedAttributes[attributeName]
        var key = this._getAttribute(item, derivedAttribute.sourceAttribute)
        if (key in derivedAttribute.mappedValues) {
          result = derivedAttribute.mappedValues[key]
        } else {
          result = derivedAttribute.defaultValue
        }
      } else if (attributeName === "true") {
        result = true
      } else if (attributeName === "false") {
        result = false
      } else if (attributeName === "none") {
        result = null
      } else {
        result = item.getAttribute(attributeName)
        if (result === null) {
          result = ''
        }
      }
    }
    return result
  },
  
  // returns the id attribute value of the item
  _getItemID: function(item) {
    return this._getAttribute(item, this._idAttribute)
  },
  
  // get ID string of an item as specified with the idXxx tags
  _getID: function(item) {
    var id = this._getItemID(item)
    if (this._idAsFullPath) {
      // create id as a path
      while ((item = item.getParent()) && !item.isRoot()) {
        id = this._getItemID(item) + this._idPathSeparator + id
      }
    }
    return id
  },
  
  // sort function for comparing two items according to current sort column
  // this should only be applied to child-items of the same parent
  _sortFuncItems: function(item1, item2) {
    for (var i=0;i<this._sortAttributes.length;i++) {
      var sortAttribute = this._sortAttributes[i]
      var value1 = this._getAttribute(item1, sortAttribute.attribute)
      var value2 = this._getAttribute(item2, sortAttribute.attribute)
      if (value1 < value2) {
        return sortAttribute.inverted * this._sortInverted * -1
      } else if (value1 > value2) {
        return sortAttribute.inverted * this._sortInverted
      }
      // values seem to be identical, try next attribute (if specified)
    }
    return 0
  },
  
  // sort function for comparing two table (HTML) rows according to current sort column
  // this can be used to sort the whole visible table at once
  _sortFuncRows: function(row1, row2) {
    if (row1.mevis_treeDepth < row2.mevis_treeDepth) {
      // traverse hierarchy from row2 until we are on the same level:
      while (row1.mevis_treeDepth < row2.mevis_treeDepth) {
        row2 = this._rowMap[row2.mevis_item.getParent().getID()]
      }
      // if now the row are the same, row2 was a child of row1
      // this means row2 must come behind row1
      if (row1 === row2) {
        return -1
      }
    } else if (row1.mevis_treeDepth > row2.mevis_treeDepth) {
      // traverse hierarchy from row1 until we are on the same level:
      while (row1.mevis_treeDepth > row2.mevis_treeDepth) {
        row1 = this._rowMap[row1.mevis_item.getParent().getID()]
      }
      // if now the row are the same, row1 was a child of row2
      // this means row1 must come behind row2
      if (row1 === row2) {
        return 1
      }
    }
    // now we have two rows of the same depth,
    // but we don't start comparing until we have the same parent:
    while (row1.mevis_item.getParent() !== row2.mevis_item.getParent()) {
      row1 = this._rowMap[row1.mevis_item.getParent().getID()]
      row2 = this._rowMap[row2.mevis_item.getParent().getID()]
    }
    // (note that we automatically stop at the root item)
    // now we have two rows with the same parent - compare their items according to the current sort criteria:
    return this._sortFuncItems(row1.mevis_item, row2.mevis_item)
  },
  
  // used in event handling
  _getParentRowOfElement: function(target) {
    if (target.tagName.toLowerCase() === "tr") {
      return target
    } else {
      return this._getParentRowOfElement(target.parentNode)
    }
  },
  
  _getParentCellOfElement: function(target) {  
    if (target === null) {
      return null;
    }
    var tagName = target.tagName.toLowerCase()
    if (tagName === "td" || tagName === "th") {
      return target
    } else {
      return this._getParentCellOfElement(target.parentNode)
    }
  },
  
  // mark table row as selected/deselected
  _markRowSelected: function(tableRow, select) {
    if (select) {
      MLAB.GUI.addStyleSheetClass(tableRow, "MLAB-GUI-MLItemModelViewControl_SelectedRow")
    } else {
      MLAB.GUI.removeStyleSheetClass(tableRow, "MLAB-GUI-MLItemModelViewControl_SelectedRow")
    }
  },
  
  // select/deselect table row, independently from the selection mode:
  _setRowSelected: function(tableRow, select) {
    if (tableRow) {
      var itemID = tableRow.mevis_item.getID()
      if ((itemID in this._selectedIDs) !== select) {
        this._markRowSelected(tableRow, select)
        if (select) {
          this._selectedIDs[itemID] = true
        } else {
          delete this._selectedIDs[itemID]
        }
      }
    }
  },
  
  // select the given row, deselecting the previous row first
  _selectTableRow: function(tableRow) {
    if (this._lastSelectedTableRow !== tableRow) {
      this._setRowSelected(this._lastSelectedTableRow, false)
      this._lastSelectedTableRow = tableRow
      this._setRowSelected(this._lastSelectedTableRow, true)
      if (this._currentField || this._selectionField) {
        var value = tableRow ? ('' + this._getID(tableRow.mevis_item)) : ''
        if (this._currentField) {
          this._currentField.setValue(value)
        }
        if (this._selectionField && !this._selectionFieldLock) {
          this._selectionFieldLock = true
          this._selectionField.setValue(value)
          this._pendingSelection = false // reset
          this._selectionFieldLock = false
        }
      }
    }
  },
  
  // mark row as not expanded (i.e. remove the expander handle in the first column)
  _markRowUnexpandable: function(tableRow) {
    var expander = tableRow.mevis_expander
    expander.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_EmptyHandle")
  },
  
  // mark row as expanded/collapsed (i.e. set the expander handle in the first column)
  _markRowExpanded: function(tableRow, expanded) {
    var expander = tableRow.mevis_expander
    expander.setAttribute("class", 
      expanded ? "MLAB-GUI-MLItemModelViewControl_ExpandedHandle" :
                 "MLAB-GUI-MLItemModelViewControl_CollapsedHandle")
  },
  
  // switch between expanded states of row when clicking on the expander handle
  _toggleExpandedState: function(tableRow) {
    var item = tableRow.mevis_item
    if (item.hasChildren()) {
      // get current state
      var itemID = item.getID()
      var isExpanded = this._expandedIDs[itemID]
      // invert:
      this._markRowExpanded(tableRow, !isExpanded)
      if (isExpanded) {
        delete this._expandedIDs[itemID]
        this._removeSubRowsOf(tableRow, false)
      } else {
        this._expandedIDs[itemID] = true
        this._populateRow(tableRow)
      }
      this._synchronizeHeader()
    }
  },
  
  // change sorting of table
  _setSorting: function(column, inverted) {
    if (column < this._columns.length &&
        (column !== this._sortColumn || (column >= 0 && inverted !== this._sortInverted)))
    {
      if (this._sortColumn >= 0) {
        // remove old sort marker
        var oldHeader = this._headerRow.cells[this._sortColumn]
        MLAB.GUI.removeStyleSheetClass(oldHeader, "MLAB-GUI-MLItemModelViewControl_AscendingOrder")
        MLAB.GUI.removeStyleSheetClass(oldHeader, "MLAB-GUI-MLItemModelViewControl_DescendingOrder")
      }
      this._sortColumn = column
      this._sortInverted = inverted
      if (column >= 0) {
        this._sortAttributes = this._columns[column].sortAttributes
        // set new sort marker
        var newHeader = this._headerRow.cells[this._sortColumn]
        MLAB.GUI.addStyleSheetClass(newHeader,
          (this._sortInverted > 0) ? "MLAB-GUI-MLItemModelViewControl_AscendingOrder"
                                    : "MLAB-GUI-MLItemModelViewControl_DescendingOrder")
        // get rows into an array and sort it:
        var n = this._tableBody.rows.length
        var sortedRows = new Array()
        for (var i=0;i<n;i++) {
          sortedRows.push(this._tableBody.rows[i])
        }
        sortedRows.sort(this.callback("_sortFuncRows"))
        // now rearrange the rows accordingly:
        for (var i=0;i<n;i++) {
          // only do this if the row isn't at the right place already:
          var row = sortedRows[i]
          if (this._tableBody.rows[i] !== row) {
            this._tableBody.removeChild(row)
            this._tableBody.insertBefore(row, this._tableBody.rows[i])
          }
        }
        // ready!
      } else if (this._model) {
        this._sortAttributes = new Array()
        // we can't easily write a compare function for non-sorting, so we just
        // re-create the table:
        this._removeSubRowsOf(null, false)
        this._populateRow(null)
      }
    }
  },
  
  // handle clicking on a column header:
  _handleColumnHeaderClick: function(ev) {
    var cell = this._getParentCellOfElement(ev.target)
    var column = cell.cellIndex
    if (this._sortColumn >= 0) {
      // if a table starts unsorted, it stays that way
      if (column === this._sortColumn) {
        this._setSorting(column, -this._sortInverted)
      } else {
        this._setSorting(column, 1)
      }
    }
  },
  
  // display all child items of the given row, e.g. when expanding a row
  _populateRow: function(parentRow) {
    var parentItem = parentRow ? parentRow.mevis_item : this._model.getRootItem()
    this._addRows(parentRow, parentItem, 0, parentItem.getChildCount())
  },
  
  // get row index where to insert child row for given parentRow and child index
  // parentRow may be null, which means the root item
  _getRowIndex: function(parentRow, index) {
    var rowIndex = parentRow ? parentRow.sectionRowIndex+1 : 0
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0
    // iterate over child rows until we find the index (or run out of child rows)
    while (rowIndex < this._tableBody.rows.length) {
      var row = this._tableBody.rows[rowIndex]
      if (row.mevis_treeDepth < depth) {
        break
      } else if (row.mevis_treeDepth === depth) {
        if (index === 0) {
          return rowIndex
        } else {
          index--
        }
      }
      rowIndex++
    }
    return rowIndex
  },
  
  // add new rows to the table for the given parentRow element at childIndex index,
  // derived from the given modelItem
  // parentRow may be null, which means the root item
  // returns the next rowIndex
  _addRows: function(parentRow, parentItem, at, amount) {
    this._addingRows += 1
    if (this._sortColumn === -1) {
      var rowIndex = this._addRowsIndexed(parentRow, parentItem, at, amount)
    } else {
      var rowIndex = this._addRowsSorted(parentRow, parentItem, at, amount)
    }
    this._addingRows -= 1
    // update selection if necessary and adding items has been finished:
    if (this._pendingSelection && (this._addingRows == 0)) {
      this._selectionFieldChanged()
    }
    return rowIndex
  },

  // same as above, but for when sorting is not activate:
  _addRowsIndexed: function(parentRow, parentItem, at, amount) {
    // TODO: implement sorting here !!!
    var rowIndex = this._getRowIndex(parentRow, at)
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0
    for (var i=0;i<amount;i++) {
      rowIndex = this._addRowAt(parentItem.getChild(at+i), rowIndex, depth)
    }
    return rowIndex
  },

  // same as above, but for when sorting is activated:
  _addRowsSorted: function(parentRow, parentItem, at, amount) {
    var rowIndex = parentRow ? parentRow.sectionRowIndex+1 : 0
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0
    // get sorted list of items to insert:
    var items = new Array()
    for (var i=0;i<amount;i++) {
      items.push(parentItem.getChild(at+i))
    }
    items.sort(this.callback("_sortFuncItems"))
    for (var i=0;i<items.length;i++) {
      var item = items[i]
      // find insert index:
      while (rowIndex < this._tableBody.rows.length) {
        var row = this._tableBody.rows[rowIndex]
        if (row.mevis_treeDepth < depth) {
          break
        } else if (row.mevis_treeDepth === depth && this._sortFuncItems(row.mevis_item, item) >= 0) {
          break
        }
        rowIndex++
      }
      // insert item:
      rowIndex = this._addRowAt(item, rowIndex, depth)
    }
    return rowIndex
  },
  
  // create an element that can contain the expander handle (or serve as indentation element)
  _createExpanderElement: function() {
    var div = document.createElement("div")
    div.innerHtml = "&nbsp;"
    div.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_EmptyHandle")
    return div
  },
  
  _handleExpanderClick: function(ev) {
    this._toggleExpandedState(this._getParentRowOfElement(ev.target))
    ev.stopPropagation()
  },
  
  _handleRowClick: function(ev) {
    // TODO: implement different selection modes
    var tryEdit = false
    var row = this._getParentRowOfElement(ev.target)
    if (this._selectionMode !== "NoSelection") {
      if (this._lastSelectedTableRow === row) {
        // check if the cell should be edited
        tryEdit = true
      } else {
        this._selectTableRow(row)
      }
    } else {
      tryEdit = true
    }
    
    // initiate editing:
    var cell = this._getParentCellOfElement(ev.target)
    if (cell !== this._editingCell) {
      this._removeEditor()
    }
    if (tryEdit) {
      var cell = this._getParentCellOfElement(ev.target)
      var column = this._columns[cell.cellIndex]
      var item = row.mevis_item
      if (this._getAttribute(item, column.editableAttribute)) {
        this._activateEditor(cell, column, item)
      }
    }
  },
  
  _handleCheckboxChange: function(ev) {
    var cell = this._getParentCellOfElement(ev.target)
    var column = this._columns[cell.cellIndex]
    var row = cell.parentNode
    var item = row.mevis_item
    item.setAttribute(column.checkboxAttribute, cell.mevis_checkbox.checked)
  },

  _handleCheckboxClick: function(ev) {
    ev.stopPropagation()
  },
  
  // add a new row to the table at the given rowIndex, and with the given tree depth,
  // derived from the given modelItem
  // parentRow may be null, which means the root item
  // returns the next rowIndex
  _addRowAt: function(modelItem, rowIndex, depth) {
    var row = this._tableBody.insertRow(rowIndex)
    row.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_TableRow")
    row.mevis_treeDepth = depth
    row.mevis_item = modelItem
    var itemID = modelItem.getID()
    this._rowMap[itemID] = row
    var isExpanded = (itemID in this._expandedIDs)
    var isSelected = (itemID in this._selectedIDs)
    if (isSelected) {
      // row was previously selected
      this._markRowSelected(row, true)
    }
    for (var i=0;i<this._columns.length;i++) {
      var column = this._columns[i]
      var cell = row.insertCell(i)
      if (i === 0 && !this._model.isFlat()) {
        // flat models don't show indentation in first column
        for (var j=0;j<depth;j++) {
          // add empty expander elements
          cell.appendChild(this._createExpanderElement())
        }
        var expander = this._createExpanderElement()
        expander.onclick = this.callback("_handleExpanderClick")
        row.mevis_expander = expander
        if (modelItem.hasChildren()) {
          this._markRowExpanded(row, isExpanded)
        } else {
          this._markRowUnexpandable(row)
        }
        cell.appendChild(expander)
      }
      content = document.createElement("div")
      content.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_CellContent")
      if (column.alignment) {
        content.setAttribute("align", column.alignment.toLowerCase())
      }
      cell.mevis_content = content
      cell.appendChild(content)
      
      // update the dynamic content
      this._updateContent(cell, column, modelItem)
      
      cell.onclick = this.callback("_handleRowClick")
    }
    rowIndex++
    if (isExpanded) {
      // if item was expanded, expand again!
      rowIndex = this._addRows(row, modelItem, 0, modelItem.getChildCount())
    }
    return rowIndex
  },
  
  _updateContent: function(cell, column, modelItem) {
    // actual content:
    var content = cell.mevis_content
    var previousElement = content
    if (content.firstChild) {
      // purge the old content:
      content.removeChild(content.firstChild)
    }

    // icon?
    if (column.iconAttribute) {
      var iconValue = this._getAttribute(modelItem, column.iconAttribute)
      if (iconValue) {
        var icon
        if ("mevis_icon" in cell) {
          icon = cell.mevis_icon
        } else {
          icon = document.createElement("img")
          cell.mevis_icon = icon
          cell.insertBefore(icon, previousElement)
        }
        previousElement = icon
        if (typeof(iconValue) === "object") {
          if (iconValue.type === "PngImageData") {
            icon.src = "data:image/png;base64," + iconValue.data
          } else if (iconValue.type === "JpgImageData") {
            icon.src = "data:image/jpeg;base64," + iconValue.data
          } else if (iconValue.type === "FilePath") {
            icon.src = MLAB.Core.translatePath(iconValue.data)
          }
        } else {
          icon.src = MLAB.Core.translatePath(iconValue)
        }
      } else if ("mevis_icon" in cell) {
        // remove icon
        cell.removeChild(cell.mevis_icon)
        delete cell.mevis_icon
      }
    }

    // tooltip?    
    if (column.tooltipAttribute) {
      var tooltipValue = this._getAttribute(modelItem, column.tooltipAttribute);
      if (tooltipValue !== null && tooltipValue !== undefined && tooltipValue !== "") {      
        cell.mevis_title = tooltipValue;
        content.parentNode.setAttribute("title", cell.mevis_title);
      } else if ("mevis_title" in cell) {
        delete cell.mevis_title;
        content.parentNode.removeAttribute("title");
      }
    }
    
    // checkbox?
    if (column.checkboxAttribute) {
      var checkboxValue = this._getAttribute(modelItem, column.checkboxAttribute)
      if (checkboxValue !== null && checkboxValue !== undefined) {
        var checkbox
        if ("mevis_checkbox" in cell) {
          checkbox = cell.mevis_checkbox
        } else {
          checkbox = document.createElement("input")
          checkbox.type = "checkbox"
          checkbox.onchange = this.callback("_handleCheckboxChange")
          checkbox.onclick = this.callback("_handleCheckboxClick")
          cell.mevis_checkbox = checkbox
          cell.insertBefore(checkbox, previousElement)
        }
        previousElement = checkbox
        checkbox.checked = checkboxValue
        checkbox.disabled = !this._getAttribute(modelItem, column.checkboxEditableAttribute)
      } else if ("mevis_checkbox" in cell) {
        // remove checkbox
        cell.removeChild(cell.mevis_checkbox)
        delete cell.mevis_checkbox
      }
    }

    // in _alwaysShowAllEditors, show editors for editable items
    if (this._alwaysShowAllEditors &&
        this._getAttribute(modelItem, column.editableAttribute))
    {      
      this._createEditor(cell, column, modelItem);
    } else {
      content.appendChild(document.createTextNode(this._getAttribute(modelItem, column.displayAttribute)));
    }
  },
  
 
  // activate editor widget for the given cell, creating it if necessary
  _activateEditor: function(cell, column, modelItem) {
    if (cell === this._editingCell) {
      // already editing
      return
    }
    if (!this._alwaysShowAllEditors) {
      // remove previous editor
      this._removeEditor()
      this._createEditor(cell, column, modelItem)
    }
    editorNode = cell.mevis_content.firstChild
    if (editorNode) {
      editorNode.focus()
      this._editingCell = cell
    }
  },
    

  // create an editor widget for the given cell
  _createEditor: function(cell, column, modelItem) {
    var content = cell.mevis_content
    if (content.firstChild) {
      // purge the old content:
      content.removeChild(content.firstChild)
    }
    // don't forget that we use the editAttribute instead of the displayAttribute
    var value = this._getAttribute(modelItem, column.editAttribute)
    var items = this._getAttribute(modelItem, column.comboboxAttribute)
    var itemTooltips = this._getAttribute(modelItem, column.comboboxTooltipsAttribute)
    
    var editorNode = null
    if (items) {
      var enumItems = items.split(column.comboboxItemDelimiter)
      var enumItemTooltips = itemTooltips.split(column.comboboxItemDelimiter)
      if ((enumItemTooltips.length > 0) && (enumItemTooltips.length !== enumItems.length)) {
        this.getModule().logError("MLAB.GUI.MLItemModelViewControl: " +
                                     "comboboxTooltipsAttribute " + column.comboboxTooltipsAttribute + " has different (but non-zero) number of items than comboboxAttribute " + column.comboboxAttribute + " (" + enumItemTooltips + " vs. " + enumItems + ")!")
      }
      
      var editorNode = document.createElement("select")
      for (var i=0; i<enumItems.length; i++) {
        var option = document.createElement("option")
        option.appendChild(document.createTextNode(enumItems[i]))
        option.value = enumItems[i]
        if (i < enumItemTooltips.length) {
          option.title = enumItemTooltips[i]
        }
        if (value == enumItems[i]) { option.selected = true }
        editorNode.appendChild(option)
        editorNode.onkeydown = this.callback("_onNavigationKeyDown")
      }
      editorNode.onchange = this.callback("_onComboBoxChange")
    } else {
      var editorNode = document.createElement("input")
      editorNode.value = value
      editorNode.onkeydown = this.callback("_onLineEditKeyDown")
    }
    editorNode.onclick = this.callback("_onEditorClick")
    content.appendChild(editorNode)
  },
  
  // remove editor widget
  _removeEditor: function() {
    if (this._editingCell !== null) {
      if (!this._alwaysShowAllEditors) {
        var cell = this._editingCell
        var column = this._columns[cell.cellIndex]
        var row = cell.parentNode
        var item = row.mevis_item
        this._updateContent(cell, column, item)
      }
      this._editingCell = null
    }
  },
  
  // make sure that a click into an editor doesn't change the selection
  _onEditorClick: function(ev) {
    if (this._alwaysShowAllEditors) {
      // update editing cell, just in case...
      this._editingCell = this._getParentCellOfElement(ev.target)
    }
    ev.stopPropagation()
  },
  
  _onComboBoxChange: function(ev) {
    this._commitEditorValue()
  },
  
  _onLineEditKeyDown: function(ev) {
    if (ev.keyCode === KeyEvent.DOM_VK_RETURN) {
      this._commitEditorValue()
      this._removeEditor()
      ev.stopPropagation()
    } else {
      this._onNavigationKeyDown(ev)
    }
  },
  
  // this is called on both line inputs and combo boxes
  _onNavigationKeyDown: function(ev) {
    if (ev.keyCode === KeyEvent.DOM_VK_RETURN || ev.keyCode === KeyEvent.DOM_VK_ESCAPE) {
      // the new value should already have been committed when we get here
      this._removeEditor()
      ev.stopPropagation()
    } else if (ev.keyCode === KeyEvent.DOM_VK_TAB) {
      this._editNext(this._editingCell, ev.shiftKey)
      ev.preventDefault()
      ev.stopPropagation()
    }
  },
  
  // get next table cell
  _nextCell: function(cell, backwards) {
    var nextCell
    // got to previous/next cell
    if (backwards) {
      // goto previous cell
      nextCell = cell.previousElementSibling
      if (!nextCell) {
        // was last cell in row, go to previous row:
        var row = cell.parentNode.previousElementSibling
        if (row) {
          nextCell = row.lastElementChild
        } else {
          // was first row in table, go to last row
          var table = cell.parentNode.parentNode
          nextCell = table.lastElementChild.lastElementChild
        }
      }
    } else {
      // goto next cell
      nextCell = cell.nextElementSibling
      if (!nextCell) {
        // was last cell in row, go to previous row:
        var row = cell.parentNode.nextElementSibling
        if (row) {
          nextCell = row.firstElementChild
        } else {
          // was first row in table, go to last row
          var table = cell.parentNode.parentNode
          nextCell = table.firstElementChild.firstElementChild
        }
      }
    }
    return nextCell
  },
 
  _editNext: function(startCell, backwards, first) {
    // if first is set, try to set editor on startCell, otherwise
    // set editor on next possible cell
    this._commitEditorValue() // commit value of current editor
    var cell = startCell
    while(true) {
      if (first) {
        first = false
      } else {
        cell = this._nextCell(cell, backwards)
        if (cell === startCell) {
          // we checked every cell, no (other) cell was editable
          break
        }
      }
      // ok, now see if the cell is editable
      var column = this._columns[cell.cellIndex]
      var row = cell.parentNode
      var item = row.mevis_item
      if (this._getAttribute(item, column.editableAttribute)) {
        this._activateEditor(cell, column, item)
        break
      }
      // otherwise check the next cell
    }
  },
  
  _commitEditorValue: function() {
    if (this._editingCell !== null) {
      var cell = this._editingCell
      var editor = cell.mevis_content.firstChild
      if (editor.value !== undefined && editor.value !== null) {
        var column = this._columns[cell.cellIndex]
        var row = cell.parentNode
        var item = row.mevis_item
        item.setAttribute(column.editAttribute, editor.value)
      }
    }
  },
  
  // do cleanup when an item is fully removed:
  _removeItem: function(row, itemID) {
    // TODO: we will miss selected/expanded IDs if these have been folded away
    // when they are removed, but this will not be much of a problem - we can remove
    // these when we notice that these IDs aren't valid anymore
    delete this._selectedIDs[itemID]
    delete this._expandedIDs[itemID]
    if (row === this._lastSelectedTableRow) {
      // automatically deselect row
      this._selectTableRow(null)
    }
  },
  
  // remove the given row; if fully is false, the rows are just collapsed
  _removeRow: function(row, fully) {
    var item = row.mevis_item
    var itemID = item.getID()
    if (fully) {
      this._removeItem(row, itemID)
    }
    delete this._rowMap[itemID]
    this._removeSubRowsOf(row, fully)
    this._tableBody.deleteRow(row.sectionRowIndex)
  },
  
  // remove all sub-rows of the given row,;if fully is false, the rows are just collapsed
  _removeSubRowsOf: function(parentRow, fully) {
    var depth = parentRow ? parentRow.mevis_treeDepth+1 : 0
    var nextRowIndex = parentRow ? parentRow.sectionRowIndex+1 : 0
    while (true) {
      var subRow = this._tableBody.rows[nextRowIndex]
      if (!(subRow) || (subRow.mevis_treeDepth < depth)) {
        // stop at next item that has the same or higher depth in the hierarchy
        // (or if there are no more items):
        break
      }
      var itemID = subRow.mevis_item.getID()
      if (fully) {
        this._removeItem(subRow, itemID)
      }
      delete this._rowMap[itemID]
      this._tableBody.deleteRow(nextRowIndex)
    }
  },
  
})


MLAB.GUI.WidgetControlFactory.registerWidgetControl("ItemModelView", MLAB.GUI.MLItemModelViewControl)
