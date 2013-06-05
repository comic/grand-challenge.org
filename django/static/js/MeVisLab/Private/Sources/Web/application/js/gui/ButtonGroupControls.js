/** \class MLAB.GUI.CommonButtonGroupItem
 * 
 */
MLAB.GUI.deriveClass("CommonButtonGroupItem", MLAB.Core.Object, {
  CommonButtonGroupItem: function(itemTree, control) {
    this._fieldExpressionEvaluators = []
    this._widget = this._createWidget()
    this._widget.addStyleSheetClass("MLAB-GUI-CommonButtonGroupItem")
    this._tree = itemTree
    this._control = control
    this._enumItem = null
    var f = this._control.getField()
    if (f && f.isEnumField()) {
      this._enumItem = f.item(this._tree.getValue())
    }
    this._value = this._tree.getValue()
    this._setupTypicalTags()
  },
  
  value: function() { return this._value },
  
  enumItem: function() { return this._enumItem },
  
  widget: function() {
    return this._widget
  },
  
  _createWidget: function() { MLAB.Core.throwException("Not implemented") },
  
  setChecked: function(checked) { MLAB.Core.throwException("Not implemented") },
  isChecked: function() { MLAB.Core.throwException("Not implemented") },
  
  _setupTypicalTags: function() {
    var enabled = MLAB.Core.convertMDLValueToBool(this._tree.childValue("enabled", "yes"))
    if (!enabled) {
      this._widget.setEnabled(false)
    }
    var visible = MLAB.Core.convertMDLValueToBool(this._tree.childValue("visible", "yes"))
    if (!visible) {
      this._widget.setVisible(false)
    }
    
    var title = null
    if (this._enumItem) {
      if (this._control._stripEnumItemPrefix || !this._enumItem.hasAutoTitle()) {
        title = this._enumItem.title() 
      } else {
        title = this._enumItem.value()
      }
    }
    title = this._tree.childValue("title", title)
    if (title || title === "") {
      this._title = title
    } else {
      this._title = this._tree.getValue()
    }
    
    this._exclusiveButtons = this._tree.childValue("exclusiveButtons", null)
    
    this._tooltip = this._tree.childValue("tooltip", null)
    this._command = this._tree.childValue("command", null)
    this._image = MLAB.Core.translatePath(this._tree.childValue("image", null))
    this._activeOnImage = MLAB.Core.translatePath(this._tree.childValue("activeOnImage", null)) 
    this._activeOffImage = MLAB.Core.translatePath(this._tree.childValue("activeOffImage", null))
    this._disabledOnImage = MLAB.Core.translatePath(this._tree.childValue("disabledOnImage", null))
    this._disabledOffImage = MLAB.Core.translatePath(this._tree.childValue("disabledOffImage", null))
    this._normalOnImage = MLAB.Core.translatePath(this._tree.childValue("normalOnImage", null))
    this._normalOffImage = MLAB.Core.translatePath(this._tree.childValue("normalOffImage", null))
  },
  
  setupFieldExpressionEvaluators: function() {
    var dependsOn = this._tree.childValue("dependsOn", null)
    if (dependsOn) {
      this._addFieldExpressionEvaluator(dependsOn, this._widget, "setEnabled")
    }
    var visibleOn = this._tree.childValue("visibleOn", null)
    if (visibleOn) {
      this._addFieldExpressionEvaluator(visibleOn, this._widget, "setVisible")
    }
  },
  
  _addFieldExpressionEvaluator: function(expression, receiver, slot) {
    var fieldExpressionEvaluator = new MLAB.Core.FieldExpressionEvaluator(expression, this._control.getModule())
    fieldExpressionEvaluator.connect("resultChanged", receiver, slot)
    // initially trigger the evaluator
    fieldExpressionEvaluator.fieldChanged()
    this._fieldExpressionEvaluators.push(fieldExpressionEvaluator)
  },
  
})

/** \class MLAB.GUI.CommonButtonGroupControl
 * 
 */
MLAB.GUI.deriveClass("CommonButtonGroupControl", MLAB.GUI.WidgetControl, {
  CommonButtonGroupControl: function(mdlTree, module) {
    this._items = []
    MLAB.GUI.CommonButtonGroupControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._table = MLAB.GUI.WidgetFactory.create("Table", id)
    this._table.setControl(this)
    return this._table
  },
  
  hasExclusiveButtons: function() {
    return this._exclusiveButtons
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.CommonButtonGroupControl.super.setupTypicalTags.call(this)
    
    var exclusiveButtonsDefault = this.getField() !== null ? "true" : "false"
    
    this._buttonClickedCommand = this._mdlTree.childValue("buttonClickedCommand", null)
    this._buttonPressedCommand = this._mdlTree.childValue("buttonPressedCommand", null)
    this._exclusiveButtons = MLAB.Core.convertMDLValueToBool(this._mdlTree.childValue("exclusiveButtons", exclusiveButtonsDefault))
    var orientation = this._mdlTree.childValue("orientation", "horizontal").toLowerCase()
    if (orientation === "horizontal") {
      this._orientation = MLAB.GUI.HORIZONTAL
      this._widget.addStyleSheetClass("MLAB-GUI-HorizontalButtonGroup")
    } else {
      this._orientation = MLAB.GUI.VERTICAL
      this._widget.addStyleSheetClass("MLAB-GUI-VerticalButtonGroup")
    }
    
    this._stripEnumItemPrefix = MLAB.Core.convertMDLValueToBool(this._mdlTree.childValue("stripEnumItemPrefix", "true"))
    
    this._setupItems()
  },
  
  _setupItems: function() {
    var strips = parseFloat(this._mdlTree.childValue("strips", "1.0"))
    
    var itemsTree = this._mdlTree.get("items")
    if (itemsTree) {
      
      var itemsPerStrip = Math.ceil(itemsTree.count()/strips)
      var row = 0
      var column = 0
      
      for (var i=0; i<itemsTree.count(); i++) {
        var item = this._createItem(itemsTree.child(i))
        item.setupFieldExpressionEvaluators()
        this._items.push(item)
        this._table.addWidget(row, column, item.widget())
        if (this._orientation === MLAB.GUI.HORIZONTAL) {
          column++
          if (column === itemsPerStrip) {
            column = 0
            row++
          }
        } else {
          row++
          if (row === itemsPerStrip) {
            row = 0
            column++
          }
        }
      }
    }
    
    if (this.getField() !== null) {
      this.fieldChanged(this.getField())
    }
  },
  
  _createItem: function(itemTree) {
    MLAB.Core.throwException("Not implemented")
  },
  
  fieldChanged: function(field) {
    if (field === this.getField()) {
      var value = (field.isEnumField() || field.isIntegerField()) ? field.stringValue() : null

      var itemToCheck = null
      for (var i=0; i<this._items.length; i++) {
        if (value === this._items[i].value()) {
          itemToCheck = this._items[i]
        } else if (this._exclusiveButtons) {
          this._items[i].setChecked(false)
        }
      }
      if (itemToCheck) {
        itemToCheck.setChecked(true)
      }
    }
  },
  
  itemCheckStateChanged: function(item, checked) {
    if (this._exclusiveButtons) {
      for (var i=0; i<this._items.length; i++) {
        if (item !== this._items[i]) { 
          this._items[i].setChecked(false)
        }
      }
    }
    if (checked) {
      var field = this.getField()
      if (field !== null && (field.isEnumField() || field.isIntegerField())) {
        field.setStringValue(item.value())
      }
    }
  },
})


/** \class MLAB.GUI.PushButtonGroupItem
 * 
 */
MLAB.GUI.deriveClass("PushButtonGroupItem", MLAB.GUI.CommonButtonGroupItem, {
  PushButtonGroupItem: function(itemTree, control) {
    MLAB.GUI.PushButtonGroupItem.super.constructor.call(this, itemTree, control)
    this._widget.addStyleSheetClass("MLAB-GUI-PushButtonGroupItem")
  },
  
  _createWidget: function() {
    this._button = MLAB.GUI.WidgetFactory.create("Button")
    return this._button
  },
  
  _setupTypicalTags: function() {
    MLAB.GUI.PushButtonGroupItem.super._setupTypicalTags.call(this)
    
    this._button.setCheckable(true)
    
    if (this._title !== "") {
      this._button.setTitle(this._title)
    }
    
    if (this._command) {
      this._button.connect("clicked", this, "_onClick")
    }
    
    this._button.connect("checkStateChanged", this, "_onCheckStateChange")
    
    if (this._image) {
      var image = MLAB.Core.translatePath(this._image)
      this._button.setImageUrl(image)
    }

    if (this._tooltip) {
      this._button.setToolTip(this._tooltip)
    }
    
    if (this._activeOnImage) { this._button.setActiveOnImage(this._activeOnImage) }
    if (this._activeOffImage) { this._button.setActiveOffImage(this._activeOffImage) }
    if (this._disabledOnImage) { this._button.setDisabledOnImage(this._disabledOnImage) }
    if (this._disabledOffImage) { this._button.setDisabledOffImage(this._disabledOffImage) }
    if (this._normalOnImage) { this._button.setNormalOnImage(this._normalOnImage) }
    if (this._normalOffImage) { this._button.setNormalOffImage(this._normalOffImage) }
  },
  
  _onCheckStateChange: function(checked) {
    this._control.itemCheckStateChanged(this, checked)
  },
  
  _onClick: function() {
    if (this._control.hasExclusiveButtons()) {
      // if buttons are exclusive, then clicking them should not toggle the check state,
      // since it is not clear which button needs to be checked if one is unchecked.
      // Note that _onCheckStateChange(false) was already called for this button and
      // the setChecked(true) call will trigger an _onCheckStateChange(true) call.
      if (!this._button.isChecked()) {
        this._button.setChecked(true)
      }
    }
    this._control.sendGenericRequest(this._command, [])
  },
  
  setChecked: function(checked) { this._button.setChecked(checked) },
  isChecked: function() { return this._button.isChecked() },
})


/** \class MLAB.GUI.PushButtonGroupControl
 * 
 */
MLAB.GUI.deriveClass("PushButtonGroupControl", MLAB.GUI.CommonButtonGroupControl, {
  PushButtonGroupControl: function(mdlTree, control) {
    this._buttons = []
    MLAB.GUI.PushButtonGroupControl.super.constructor.call(this, mdlTree, control)
  },

  setupTypicalTags: function() {
    MLAB.GUI.PushButtonGroupControl.super.setupTypicalTags.call(this)
  },
  
  _createItem: function(itemTree) {
    return new MLAB.GUI.PushButtonGroupItem(itemTree, this)
  },
})

MLAB.GUI.WidgetControlFactory.registerWidgetControl("PushButtonGroup", MLAB.GUI.PushButtonGroupControl)
