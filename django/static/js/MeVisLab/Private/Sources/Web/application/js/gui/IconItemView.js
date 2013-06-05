/** \class MLAB.GUI.ItemViewDerivedAttribute
 * 
 */
MLAB.GUI.defineClass("ItemViewDerivedAttribute", {
  ItemViewDerivedAttribute: function(name) {
    this.name = name
  },
  
  setup: function(tree) {
    this.name = tree.getValue()
    this.sourceAttribute = tree.childValue("sourceAttribute", null)
    this.defaultValue = tree.childValue("defaultValue", null)
    this.mappedValues = {}
    var caseTrees = tree.getAll("Case")
    for (var j=0;j<caseTrees.length;j++) {
      var caseTree = caseTrees[j]
      var key = caseTree.getValue()
      var value = caseTree.childValue("value", caseTree.childValue("pathValue"))
      this.mappedValues[key] = value
    }
  },
})

/** \class MLAB.GUI.ItemViewColumn
 * 
 */
MLAB.GUI.defineClass("ItemViewColumn", {
  ItemViewColumn: function(name, index) {
    this.name = name
    this.index = index
  },
  
  setup: function(tree, commonTree) {
    this.displayAttribute = tree.childValue("displayAttribute", this.name)
    if (this.displayAttribute.toLowerCase() === "none") {
      this.displayAttribute = null
    }
    this.editAttribute = tree.childValue("editAttribute", this.displayAttribute)
    this.iconAttribute = tree.childValue("iconAttribute", null)
    this.tooltipAttribute = this._getCommonColumnAttribute(tree, commonTree, "tooltipAttribute")
    this.checkboxAttribute = tree.childValue("checkboxAttribute", null)
    this.checkboxEditableAttribute = this._getCommonColumnAttribute(tree, commonTree, "checkboxEditableAttribute")
    this.editableAttribute = this._getCommonColumnAttribute(tree, commonTree, "editableAttribute")
    this.comboboxAttribute = tree.childValue("comboboxAttribute", null)
    this.comboboxTooltipsAttribute = tree.childValue("comboboxTooltipsAttribute", null)
    this.comboboxItemDelimiter = tree.childValue("comboboxItemDelimiter", "|")
    this.alignment = tree.childValue("align", null)
    this.sortAttributes = new Array()
    var sortAttributeString = tree.childValue("sortAttributes", this.displayAttribute)
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
        this.sortAttributes.push(sortAttributeEntry)
      }
    }
  },
  
  _getCommonColumnAttribute: function(childTree, tree, name) {
    attribute = childTree.childValue(name, null)
    if (attribute === null) {
      attribute = tree.childValue(name, null)
    }
    return attribute
  },
  
  _getCommonAttribute: function(tree, commonTree, name) {
    attribute = tree.childValue(name, null)
    if (attribute === null) {
      attribute = commonTree.childValue(name, null)
    }
    return attribute
  },
})

/** \class MLAB.GUI.ItemViewItem
 *  
 */
MLAB.GUI.deriveClass("ItemViewItem", MLAB.Core.Object, {
  ItemViewItem: function(itemView, modelItem) {
    MLAB.GUI.ItemViewItem.super.constructor.call(this)
    this._view = itemView
    this._modelItem = modelItem
    this._isSelected = false
    this._isExpanded = false // initially we don't have any children so they can't be visible
    this._children = []
  },
  
  getDOMElement: function() {
    MLAB.Core.throwException("Not implemented")
  },
  
  isExpanded: function() { return this._isExpanded },
  
  collapse: function() { this._isExpanded = false },
  
  expand: function() { this._isExpanded = true },
  
  modelItem: function() { return this._modelItem },
  
  hasChildren: function() { return this._modelItem.hasChildren() },
  
  setup: function(columns, depth) {
    MLAB.Core.throwException("Not implemented")
  },
  
  updateContent: function(column, alwaysShowAllEditors) {
    MLAB.Core.throwException("Not implemented")
  },
  
  setSelected: function(selected) {
    this._isSelected = selected
    // a derived class may add a CSS class to its DOM element, so that
    // selected items can be highlighted
  },
  
  removeAllChildren: function() {
    this.removeChildren(0, this._modelItem.getChildCount())
  },
  
  removeChildren: function(firstChildIndex, numberOfChildren) {
    MLAB.Core.throwException("Not implemented")
  },
  
  setupAllChildren: function() {
    this.setupChildren(0, this._modelItem.getChildCount())
  },

  setupChildren: function(firstChildIndex, numberOfChildren) {
    MLAB.Core.throwException("Not implemented")
  },
})


/** \class MLAB.GUI.IconItemViewItem
 * 
 */
MLAB.GUI.deriveClass("IconItemViewItem", MLAB.GUI.ItemViewItem, {
  IconItemViewItem: function(itemView, modelItem) {
    MLAB.GUI.IconItemViewItem.super.constructor.call(this, itemView, modelItem)
  },
  
  getDOMElement: function() { return this._table },

  // Each item is a table in which the columns described in the MDL will
  // be here represented as rows
  setup: function(columns, depth) {
    this._table = document.createElement("table")
    this._table.setAttribute("class", "MLAB-GUI-IconItemViewItem")
    this._lastSelectedTableRow = null
    this._selectedIDs = new Object()

    for (var i=0;i<columns.length;i++) {
      var column = columns[i]
      var tableRow = this._table.insertRow(i)
      var tableCell = tableRow.insertCell(0)
      tableRow.mevis_item = tableCell
      tableRow.onclick = this.callback("_handleOnRowClick")
      
      content = document.createElement("div")
      content.setAttribute("class", "MLAB-GUI-MLItemModelViewControl_CellContent")
      if (column.alignment) {
        content.setAttribute("align", column.alignment.toLowerCase())
      }
      tableCell.mevis_content = content
      tableCell.appendChild(content)
      
      this.updateContent(columns[i], this._view.alwaysShowAllEditors())
    }
  },
  
    
  updateContent: function(column, alwaysShowAllEditors) {
    // column is of class MLAB.GUI.ItemViewColumn

    // Colums are displayed as rows in the item table
    var row = this._table.rows[column.index]
    row.mevis_item = this._modelItem
    var cell = row.cells[0]
    // actual content:
    var content = cell.mevis_content
    var previousElement = content
    if (content.firstChild) {
      // purge the old content:
      content.removeChild(content.firstChild)
      var itemID = row.mevis_item.getID()
      delete this._selectedIDs[itemID]
    }

    // icon?
    if (column.iconAttribute) {
      var iconValue = this._getAttributeValue(column.iconAttribute)
      if (iconValue) {
        var icon
        if ("mevis_icon" in cell) {
          icon = cell.mevis_icon
        } else {
          icon = document.createElement("img")
          cell.mevis_icon = icon
          cell.appendChild(icon)
        }
        previousElement = icon
        // set the dimensions
        icon.onload = this.callback("_handleOnLoadIcon")
        
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
      var tooltipValue = this._getAttributeValue(column.tooltipAttribute);
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
      var checkboxValue = this._getAttributeValue(column.checkboxAttribute)
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
        checkbox.disabled = !this._getAttributeValue(column.checkboxEditableAttribute)
      } else if ("mevis_checkbox" in cell) {
        // remove checkbox
        cell.removeChild(cell.mevis_checkbox)
        delete cell.mevis_checkbox
      }
    }

    if (alwaysShowAllEditors && this._getAttributeValue(column.editableAttribute)) {
      // the item is editable in this column and should display its editor
      this._createEditor(cell, column);
    } else {
      // the item is not editable in this column or should not display its editor,
      // just append the data to the DOM element
      content.appendChild(document.createTextNode(this._getAttributeValue(column.displayAttribute)));
    }    
  },
  
  //Propagates the width to the first elements inside each cell
  //Maybe it's necessary to set the maxwidth too
  _handleOnLoadIcon: function(ev){
    var width = ev.target.width
    this._table.style.width = width + "px"
    for (i = 0; i < this._table.rows.length; i++){
        for (j = 0; j < this._table.rows[i].cells.length; j++){
            for (k = 0; k < this._table.rows[i].cells[j].childNodes.length; k++){
                var e = this._table.rows[i].cells[j].childNodes[k]
                    if (typeof(e) !== "undefined")
                        e.style.width = width + "px"
            }
        }
    }
  },
  
  // create an editor widget for the given cell
  _createEditor: function(cell, column) {
    var content = cell.mevis_content
    if (content.firstChild) {
      // purge the old content:
      content.removeChild(content.firstChild)
    }
    // don't forget that we use the editAttribute instead of the displayAttribute
    var value = this._getAttributeValue(column.editAttribute)
    var items = this._getAttributeValue(column.comboboxAttribute)
    var itemTooltips = this._getAttributeValue(column.comboboxTooltipsAttribute)
    
    var editorNode = null
    if (items) {
      var enumItems = items.split(column.comboboxItemDelimiter)
      var enumItemTooltips = itemTooltips.split(column.comboboxItemDelimiter)
      if ((enumItemTooltips.length > 0) && (enumItemTooltips.length !== enumItems.length)) {
        this.getModule().logError("MLAB.GUI.MLItemModelViewControl: " +
                                  "comboboxTooltipsAttribute " + column.comboboxTooltipsAttribute + 
                                  " has different (but non-zero) number of items than comboboxAttribute " + 
                                  column.comboboxAttribute + " (" + enumItemTooltips + " vs. " + enumItems + ")!")
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
  
  _getAttributeValue: function(attributeName) {
    return this._view.getAttribute(this._modelItem, attributeName)
  },
  
  _handleOnRowClick: function(ev) {
    // TODO: implement different selection modes
    var tryEdit = false
    var row = this._getParentRowOfElement(ev.target)
    if (this._view._selectionMode !== "NoSelection") {
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
    var row = this._getParentRowOfElement(ev.target)
    var cell = this._getParentCellOfElement(ev.target)
    if (cell !== this._editingCell) {
      this._removeEditor()
    }
    if (tryEdit) {
      var cell = this._getParentCellOfElement(ev.target)
      var column = this._view._columns[row.rowIndex]
      var item = row.mevis_item
      if (this._view.getAttribute(item, column.editableAttribute)) {
        this._activateEditor(cell, column, item)
      }
    }
  },
  
  // activate editor widget for the given cell, creating it if necessary
  _activateEditor: function(cell, column, modelItem) {
    if (cell === this._editingCell) {
      // already editing
      return
    }
    if (!this._view._alwaysShowAllEditors) {
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
  
   // remove editor widget
  _removeEditor: function() {
    if (this._editingCell !== null) {
      if (!this._view._alwaysShowAllEditors) {
        var cell = this._editingCell
        var row = cell.parentNode
        var column = this._view._columns[row.rowIndex]
        var item = row.mevis_item
        this._updateContent(cell, column, item)
      }
      this._editingCell = null
    }
  },
  
  // update the cell currently being edited pointer
  _updateEditingCell: function(ev) {
    var cell = this._getParentCellOfElement(ev.target)
    this._editingCell = cell
    if (this._editingCell === null 
        || typeof(this._editingCell) === "undefined") {
        // if we can't find the cell, we select the first editable element
        // in the table
        var editor = $(this._table).find("select,input").eq(0)
        this._editingCell = this._getParentCellOfElement(editor)
      }
  },
  
  // make sure that a click into an editor doesn't change the selection
  _onEditorClick: function(ev) {
    if (this._view.alwaysShowAllEditors()) {
      // update editing cell, just in case...
      
      // BUG 6452:
      // Because of live DOM edition, this method would fail under
      // certain circumstances, the responsibility of updating
      // this._editingCell is now of other events
      // this._editingCell = this._getParentCellOfElement(ev.target)
    }
    ev.stopPropagation()
  },
  
  _onComboBoxChange: function(ev) {
    this._updateEditingCell(ev)
    this._commitEditorValue()
    this._editingCell.mevis_content.firstChild.focus()
    ev.stopPropagation()
  },
  
  _onLineEditKeyDown: function(ev) {
    if (ev.keyCode === MLAB.Core.KeyEvent.DOM_VK_RETURN) {
      this._commitEditorValue()
      this._removeEditor()
      ev.stopPropagation()
    } else {
      this._onNavigationKeyDown(ev)
    }
  },
  
  // this is called on both line inputs and combo boxes
  _onNavigationKeyDown: function(ev) {
    if (ev.keyCode === MLAB.Core.KeyEvent.DOM_VK_RETURN || ev.keyCode === MLAB.Core.KeyEvent.DOM_VK_ESCAPE) {
      // the new value should already have been committed when we get here
      this._removeEditor()
      ev.stopPropagation()
    } else if (ev.keyCode === MLAB.Core.KeyEvent.DOM_VK_TAB) {
      this._updateEditingCell(ev)
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
          var tbody = cell.parentNode.parentNode
          nextCell = tbody.firstElementChild.firstElementChild
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
    // table < tbody < tr < td
    var startTable = cell.parentNode.parentNode.parentNode
    var table = startTable
    while(true) {
      if (first) {
        first = false
      } else {
        cell = this._nextCell(cell, backwards)
        if (cell === startCell) {
          // we checked every cell, no (other) cell was editable
          // get the next/previous table from the parent
          
          var nextTable = null
          if (backwards) {
            nextTable = table.previousElementSibling
            if (!nextTable){
              // that was the first table, we go to the last one
              nextTable = table
              do {
                nextTable = nextTable.nextElementSibling
              } while (nextTable.nextElementSibling)
            }
          }
          else {
            nextTable = table.nextElementSibling
             if (!nextTable){
              // that was the last table, we go back to the first one
              nextTable = table
              do {
                nextTable = nextTable.previousElementSibling
              } while (nextTable.previousElementSibling)
            }
          }
          table = nextTable

          if (table.tagName.toLowerCase() === "table"){
            // table > tbody > tr > td
            cell = table.firstElementChild.firstElementChild.firstElementChild
            // we have looped through all the tables
            if (table === startTable){
              break
              first = true
            }
          }
        }
      }
      
      // ok, now see if the cell is editable
      var row = cell.parentNode
      var column = this._view._columns[row.rowIndex]
      var item = row.mevis_item
      if (this._getAttributeValue(column.editableAttribute)) {
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
        var row = cell.parentNode
        var column = this._view._columns[row.rowIndex]
        var item = row.mevis_item
        item.setAttribute(column.editAttribute, editor.value)
      }
    }
  },
  
  // used in event handling
  _getParentRowOfElement: function(target) {
    if (target === null)
        return null
    if (target.tagName.toLowerCase() === "tr") {
      return target
    } else {
      return this._getParentRowOfElement(target.parentNode)
    }
  },
  
  _getParentCellOfElement: function(target) {
    if (target === null)
      return null
    var tagName = target.tagName.toLowerCase()
    if (tagName === "td" || tagName === "th") {
      return target
    } else {
      return this._getParentCellOfElement(target.parentNode)
    }
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
  
  setSelected: function(selected) {
    MLAB.GUI.IconItemView.super.setSelected.call(this, selected)
    if (selected) {
      MLAB.GUI.addStyleSheetClass(this._table, "MLAB-GUI-Selected")
    } else {
      MLAB.GUI.removeStyleSheetClass(this._table, "MLAB-GUI-Selected")
    }
  },
  
  removeChildren: function(firstChildIndex, numberOfChildren) {
    for (var i = firstChildIndex; i < numberOfChildren; i++){
      this._table.deleteRow(i)
    }
  },
  
  setupChildren: function(firstChildIndex, numberOfChildren) {
    // setup DOM elements for the children from the modelItem
    /* NOTE: IconItemViewItem has no children
    for (var i=firstChildIndex; i<numberOfchildren; i++) {
        var child = this._view.createItem(this._modelItem.getChild(i))
        this._children.push(child)
        child.setup(this._view.getColumns(), this._depth+1)
    // TODO: add the child dom element to this dom element
    }
    */
  },
})

/** \class MLAB.GUI.ItemView
 * 
 */
MLAB.GUI.deriveClass("ItemView", MLAB.GUI.Widget, {
  ItemView: function(mdlTree, module) {
    MLAB.GUI.ItemView.super.constructor.call(this, mdlTree, module)
    this.registerSignal("selectionChanged")
    this.registerSignal("rowsAdded")
    
    this._columns = []
    this._itemsByID = []
    
    // store a map of which columns to update when an attribute changes -
    // the object stores a map from attribute names to bitsets (stored as numbers)
    // (this restricts the number of columns to a probably small number)
    this._columnUpdateMap = {}
    
    this._lastSelectedTableRow = null

    this._addingRows = 0  // recursion counter
    
    // item model will be null initially (implementation will be provided by ItemModelHandler)
    this._model = null
    
    this._visibleRows = 5
  },
  
  alwaysShowAllEditors: function() { return this._alwaysShowAllEditors },
  setAlwaysShowAllEditors: function(alwaysShowAllEditors) { this._alwaysShowAllEditors = alwaysShowAllEditors },  
  setIdAttribute: function(idAttribute) { this._idAttribute = idAttribute },
  setIdAsFullPath: function(idAsFullPath) { this._idAsFullPath = idAsFullPath },
  setIdPathSeparator: function(idPathSeparator) { this._idPathSeparator = idPathSeparator },
  setSelectionMode: function(selectionMode) { this._selectionMode = selectionMode },
  setDerivedAttributes: function(derivedAttributes) { this._derivedAttributes = derivedAttributes },
  setVisibleRows: function(visibleRows) { this._visibleRows = visibleRows },
  
  setHeaderVisible: function(visible) {
    //MLAB.Core.throwException("Not implemented")
  },
  
  getColumns: function() { return this._columns },
  
  addColumn: function(column) {
    this._columns.push(column)
    
    this._columnUsesAttribute(column.index, column.displayAttribute)
    this._columnUsesAttribute(column.index, column.iconAttribute)
    this._columnUsesAttribute(column.index, column.tooltipAttribute);
    this._columnUsesAttribute(column.index, column.checkboxAttribute)
    this._columnUsesAttribute(column.index, column.checkboxEditableAttribute)
    
    this._handleColumnAdded(column)
  },
  
  _handleColumnAdded: function(column) {
    // a sub class may populated the header here
  },
  
  getItemByModelItem: function(modelItem) {
    if (modelItem.isRoot()) {
      return this._rootItem
    }
    return this._itemsByID[modelItem.getID()]
  },
  
  setModel: function(model) {
    if (this._model) {
      this._model.removeListener(this)
      // remove everything unter the root item:
      this._rootItem.removeAllChildren()
    }

    this._model = model
    
    if (this._model) {
      this._checkTable()
      this._model.addListener(this)
      // add all direct children of the root item:
      this._rootItem = new MLAB.GUI.ItemViewItemContainer(this, this._model.getRootItem())
      this._rootItem.setupAllChildren()
      this._rootItem.expand()
    }
  },
  
  // get attribute value from item
  getAttribute: function(item, attributeName) {
    var result = ''
    if (attributeName) {
      if (attributeName in this._derivedAttributes) {
        var derivedAttribute = this._derivedAttributes[attributeName]
        var key = this.getAttribute(item, derivedAttribute.sourceAttribute)
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
  
  updateSelection: function(selectionIds, selectionCount) {
    MLAB.Core.throwException("Not implemented")
  },
  /*
  // returns the id attribute value of the item
  _getModelItemID: function(modelItem) {
    return this.getAttribute(modelItem, this._idAttribute)
  },
  
  // get ID string of an item as specified with the idXxx tags
  _getID: function(modelItem) {
    var id = this._getModelItemID(modelItem)
    if (this._idAsFullPath) {
      // create id as a path
      while ((modelItem = modelItem.getParent()) && !modelItem.isRoot()) {
        id = this._getModelItemID(modelItem) + this._idPathSeparator + id
      }
    }
    return id
  },*/

  _createDOMElement: function() {
    MLAB.Core.throwException("Not implemented")
  },
  
  setSorting: function(column, inverted) {
    MLAB.Core.throwException("Not implemented")
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
  
  // check if an attribute even exists:
  _checkAttributeName: function(attrName) {
    if (attrName && attrName !== true && !this._model.hasAttribute(attrName) &&
        !(attrName in this._derivedAttributes))
    {
      this.logError("MLAB.GUI.ItemViewControl: " +
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
  
  // listener callback
  itemChanged: function(modelItem, before) {
    var item = this.getItemByModelItem(modelItem) 
    if (item && (item.isExpanded() || modelItem.isRoot())) {
      // the item is visible
      if (before) {
        item.removeAllChildren()
      } else {
        item.setupAllChildren()
      }
    }
  },
  
  // listener callback
  itemsInserted: function(parentModelItem, at, amount, before) {
    if (!before) {
      var parentItem = this.getItemByModelItem(parentModelItem)
      if (parentItem && (parentItem.isExpanded() || parentModelItem.isRoot())) {
        // the item is visible
        parentItem.setupChildren(at, amount)
      }
    }
  },
  
  // listener callback
  itemsRemoved: function(parentModelItem, at, amount, before) {
    if (before) {
      var parentItem = this.getItemByModelItem(parentModelItem)
      if (parentItem) {
        parentItem.removeChildren(at, amount)
      }
    }
  },
  
  // listener callback
  dataChanged: function(modelItems, attributes) {
    // which columns must be updated when the given attributes have changed:
    var columns = 0
    for (var i=0;i<attributes.length;i++) {
      if (attributes[i] in this._columnUpdateMap) {
        columns = columns | this._columnUpdateMap[attributes[i]]
      }
    }
    // iterate over modelItems:
    for (var i=0;i<modelItems.length;i++) {
      var item = this.getItemByModelItem(modelItems[i])
      if (item) {
        for (var col=0;col<this._columns.length;col++) {
          if (((1 << col) & columns) !== 0) {
            // update item content:
            item.updateContent(this._columns[col], this._alwaysShowAllEditors)
          }
        }
      }
    }
  },
  
  createItem: function(modelItem) {
    MLAB.Core.throwException("Not implemented")
  },
})
  
/** \class MLAB.GUI.IconItemView
 * HTML container for the items
 */
MLAB.GUI.deriveClass("IconItemView", MLAB.GUI.ItemView, {
  IconItemView: function(mdlTree, module) {
    MLAB.GUI.IconItemView.super.constructor.call(this, mdlTree, module)
  },
    
  _createDOMElement: function() {
    var div = document.createElement("div")
    div.setAttribute("class", "MLAB-GUI-IconItemView")
    this._setDOMElement(div)
  },
 
  updateSelection: function(selectionIds, selectionCount) {
    // TO BE IMPLEMENTED
  },
  
  // change sorting of table
  setSorting: function(column, inverted) {
    // TO BE IMPLEMENTED
  },

  createItem: function(modelItem) {
    var item = new MLAB.GUI.IconItemViewItem(this, modelItem)
    this._itemsByID[modelItem.getID()] = item
    return item
  },
})

MLAB.GUI.WidgetFactory.registerWidgetClass("IconItemView", MLAB.GUI.IconItemView)

/** \class MLAB.GUI.ItemViewItemContainer
 * Item container inside ItemView
 */
MLAB.GUI.deriveClass("ItemViewItemContainer", MLAB.GUI.ItemViewItem, {
  ItemViewItemContainer: function(itemView, modelView) {
    MLAB.GUI.ItemViewItemContainer.super.constructor.call(this, itemView, modelView)
  },
    
  _createDOMElement: function() {
    // NOTHING
  },
 
  updateSelection: function(selectionIds, selectionCount) {
    // TO BE IMPLEMENTED
  },
  
  // change sorting of table
  setSorting: function(column, inverted) {
    // TO BE IMPLEMENTED
  },
  
  setupChildren: function(firstChildIndex, numberOfChildren) {
    for (var i=firstChildIndex; i<firstChildIndex+numberOfChildren; i++) {
        var child = this._view.createItem(this._modelItem.getChild(i))
        this._children.push(child)
        child.setup(this._view.getColumns(), this._depth+1)
        this._view._getDOMElement().appendChild(child.getDOMElement())
    }
  },
  
  removeChildren: function(firstChildIndex, numberOfChildren) {
    for (var i=firstChildIndex; i<numberOfChildren; i++) {
        var child = this._children[i]
        this._view._getDOMElement().removeChild(child.getDOMElement())
        child.removeAllChildren()
    }
    this._children.splice(firstChildIndex, numberOfChildren)
  },
})