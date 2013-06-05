/** \class MLAB.GUI.IconItemViewControl
 * 
 */
MLAB.GUI.deriveClass("IconItemViewControl", MLAB.GUI.WidgetControl, {
  IconItemViewControl: function(mdlTree, module) {
    MLAB.GUI.IconItemViewControl.super.constructor.call(this, mdlTree, module)
    
    this._selectionFieldLock = false
    
    this._pendingSelection = false
  },
  
  createWidget: function(id) {
    var w = MLAB.GUI.WidgetFactory.create("IconItemView", id)
    w.setControl(this)
    this._view = w
    return w
  },

  setupTypicalTags: function() {
    MLAB.GUI.IconItemViewControl.super.setupTypicalTags.call(this, "MLAB-GUI-IconItemViewControl")
    
    this._view.connect("rowsAdded", this, "_rowsAdded")
    
    // Decide if all editable fields should show the editors by default
    var alwaysShowAllEditors = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("alwaysShowAllEditors", "false"))
    this._view.setAlwaysShowAllEditors(alwaysShowAllEditors)

    this._view.setIdAttribute(this.getMDLAttribute("idAttribute", null))
    this._view.setIdAsFullPath(MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("idAsFullPath", "false")))
    this._view.setIdPathSeparator(this.getMDLAttribute("idPathSeparator", "/"))    
    var showHeader = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("header", "true"))
    this._view.setHeaderVisible(showHeader)
    this._view.setVisibleRows(parseInt(this.getMDLAttribute("visibleRows", "5")))
    
    this._idSeparator = this.getMDLAttribute("idSeparator", ";")
    
    // these fields may be null if not specified
    this._currentField = this.getMDLFieldAttribute("currentField")
    this._selectionField = this.getMDLFieldAttribute("selectionField")
    if (this._selectionField) {
      this._selectionField.addListener(this)
    }
    
    if (this._currentField || this._selectionField) {
      this._view.connect("selectionChanged", this, "viewSelectionChanged")
    }
    
    this._view.setSelectionMode(this.getMDLAttribute("selectionMode"))
    
    // store derived attributes information
    this._parseDerivedAttributes()
    
    this._setupColumns()

    // sorting
    var sortByColumn = this.getMDLAttribute("sortByColumn", "-1")  // -1 means unsorted
    var sortAscending = this.getMDLAttribute("sortAscending", "true")
    this._view.setSorting(new Number(sortByColumn), MLAB.Core.convertMDLValueToBool(sortAscending) ? 1 : -1)
    
    // update field value
    this._baseFieldChanged()
    if (this._selectionField) {
      this._selectionFieldChanged()
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
    if (this._field && this._field.isBaseField()) {
      var model = this._field.getValue()
      this._view.setModel(model)
    } else {
      // this should rarely happen - but we handle it, too
      this._view.setModel(null)
    }
  },

  _selectionFieldChanged: function() {
    if (!this._selectionFieldLock) {
      this._selectionFieldLock = true
      // try to support multiple selections, even if the remaining code does not - yet!
      var ids = (''+this._selectionField.getValue()).split(this._idSeparator)
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
      this._pendingSelection = this._view.updateSelection(selectionIds, selectionCount)
      
      this._selectionFieldLock = false
    }
  },
  
  viewSelectionChanged: function(value) {
    if (this._currentField)  {
      this._currentField.setValue(value) 
    }
    if (this._selectionField && !this._selectionFieldLock) {
      this._selectionFieldLock = true
      this._selectionField.setValue(value)
      this._selectionFieldLock = false
    }
    this._pendingSelection = false // reset
  },
  
  _rowsAdded: function() {
    // update selection if necessary
    if (this._pendingSelection) {
      this._selectionFieldChanged()
    }
  },

  _parseDerivedAttributes: function() {
    var derivedAttributes = {}
    var derivedAttributeTrees = this._mdlTree.getAll("DerivedAttribute")
    for (var i=0; i<derivedAttributeTrees.length; i++) {
      var childTree = derivedAttributeTrees[i]
      var derivedAttribute = new MLAB.GUI.ItemViewDerivedAttribute(childTree.getValue())
      derivedAttribute.setup(childTree.getValue())
      derivedAttributes[derivedAttribute.name] = derivedAttribute
    } 
    this._view.setDerivedAttributes(derivedAttributes)
  },
  
  _setupColumns: function() {
    var columnTrees = this._mdlTree.getAll("Column")
    for (var i=0; i<columnTrees.length; i++) {
      var childTree = columnTrees[i]
      var column = new MLAB.GUI.ItemViewColumn(childTree.getValue(), i)
      column.setup(childTree, this._mdlTree)
      this._view.addColumn(column)
    }
  },
})

MLAB.GUI.WidgetControlFactory.registerWidgetControl("IconItemView", MLAB.GUI.IconItemViewControl)
