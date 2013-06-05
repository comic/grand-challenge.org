/** \class MLAB.GUI.WidgetControlModuleInterface
 * 
 * Base class for MLAB.GUI.WidgetControl which is an interface for all module related
 * communication. It stores a reference to the MLABModule with which it works.
 */
MLAB.GUI.deriveClass("WidgetControlModuleInterface", MLAB.Core.Object, {
  WidgetControlModuleInterface: function(module) {
    MLAB.GUI.WidgetControlModuleInterface.super.constructor.call(this)
    this._module = module
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.createSubControl
   * 
   * Calls MLABModule.createControl() and returns the control, or null if it could not be created.
   */
  createSubControl: function(mdlTree) { 
    return this._module.createControl(mdlTree) 
  },
  
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.log
   * 
   * Logs a message by calling MLABModule.log().
   * 
   * \param message The log message string.
   */
  log: function(message) {
    this._module.log(message) 
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.logError
   * 
   * Logs an error message by calling MLABModule.logError().
   * 
   * \param error The error message string.
   */
  logError: function(error) { 
    this._module.logError(error) 
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.logException
   * 
   * Logs an exception by calling MLABModule.logException().
   * 
   * \param exception The exception.
   */
  logException: function(exception) {
    this._module.logException(exception)
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.getModule
   * 
   * Returns the module.
   * 
   * \return The MLABModule.
   */
  getModule: function() {
    return this._module
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.field
   * 
   * Looks for a field and it by calling MLABModule.field().
   * 
   * \param fieldName The field name string.
   * \return Returns the MLAB.Core.Field, or null if it was not found.
   */
  field: function(fieldName) {
    return this._module.field(fieldName)
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.sendBaseFieldMessage
   * 
   * Creates a base field message using the provided class and data. 
   * Calls MLABModule.sendBaseFieldMessage().
   * 
   * \param baseFieldMessageClass The message class. See \ref RemoteMessages for possible messages.
   * \param data A mapping object containing the attributes that required by the message, e.g.: {pox_x: 10, pox_y: 52}
   */
  sendBaseFieldMessage: function(baseFieldMessageClass, data) {
    this._module.sendBaseFieldMessage(this._field, baseFieldMessageClass, data)
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.log
   * 
   * Logs a message by calling MLABModule.log().
   * 
   * \param message The log message string.
   */
  sendGenericRequest: function(request, args) {
    this._module.sendGenericRequest(request, args)
  },
  
  /** \fn MLAB.GUI.WidgetControlModuleInterface.log
   * 
   * Logs a message by calling MLABModule.log().
   * 
   * \param message The log message string.
   */
  sendMessage: function(message) {
    this._module.sendMessage(message)
  }
})


/** \class MLAB.GUI.WidgetControl(MLAB.GUI.WidgetControlModuleInterface)
 *
 * This is the base class for all widget controls. The widget controls are based on
 * the \ref guiscript in MeVisLab, which have also a base class ::MLAB.GUI.WidgetControl.
 * 
 * \param mdlTree The MDL tree that defines this control and its sub controls.
 * \param module The MLABModule to which this control belongs.
 */
MLAB.GUI.deriveClass("WidgetControl", MLAB.GUI.WidgetControlModuleInterface, {
  WidgetControl: function(mdlTree, module) {
    MLAB.GUI.WidgetControl.super.constructor.call(this, module)

    this._widget = null
    this._field = null
    this._mdlTree = mdlTree
    this._children = []
    this._fieldExpressionEvaluators = []
    this._name = this.getMDLAttribute("name", null)
    this.registerSignal("tabEnabledChanged")
  },
  
  /** \fn MLAB.GUI.WidgetControl.destroy
   * 
   * The destructor. Calls the destructor of each child control. We do not need this
   * to clear memory in Javascript, but it may be necessary to notify the server
   * about a destroyed control. For example, the remote rendering control needs to
   * send a MLAB.Core.RenderingRenderStopStreamingMessage on destruction.
   */
  destroy: function() {
    for (var i=0; i<this._children.length; i++) {
      this._children[i].destroy()
    }
  },
  
  hide: function() {
    this.setVisible(false)
  },
  
  show: function() {
    this.setVisible(true)
  },
  
  setVisible: function(visible) {
    this._widget.setVisible(visible)
  },
  
  isVisible: function() {
    return this._widget.isVisible()
  },
  
  setEnabled: function(enabled) {
    this._widget.setEnabled(enabled)
  },
  
  /** \fn MLAB.GUI.WidgetControl.getName
   * 
   * Returns the name of the control.
   * 
   * \return The name string.
   */
  getName: function() {
    return this._name
  },

  getField: function() {
    return this._field 
  },
  
  getWidget: function() {
    return this._widget 
  },

  isFieldControl: function() {
    return false 
  },
  
  fieldChanged: function(field) {
    // can be reimplemented in a sub class
  },
  
  createWidget: function(id) {
    var w = MLAB.GUI.WidgetFactory.create("Widget", id)
    w.setControl(this)
    return w
  },
  
  _setupGUI: function() {
    var id = this._name
    if (!id) {
      id = MLAB.GUI.getNextID().toString()
    }
    
    this._widget = this.createWidget(id)
    
    var classNames = []
    var superClass = this.constructor
    while (superClass) {
      classNames.splice(0, 0, superClass.prototype.getClassName())
      if (superClass.super.constructor == MLAB.GUI.WidgetControl.super.constructor) {
        break
      }
      superClass = superClass.super.constructor
    }
    this._widget.addStyleSheetClass(classNames.join(" ").replace(/\./g, '-'))
    
    var mdlCSSClass = this.getMDLAttribute("html_cssClass", null)
    if (mdlCSSClass) {
      this._widget.addStyleSheetClass(mdlCSSClass)
    }
    
    
    var enabled = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("enabled", "yes"))
    this._widget.setEnabled(enabled)
    var visible = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("visible", "yes"))
    this._widget.setVisible(visible)
    
    var tooltip = this.getMDLAttribute("tooltip", null)
    if (tooltip) {
      this._widget.setToolTip(tooltip)
    }
  },
  
  setup: function(parentControl) {
    if (this._mdlTree.getValue() && this._mdlTree.getValue().length > 0) {
      var f = this.field(this._mdlTree.getValue())
      if (f) { 
        this._field = f
        f.addListener(this)
      }
    }
    
    this._setupGUI()    
        
    var dependsOnExpression = this.getMDLAttribute("dependsOn", null)
    if (dependsOnExpression) {
      this.addFieldExpressionEvaluator(dependsOnExpression, "setEnabled")
    }
    var visibleOnExpression = this.getMDLAttribute("visibleOn", null)
    if (visibleOnExpression) {
      this.addFieldExpressionEvaluator(visibleOnExpression, "setVisible")
    }
    
    this._parent = parentControl
  },
  
  addFieldExpressionEvaluator: function(expression, slot) {
    var fieldExpressionEvaluator = new MLAB.Core.FieldExpressionEvaluator(expression, this.getModule())
    fieldExpressionEvaluator.connect("resultChanged", this, slot)
    // initially trigger the evaluator
    fieldExpressionEvaluator.fieldChanged()
    this._fieldExpressionEvaluators.push(fieldExpressionEvaluator)
  },
  
  appendChild: function(childControl) {
    this._children.push(childControl)
    this._widget.addWidget(childControl.getWidget())
  },
  
  // TODO: move to widget
  setupTypicalTags: function() { 
    var w = this.getMDLAttribute("w", null)
    if (w) { this._widget.getStyle().width = w + "px" }
    var h = this.getMDLAttribute("h", null)
    if (h) { this._widget.getStyle().height = h + "px" }
  },
  
  setupChildren: function() {
    try {
      for (var i=0; i<this._mdlTree.count(); i++) {
        var c = this.createSubControl(this._mdlTree.child(i))
        if (c) { this.setupChild(c) }
      }
    } catch(e) {
      this.logException(e)
    }
  },
  
  setupChild: function(child) {
    child.setup(this)
    child.setupTypicalTags()
    this.appendChild(child)
    child.handleAppendedToDOM()
    child.setupChildren()
  },
  
  handleAppendedToDOM: function() {
    // does nothing, can be reimplemented by sub controls
  },
  
  getMDLAttribute: function(attributeName, defaultValue) {
    return this._mdlTree.childValue(attributeName, defaultValue)
  },
  
  getMDLFieldAttribute: function(attributeName) {
    var field = null
    var fieldName = this.getMDLAttribute(attributeName, null)
    if (fieldName) {
      field = this.field(fieldName)
      if (!field) {
        this.logError("MLAB.GUI.WidgetControl.getMDLFieldAttribute: field not found: " + fieldName)
      }
    }
    return field
  },

  getMDLEnumAttribute: function(attributeName, enums, defaultValue) {
    var value = this.getMDLAttribute(attributeName, null)
    if (value !== null) {
      for (var i=0;i<enums.length;i++) {
        if (value.toLowerCase() === enums[i].toLowerCase()) {
          return enums[i]
        }
      }
      this.logError("MLAB.GUI.WidgetControl.getMDLEnumAttribute: unknown enum value: " + value)
    }
    return defaultValue
  },
  
  // only used if this control is used as a TabView item
  _tabEnabledChanged: function(enabled) {
    this.emit("tabEnabledChanged", this, enabled)
  },
  
  getType: function() {
    return this._mdlTree.getName()
  }
})


/** \class MLAB.GUI.FrameControl
 * 
 */
MLAB.GUI.deriveClass("FrameControl", MLAB.GUI.WidgetControl, {
  FrameControl: function(mdlTree, module) {
    MLAB.GUI.FrameControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    var w = MLAB.GUI.WidgetFactory.create("Table", id)
    w.setControl(this)
    return w
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.FrameControl.super.setupTypicalTags.call(this)
    
    var table = this.getWidget()
    
    var margin = this.getMDLAttribute("margin", "0")
    table.setMargin(margin)

    var width = this.getMDLAttribute("w", null)
    if (width !== null) {
      table.setWidth(width)
    } 
    var height = this.getMDLAttribute("h", null)
    if (height !== null) {
      table.setHeight(height)
    }
    
    var spacing = this.getMDLAttribute("spacing", "2")
    table.setSpacing(spacing)
  },
})


/** \class MLAB.GUI.HorizontalControl
 * 
 */
MLAB.GUI.deriveClass("HorizontalControl", MLAB.GUI.FrameControl, {
  HorizontalControl: function(mdlTree, module) {
    MLAB.GUI.HorizontalControl.super.constructor.call(this, mdlTree, module)
  },
  
  appendChild: function(childControl) {
    this._children.push(childControl)
    var alignX = this.getMDLAttribute("alignX", null)
    var alignY = this.getMDLAttribute("alignY", null)
    var w = null
    if (childControl.isFieldControl()) {
      var table = MLAB.GUI.WidgetFactory.create("Table")
      w = table
      var newRowIndex = table.rowCount()
      if (childControl.labelWidget() !== null) {
        table.addWidget(newRowIndex, 0, childControl.labelWidget(), alignX, alignY)
      }
      table.addWidget(newRowIndex, 1, childControl.getWidget(), alignX, alignY)
    } else {
      w = childControl.getWidget()
    }
    var table = this.getWidget()
    table.addWidget(0, table.columnCount(0), w, alignX, alignY)
  },
})


/** \class MLAB.GUI.FieldControl
 * 
 */
MLAB.GUI.deriveClass("FieldControl", MLAB.GUI.WidgetControl, {
  FieldControl: function(mdlTree, module) {
    this._lineEdit = null
    this._button  = null
    this._comboBox = null
    this._checkBox = null
    this._label = null
    this._numberEdit = null
    this._slider = null
    this._fieldChangeLocked = false
    MLAB.GUI.FieldControl.super.constructor.call(this, mdlTree, module)
  },
  
  isFieldControl: function() { return true },
  
  labelWidget: function() {
    return this._label 
  },
  
  createWidget: function(id) {
    var w = null
    if (this._field) {
      if      (this._field.isBoolField())    { w = this._setupBoolField() }
      else if (this._field.isColorField())   { w = this._setupColorField() }
      else if (this._field.isDoubleField())  { w = this._setupDoubleField() }
      else if (this._field.isEnumField())    { w = this._setupEnumField() }
      else if (this._field.isFloatField())   { w = this._setupFloatField() }
      else if (this._field.isIntegerField()) { w = this._setupIntegerField() }
      else if (this._field.isStringField())  { w = this._setupStringField() }
      else if (this._field.isTriggerField()) { w = this._setupTriggerField() }
      else if (this._field.isVectorField())  { w = this._setupVectorField() }
      else {
        w = this._setupStringField()
      }
    } else {
      this.logError("MLAB.GUI.FieldControl.setup(): no field has been specified")
    }
    
    if (w) {
      w.setControl(this)
    }
    
    return w
  },
  
  setupTypicalTags: function() {
    if (!this._field) { return }
    
      /*TODO: this is not correct, because w and h should be used not only for the field
      but also for the label.
      var w = this.getMDLAttribute("w", null)
      if (w) { this._fieldDOMElement.style.width = w + "px" }
      var h = this.getMDLAttribute("h", null)
      if (h) { this._fieldDOMElement.style.height = h + "px" }
    */

    // TODO: c++ MLABFieldControl uses MLABModule::translate() on the title, so maybe
    // the MDL from MeVisLab should pre-translate this? or add translated tag values in general,
    // e.g. translatedTitle? Or an rpc request could be used to let MeVisLab translate strings?
    var hasAutomaticTitle = false
    this._title = this.getMDLAttribute("title", null)
    if (this._title === null) { 
      this._title = this._getAutomaticFieldTitle(this._field.getName(), /*splitUppercase=*/true)
      hasAutomaticTitle = true
    }

    if (this._field.isTriggerField()) {
      this._button.setTitle(this._title)
    } else {
      var titleFieldName = this.getMDLAttribute("titleField", null)
      if (titleFieldName) {
        this._titleField = this.field(titleFieldName)
        if (this._titleField) {
          this._titleField.addListener(this)
          this._titleFieldChanged()
        } else {
          this.logError("MLAB.GUI.FieldControl.setupTypicalTags: the given title field " +
                         "is not found by the module context: " + titleFieldName)
        }
      }

      this._label = MLAB.GUI.WidgetFactory.create("Label")
      this._label.addStyleSheetClass("MLAB-GUI-FieldControlLabel")
      this._label.setTitle(this._title + (hasAutomaticTitle ? ":" : ""))
      
      var textAlign = this.getMDLAttribute("textAlign", null)
      if (textAlign) {
        this._label.setTextAlignment(textAlign)
      }
    }
  },
  
  handleAppendedToDOM: function() {
    this._isEditable = true
    this._editField = this.getMDLFieldAttribute("editField")
    if (this._editField) {
      this._editField.addListener(this)
      this._editFieldChanged()
    } else {
      this.setEditable(MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("edit", "yes")))
    }
  },
  
  _editFieldChanged: function() {
    this.setEditable(MLAB.Core.convertMDLValueToBool(this._editField.getValue()))
  },
  
  setEditable: function(editable) {
    if (this._isEditable !== editable) {
      this._isEditable = editable
      // TODO: this does not make sense for all widgets,
      // do this for line edits, button, etc. 
      // this._widget.setEditable(editable)
    }
  },
  
  _setupBoolField: function() {
    this._checkBox = MLAB.GUI.WidgetFactory.create("CheckBox")
    this._checkBox.setChecked(this._field.getValue())
    this._checkBox.connect("stateChange", this, "_checkboxChanged")
    this._checkBox.addStyleSheetClass("MLAB-GUI-FieldControlCheckBox")
    return this._checkBox
  },
  
  _checkboxChanged: function(checked) {
    this._setFieldValue(checked)
  },
  
  _boolFieldChanged: function(field) {
    this._checkBox.disconnect("stateChange", this, "_checkboxChanged")
    this._checkBox.setChecked(field.getValue())
    this._checkBox.connect("stateChange", this, "_checkboxChanged")
  },
   
  _setupEnumField: function() {
    this._enumAutoFormat = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("enumAutoFormat", "true"))

    this._comboBox = MLAB.GUI.WidgetFactory.create("ComboBox")
    this._comboBox.addStyleSheetClass("MLAB-GUI-FieldControlComboBox")
    
    var currentIndex = -1
    var enumItems = this._field.items()
    for (var i=0; i<enumItems.length; i++) {
      var item = enumItems[i]
      var title = item.value()
      if (this._enumAutoFormat || !item.hasAutoTitle()) {
        title = item.title()
      }
      this._comboBox.addItem(new MLAB.GUI.ComboBoxItem(title, item.value()))
      if (this._field.getValue() === item.value()) { currentIndex = i }
    }
    if (currentIndex >= 0) {
      this._comboBox.setCurrentIndex(currentIndex)
    }
    
    this._comboBox.connect("currentItemChanged", this, "_comboBoxChanged")
    return this._comboBox
  },
  
  _comboBoxChanged: function(enumItem) {
    if (enumItem !== null) {
      this._fieldChangedLocked = true      
      this._field.setCurrentItem(enumItem)
      this._fieldChangedLocked = false
    } else {
      this.logError("MLAB.GUI.FieldControl._comboBoxChanged(): no selected option found, field: " + this._field.getName())
    }
  },
  
  _setupStringField: function() {
    this._lineEdit = MLAB.GUI.WidgetFactory.create("LineEdit")
    this._lineEdit.setText(this._field.getValue())
    this._lineEdit.addStyleSheetClass("MLAB-GUI-FieldControlLineEdit")
    this._lineEdit.connect("returnPressed", this, "_lineEditReturnPressed")
    var updateFieldWhileEditing = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("updateFieldWhileEditing", "false"))
    this._lineEdit.setEmitTextChangedWhileEditing(updateFieldWhileEditing)
    var updateFieldWhileEditing = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("updateFieldWhileEditing", "false"))
    if (updateFieldWhileEditing) {
      this._lineEdit.connect("textChanged", this, "_lineEditTextChanged")
    }
    return this._lineEdit
  },
  
  _lineEditReturnPressed: function() {
    this._setFieldValue(this._lineEdit.text())
  },
  
  _lineEditTextChanged: function() {
    var text = this._lineEdit.text()
    if (this._field.getValue() !== text) {
      this._setFieldValue(text)
    }
  },

  _setupNumberField: function() {
    this._numberEdit = MLAB.GUI.WidgetFactory.create("NumberEdit")
    this._numberEdit.setValue(this._field.getValue())
    this._numberEdit.setRange(this._field.getMinValue(), this._field.getMaxValue())
    this._numberEdit.addStyleSheetClass("MLAB-GUI-FieldControlNumberEdit")
    var useSlider = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("slider", "false"))
    this._numberEdit.setSliderEnabled(useSlider)
    this._numberEdit.connect("returnPressed", this, "_numberEditReturnPressed")
    this._numberEdit.connect("valueChanged", this, "_numberEditValueChanged")
    
    var updateFieldWhileEditing = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("updateFieldWhileEditing", "false"))
    this._numberEdit.setEmitValueChangedWhileEditing(updateFieldWhileEditing)
    
    return this._numberEdit
  },
  
  _numberEditReturnPressed: function() {
    this._setFieldValue(this._numberEdit.getValue())
  },
  
  _numberEditValueChanged: function(value) {
    var v = value
    if (this._field.isFloatField()) {
      v = MLAB.Core.roundDoubleToFloat(value)
    }
    if (v !== this._field.getValue()) {
      this._setFieldValue(v)
    }
  },

  _numberFieldChanged: function(field) {
    this._numberEdit.disconnect("valueChanged", this, "_numberEditValueChanged")
    this._numberEdit.setValue(field.getValue())
    this._numberEdit.connect("valueChanged", this, "_numberEditValueChanged")
  },
  
  _setupDoubleField: function() {
    var numberEdit = this._setupNumberField()
    numberEdit.setIsFloatValue(true)
    return numberEdit
  },

  _setupFloatField: function() {
    var numberEdit = this._setupNumberField()
    numberEdit.setIsFloatValue(true)
    numberEdit.setUseDoublePrecision(false)
    return numberEdit
  },

  _setupIntegerField: function() {
    return this._setupNumberField()
  },
  
  _setupTriggerField: function() {
    this._button = MLAB.GUI.WidgetFactory.create("Button")
    this._button.connect("clicked", this, "_buttonClicked")
    return this._button
  },
  
  _buttonClicked: function() {
    this._field.touch() 
  },
  
  // by default, other field types are displayed as a string field
  _setupColorField: function() { 
    return this._setupStringField() 
   },
   
  _setupVectorField: function() {
    return this._setupStringField()
  },
  
  _titleFieldChanged: function() {
    var title = this._titleField.getValue()
    if (this._field.isTriggerField()) {
      this._button.setTitle(title)
    } else {
      this._label.setTitle(title)
    }
  },
  
  fieldChanged: function(field) {
    if (field === this._field) {
      if (!this._fieldChangeLocked) {
        if (field.isBoolField()) {
          this._boolFieldChanged(field)
        } else if (field.isEnumField()) {
          this._comboBox.setCurrentItem(this._field.getValue())
        } else if (field.isNumberField()) {
          this._numberFieldChanged(field)
        } else if (field.isStringField()) {
          this._lineEdit.setText(field.getValue())
        }
      }
    } else if (field === this._titleField) {
      this._titleFieldChanged()
    } else if (field === this._editField) {
      this._editFieldChanged()
    } else {
      this.logError("MLAB.GUI.FieldControl.fieldChanged: unexpected field: " + field.getName() + ":" + field.getType())
    }
  },
  
  _setFieldValue: function(value) {
    this._fieldChangeLocked = true
    this._field.setValue(value)
    this._fieldChangeLocked = false
  },
  
  setEnabled: function(enabled) {
    MLAB.GUI.FieldControl.super.setEnabled.call(this, enabled)
    if (this._label) {
      this._label.setEnabled(enabled)
    }
  },
  
  setVisible: function(visible) {
    MLAB.GUI.FieldControl.super.setVisible.call(this, visible)
    if (this._label) {
      this._label.setVisible(visible)
    }
  },
  
  // reimplementation of C++ function MLABUtils::getAutomaticFieldTitle()
  _getAutomaticFieldTitle: function(fieldName, splitUppercase) {
    if (fieldName.length === 0) { return fieldName }
    
    var i = fieldName.indexOf(".")
    if (i<0) { 
      i=0
    } else {
      i++
    }
    if (fieldName.length <= i) { return fieldName }
    
    var s = fieldName.charAt(i).toUpperCase()
    var lower = false
    for (++i; i<fieldName.length; i++) {
      var ref = fieldName.charAt(i)
      var isUpperCase = (ref === ref.toUpperCase())
      if (isUpperCase && lower) {
        s += ' '
      }
      lower = !isUpperCase
      if (ref === '_') {
        s += ' '
      } else {
        if (splitUppercase) {
          s += ref
        } else {
          s += ref.toLowerCase()
        }
      }
    }
    
    return s
  }

})


/** \class MLAB.GUI.LineEditControl
 * 
 */
MLAB.GUI.deriveClass("LineEditControl", MLAB.GUI.WidgetControl, {
  LineEditControl: function(mdlTree, module) {
    MLAB.GUI.LineEditControl.super.constructor.call(this, mdlTree, module)
  },
  
  setup: function(parentControl) {
    MLAB.GUI.LineEditControl.super.setup.call(this, parentControl)
  }
})


/** MLAB.GUI.ButtonControl
 * 
 */
MLAB.GUI.deriveClass("ButtonControl", MLAB.GUI.WidgetControl, {
  ButtonControl: function(mdlTree, module) {
    this._button = null
    MLAB.GUI.ButtonControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._button = MLAB.GUI.WidgetFactory.create("Button", id)
    this._button.setControl(this)
    return this._button
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.ButtonControl.super.setupTypicalTags.call(this)

    var imageTree = this._mdlTree.get("image")
    if (imageTree) {
      var imageUrl = MLAB.Core.translatePath(imageTree.getValue())
      this._button.setImageUrl(imageUrl)
    }
    
    var title = null
    var titleTree = this._mdlTree.get("title")
    if (titleTree) {
      title = titleTree.getValue()
    } else {
      title = this._field.getName()
    }
    
    if (title && title !== "") {
      this._button.setTitle(title)
    }
    
    var titleField = this.getMDLFieldAttribute("titleField")
    if (titleField) {
      titleField.addListener({fieldChanged: this.callback("_titleFieldChanged")})
      this._titleFieldChanged(titleField)
    }

    var commandTree = this._mdlTree.get("command")
    if (commandTree) {
      this._command = commandTree.getValue()
    } else {
      this._command = null
    }
    
    this._button.connect("clicked", this, "_onButtonClick")
  },
  
  _titleFieldChanged: function(field) {
    this._button.setTitle(field.getValue())
  },
  
  _onButtonClick: function() {
    if (this._command) {
      this.sendGenericRequest(this._command, [])
    }
    var field = this.getField()
    if (field) {
      field.touch()
    }
  },
})

/** \class MLAB.GUI.SliderControl
 * 
 */
MLAB.GUI.deriveClass("SliderControl", MLAB.GUI.WidgetControl, {
  SliderControl: function(mdlTree, module) {
    MLAB.GUI.SliderControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._slider = MLAB.GUI.WidgetFactory.create("Slider", id)
    return this._slider
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.SliderControl.super.setupTypicalTags.call(this)
    
    if (!this._field) {
      MLAB.Core.throwException("Slider control requires a field")
    }
    
    if (this._field.isFloatField() || this._field.isDoubleField()) {
      this._slider.setIsFloatValue(true)
    }
    
    this._slider.setValue(this._field.getValue())
    this._slider.setRange(this._field.getMinValue(), this._field.getMaxValue())
    
    this._slider.connect("valueChanged", this, "_sliderValueChanged")
    
    var updateFieldWhileEditing = MLAB.Core.convertMDLValueToBool(this.getMDLAttribute("updateFieldWhileEditing", "false"))
    this._slider.setEmitValueChangedWhileEditing(updateFieldWhileEditing)

    var title = this._mdlTree.childValue("title", null)
    
    if (title) {
      this._slider.setTitle(title)
    }
    
    this._command = this._mdlTree.childValue("command", null)
  },
  
  _sliderValueChanged: function() {
    this._field.setValue(this._slider.getValue())
  },
  
  fieldChanged: function() {
    this._slider.disconnect("valueChanged", this, "_sliderValueChanged")
    this._slider.setValue(this._field.getValue())
    this._slider.connect("valueChanged", this, "_sliderValueChanged")
  }
})


/** \class MLAB.GUI.TableControl
 * 
 */
MLAB.GUI.deriveClass("TableControl", MLAB.GUI.WidgetControl, {
  TableControl: function(mdlTree, module) {
    MLAB.GUI.TableControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._table = MLAB.GUI.WidgetFactory.create("Table", id)
    this._table.setControl(this)
    this._table.setMarkLastColumn(true)
    return this._table
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.TableControl.super.setupTypicalTags.call(this)
    
    for (var i=0; i<this._mdlTree.count(); i++) {
      var child = this._mdlTree.child(i)
      if (child.getName().toLowerCase() === "row") {
        this._addRow(child)
      }
    }
  },
  
  _addRow: function(tree) {
    this._table.addRow()
    try {
      for (var i=0; i<tree.count(); i++) {
        var c = this.createSubControl(tree.child(i))
        if (c) { this.setupChild(c) }
      }
    } catch(e) {
      this.logException(e)
    }
  },
  
  appendChild: function(childControl) {
    this._children.push(childControl)
    var alignX = this.getMDLAttribute("alignX", null)
    var alignY = this.getMDLAttribute("alignY", null)
    var rowIndex = this._table.rowCount()-1
    var columnIndex = this._table.columnCount(rowIndex)
    var widget = childControl.getWidget()
    if (childControl.isFieldControl() && (childControl.labelWidget() !== null)) {
      widget = MLAB.GUI.WidgetFactory.create("Table")
      widget.addWidget(0, 0, childControl.labelWidget())
      widget.addWidget(0, 1, childControl.getWidget())
    }
    this._table.addWidget(rowIndex, columnIndex, widget, alignX, alignY)
  },
})


/** \class MLAB.GUI.CheckBoxControl
 * 
 */
MLAB.GUI.deriveClass("CheckBoxControl", MLAB.GUI.WidgetControl, {
  CheckBoxControl: function(mdlTree, module) {
    MLAB.GUI.CheckBoxControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._checkBox = MLAB.GUI.WidgetFactory.create("CheckBox", id)
    this._checkBox.setControl(this)
    return this._checkBox
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.CheckBoxControl.super.setupTypicalTags.call(this)
        
    var title = this._mdlTree.childValue("title", this._field ? this._field.getName() : null)    
    if (title) {
      this._checkBox.setTitle(title)
    }

    this._command = this._mdlTree.childValue("command", null)
    
    if (this._field) {
      this._checkBox.setChecked(this._field.getValue())
    }
    this._checkBox.connect("stateChange", this, "_checkBoxChanged")
  },
  
  fieldChanged: function(field) {
    this._checkBox.disconnect("stateChange", this, "_checkBoxChanged")
    this._checkBox.setChecked(field.getValue())
    this._checkBox.connect("stateChange", this, "_checkBoxChanged")
  },

  _checkBoxChanged: function(checked) {
    if (this._command) {
      this.sendGenericRequest(this._command, [])
    }  
    var field = this.getField()
    if (field) {
      field.setValue(checked);
    }
  },  
})


/** \class MLAB.GUI.ComboBoxControl
 * 
 */
MLAB.GUI.deriveClass("ComboBoxControl", MLAB.GUI.WidgetControl, {
  ComboBoxControl: function(mdlTree, module) {
    MLAB.GUI.ComboBoxControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._comboBox = MLAB.GUI.WidgetFactory.create("ComboBox", id)
    this._comboBox.setControl(this)
    return this._comboBox
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.ComboBoxControl.super.setupTypicalTags.call(this)
    
    this._activatedCommand = this._mdlTree.childValue("activatedCommand", null)
    this._comboBox.connect("currentItemChanged", this, "_currentItemChanged")
    
    var useItems = false
    
    var comboFieldName = this._mdlTree.childValue("comboField", null)
    if (comboFieldName) {
      this._comboSeparator = this._mdlTree.childValue("comboSeparator", ",")
      this._comboField = this.field(comboFieldName)
      if (this._comboField !== null) {
        this._comboField.addListener(this)
        this.fieldChanged(this._comboField)
      } else {
        this.logError("comboField not found: " + comboFieldName)
      }
    } else {
      useItems = true
    }
    
    if (useItems) {
      var items = []
      if (this._field && this._field.isEnumField()) {
        var enumItems = this._field.items()
        // TODO: enum field support on combo boxes is not really implemented in c++, so
        // we also an MDL tag here that controls the enum item title policy: stripEnumItemPrefix
        this._enumAutoFormat = true
        for (var i=0; i<enumItems.length; i++) {
          var item = enumItems[i]
          var title = item.value()
          if (this._enumAutoFormat || !item.hasAutoTitle()) {
            title = item.title()
          }
          items.push(new MLAB.GUI.ComboBoxItem(title, value))
        }
      } else {
        var itemsTree = this._mdlTree.get("items")
        if (itemsTree) {
          for (var i=0; i<itemsTree.count(); i++) {
            var child = itemsTree.child(i)
            var value = child.getValue()
            var title = child.childValue("title", value)
            items.push(new MLAB.GUI.ComboBoxItem(title, value))
          }
        } else {
          this.logError("MLAB.GUI.ComboBoxControl: no comboField nor combobox items given")
        }
      }
      
      if (items.length) {
        this._setupItems(items)
      }
    }

    if (this._field) {
      this.fieldChanged(this._field)
    }
  },
  
  _setupItems: function(items) {
    this._comboBox.clearItems()
    for (var i=0; i<items.length; i++) {
      this._comboBox.addItem(items[i])
    }
  },
  
  fieldChanged: function(field) {
    var value = field.getValue()
    if (typeof(value) !== 'undefined') {
      if (field === this._comboField) {
        var items = value.split(this._comboSeparator)
        this._setupItems(items)
      } else if (field === this._field) {
        this._comboBox.setCurrentItem(value)
      }
    }
  },
  
  _currentItemChanged: function(event) {
    var item = this._comboBox.currentItem()
    if (item) {
      if (this._field) {
        this._field.setValue(item)
      }
      if (this._activatedCommand) {
        this.sendGenericRequest(this._activatedCommand, [item])
      }
    }
  },
})


/** \class MLAB.GUI.LabelControl
 * 
 */
MLAB.GUI.deriveClass("LabelControl", MLAB.GUI.WidgetControl, {
  LabelControl: function(mdlTree, module) {
    this._label = null
    MLAB.GUI.LabelControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._label = MLAB.GUI.WidgetFactory.create("Label", id)
    this._label.setControl(this)
    return this._label
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.LabelControl.super.setupTypicalTags.call(this)
    
    var title = this.getMDLAttribute("title", null)
    if (title) {
      this._label.setTitle(title)
    }
    
    var titleFieldName = this._mdlTree.childValue("titleField", null)
    if (titleFieldName) {
      this._titleField = this.field(titleFieldName)
      if (this._titleField !== null) {
        this._titleField.addListener(this)
        this.fieldChanged(this._titleField)
      } else {
        this.logError("titleField not found: " + titleFieldName)
      }
    }
    
    var imagePath = this.getMDLAttribute("image", null)
    if (imagePath) {
      this._label.setImageUrl(MLAB.Core.translatePath(imagePath))
    }
  },
  
  fieldChanged: function(field) {
    this._label.setTitle(field.stringValue())
  }
})


/** \class MLAB.GUI.SplitterControl
 * 
 */
MLAB.GUI.deriveClass("SplitterControl", MLAB.GUI.WidgetControl, {
  SplitterControl: function(mdlTree, module) {
    MLAB.GUI.SplitterControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._splitter = MLAB.GUI.WidgetFactory.create("Splitter", id)
    this._splitter.setControl(this)
    return this._splitter
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.SplitterControl.super.setupTypicalTags.call(this)
    
    var d = this.getMDLAttribute("direction", "horizontal")    
    if (d === "vertical") {
      d = MLAB.GUI.VERTICAL
    } else {
      d = MLAB.GUI.HORIZONTAL
    }
    this._splitter.setDirection(d)
  },
})


/** \class MLAB.GUI.HyperTextControl
 * 
 */
MLAB.GUI.deriveClass("HyperTextControl", MLAB.GUI.WidgetControl, {
  HyperTextControl: function(mdlTree, module) {
    MLAB.GUI.HyperTextControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._hyperText = MLAB.GUI.WidgetFactory.create("HyperText", id)
    this._hyperText.setControl(this)
    return this._hyperText
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.HyperTextControl.super.setupTypicalTags.call(this)
    
    var text = this.getMDLAttribute("text", null)
    if (text) {
      this.setText(text)
    }
  },
  
  setText: function(text) {
    this._hyperText.setText(text)
  },
  
  appendText: function(text) {
    this._hyperText.appendText(text)
  },
})

/** \class MLAB.GUI.BoxControl
 * 
 */
MLAB.GUI.deriveClass("BoxControl", MLAB.GUI.WidgetControl, {
  BoxControl: function(mdlTree, module) {
    this._layoutControl = null
    this._layout = null
    MLAB.GUI.BoxControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._box = MLAB.GUI.WidgetFactory.create("Box", id)
    this._box.setControl(this)
    return this._box
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.BoxControl.super.setupTypicalTags.call(this)
    
    this._layout = this.getMDLAttribute("layout", "Vertical")
    var title = this.getMDLAttribute("title", null)
    if (!title) {
      title = this._mdlTree.getValue()
    }
    if (title && title.length > 0) {
      this._box.setTitle(title)
    }
    var titleField = this.getMDLFieldAttribute("titleField")
    if (titleField) {
      titleField.addListener({fieldChanged: this.callback("_titleFieldChanged")})
      this._titleFieldChanged(titleField)
    }
  },
  
  // overwrite setupChildren() to set the minimum size for the first column
  setupChildren: function() {
    var layoutTree = new MLAB.Core.Tree({name: this._layout, value: ""})
    this._layoutControl = MLAB.GUI.WidgetControlFactory.createControl(layoutTree, this.getModule())
    MLAB.GUI.BoxControl.super.setupChild.call(this, this._layoutControl)
    MLAB.GUI.BoxControl.super.setupChildren.call(this)
  },
  
  setupChild: function(childControl) {
    this._layoutControl.setupChild(childControl)
  },
  
  _titleFieldChanged: function(field) {
    this._box.setTitle(field.getValue())
  },
})


/** \class MLAB.GUI.ProgressBarControl
 * 
 */
MLAB.GUI.deriveClass("ProgressBarControl", MLAB.GUI.WidgetControl, {
  ProgressBarControl: function(mdlTree, module) {
    MLAB.GUI.ProgressBarControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._progressbar = MLAB.GUI.WidgetFactory.create("ProgressBar", id)
    this._progressbar.setControl(this)
    return this._progressbar
  },
  
  fieldChanged: function(field) {
    this._progressbar.setProgress(field.stringValue())
  }
})


/** \class MLAB.GUI.SeparatorControl
 * 
 */
MLAB.GUI.deriveClass("SeparatorControl", MLAB.GUI.WidgetControl, {
  SeparatorControl: function(mdlTree, module) {
    this._layout = null
    MLAB.GUI.SeparatorControl.super.constructor.call(this, mdlTree, module)
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.BoxControl.super.setupTypicalTags.call(this)
    
    var d = this.getMDLAttribute("direction", "horizontal")
    if (d === "vertical") {
      d = MLAB.GUI.VERTICAL
    } else {
      d = MLAB.GUI.HORIZONTAL
    }
    this._seperator.setDirection(d)
  },
  
  createWidget: function(id) {
    this._seperator = MLAB.GUI.WidgetFactory.create("Separator", id)
    this._seperator.setControl(this)
    return this._seperator
  },
})


/** \class MLAB.GUI.VerticalControl
 * 
 */
MLAB.GUI.deriveClass("VerticalControl", MLAB.GUI.FrameControl, {
  VerticalControl: function(mdlTree, module) {
    MLAB.GUI.VerticalControl.super.constructor.call(this, mdlTree, module)
  },
  
  // overwrite setupChildren() to set the minimum size for the first column
  setupChildren: function() {
    MLAB.GUI.VerticalControl.super.setupChildren.call(this)
    var table = this.getWidget()
    table.resizeFirstColumnToMinimumWidth()
  },
  
  appendChild: function(childControl) {
    this._children.push(childControl)
    var alignX = this.getMDLAttribute("alignX", null)
    var alignY = this.getMDLAttribute("alignY", null)
    var table = this.getWidget()
    if (childControl.isFieldControl()) {
      var newRowIndex = table.rowCount()
      if (childControl.labelWidget() !== null) {
        table.addWidget(newRowIndex, 0, childControl.labelWidget(), alignX, alignY)
      }
      table.addWidget(newRowIndex, 1, childControl.getWidget(), alignX, alignY)      
    } else {
      var columnSpan = 2
      table.addWidget(table.rowCount(), 0, childControl.getWidget(), alignX, alignY, columnSpan)
    }
  },
})


/** \class MLAB.GUI.CategoryControl
 * 
 */
MLAB.GUI.deriveClass("CategoryControl", MLAB.GUI.VerticalControl, {
  CategoryControl: function(mdlTree, module) {
    MLAB.GUI.CategoryControl.super.constructor.call(this, mdlTree, module)
  },
})

/** \class MLAB.GUI.TabViewControl
 * 
 */
MLAB.GUI.deriveClass("TabViewControl", MLAB.GUI.WidgetControl, {
  TabViewControl: function(mdlTree, module) {
    this._tabView = null
    MLAB.GUI.TabViewControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    var mode = this.getMDLEnumAttribute("mode", ["invisible", "top"], "top")
    this._tabView = MLAB.GUI.WidgetFactory.create("TabView", null, mode)
    return this._tabView
  },

  setupTypicalTags: function() { 
    MLAB.GUI.TabViewControl.super.setupTypicalTags.call(this)
    this._field = this.getMDLFieldAttribute("currentIndexField")
    if (this._field) {
      this._field.addListener(this)
    }
  },
  
  setupChildren: function() {
    MLAB.GUI.TabViewControl.super.setupChildren.call(this)
    this.fieldChanged()
    if (this._tabView._tabBar) {
      this._tabView._tabBar.connect("currentTabChanged", this, "_activeTabChanged")
    }
  },
  
  setupChild: function(childControl) {
    MLAB.GUI.TabViewControl.super.setupChild.call(this, childControl)
    var dependsOnExpression = childControl.getMDLAttribute("tabDependsOn", null)
    if (dependsOnExpression) {
      childControl.addFieldExpressionEvaluator(dependsOnExpression, "_tabEnabledChanged")
    }
    childControl.connect("tabEnabledChanged", this, "_tabEnabledChanged")
    var tabTitle = childControl.getMDLAttribute("tabTitle", null)
    if (tabTitle !== null) {
      this._tabView.setTabTitle(this._tabView.tabCount()-1, tabTitle)
    }
  },

  fieldChanged: function() {
    if (this._field.isIntegerField()) {
      this._tabView.setActiveTab(this._field.getValue())
    }
  },
  
  _activeTabChanged: function(index) {
    if (this._field && this._field.isIntegerField()) {
      if (index !== this._field.getValue()) {
        this._field.setValue(index)
      }
    }
  },
  
  _tabEnabledChanged: function(tabViewItem, enabled) {
    console.log(tabViewItem + " is enabled ? " + enabled)
    this._tabView.setTabEnabled(tabViewItem.getWidget(), enabled)
  },
})


/** \class MLAB.GUI.TabViewItemControl
 * 
 */
MLAB.GUI.deriveClass("TabViewItemControl", MLAB.GUI.VerticalControl, {
  TabViewItemControl: function(mdlTree, module) {
    this._tabViewItem = null
    MLAB.GUI.TabViewItemControl.super.constructor.call(this, mdlTree, module)
  },
  
  createWidget: function(id) {
    this._tabViewItem = MLAB.GUI.WidgetFactory.create("TabViewItem")
    return this._tabViewItem
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.TabViewItemControl.super.setupTypicalTags.call(this)
    
    var title = this._mdlTree.getValue()
    this._tabViewItem.setTitle(title)
  },
})


/** \class MLAB.GUI.WindowControl
 * 
 */
MLAB.GUI.deriveClass("WindowControl", MLAB.GUI.WidgetControl, {
  WindowControl: function(mdlTree, module) {
    MLAB.GUI.WindowControl.super.constructor.call(this, mdlTree, module)
    this._windowName = mdlTree.getValue()
    if (!this._windowName || this._windowName.length === 0) { 
      this._windowName = "_default" 
    }
  },

  getWindowName: function() { 
    return this._windowName 
  },
  
  createWidget: function(id) {
    var w = MLAB.GUI.WidgetFactory.create("Window", id)
    w.setControl(this)
    return w
  },
  
  appendToDOM: function(domParent) {
    this._widget.appendToDOM(domParent)
    this.setupChildren()
    this.setupFinished()
  },
  
  // Can be overriden by framework implementation to issue commands after window is build in html
  setupFinished: function() {    
  }
})

/** \class MLAB.GUI.PanelControl
 * 
 */
MLAB.GUI.deriveClass("PanelControl", MLAB.GUI.WidgetControl, {
  PanelControl: function(mdlTree, module) {
    MLAB.GUI.PanelControl.super.constructor.call(this, mdlTree, module)
    
    this._panelName = null
    this._windowName = null
  },

  setWindowName: function(name) { 
    this._windowName = name 
  },
  getWindowName: function() { 
    return this._windowName 
  },
  
  setupTypicalTags: function() {
    MLAB.GUI.PanelControl.super.setupTypicalTags.call(this)
    this._panelName = this._mdlTree.childValue("panel")
  },
  
  setupChildren: function() {
    var panelTree = null
    if (this._panelName) {
      // the dummy tree is only used for the loop below
      panelTree = new MLAB.Core.Tree({name: "dummy", value: "", children: []}) 
      var internalTree = this._getPanelTree(this._panelName, this._module.getMDLTree())
      if (internalTree !== null) {
        panelTree.append(internalTree)
        this._windowName = panelTree.childValue("panelName")
      } else {
        this.logError("No such panel found: " + this._panelName)
      }
    } else {
      // no panelName is given, assume the given tree is already the panel tree.
      // This is the case when MLABWidgetController.createPanel() creates this control.
      panelTree = this._mdlTree
    }
    try {
      for (var i=0; i<panelTree.count(); i++) {
        var c = this.createSubControl(panelTree.child(i))
        if (c) { this.setupChild(c) }
      }
      //this._enabledChanged()
    } catch(e) {
      this.logException(e)
    }
  },
  
  _getPanelTree: function(panelName, mdlTree) {
    var panelTree = null
    for (var i=0; i<mdlTree.count(); i++) {
      var child = mdlTree.child(i)
      if (child.childValue("panelName") === panelName) {
        panelTree = child
        break
      }
    }
    if (!panelTree) {
      for (var i=0; i<mdlTree.count(); i++) {
        panelTree = this._getPanelTree(panelName, mdlTree.child(i))
        if (panelTree) { break }
      }
    }
    return panelTree
  },
  
  createWidget: function(id) {
    var w = MLAB.GUI.WidgetFactory.create("Panel", id)
    w.setControl(this)
    return w
  },
  
  /**
   * Called when this panel is top level, otherwise setupChildren() and setupFinished()
   * are called from MLAB.GUI.WidgetControl.
   */
  appendToDOM: function(domParent) {
    // we are a top level panel, otherwise appendToDOM() would not be called.
    
    //Set the window name,
    // because the window controller will use it to look this panel up.
    //this._windowName = this._mdlTree.getValue()
    //if (!this._windowName || this._windowName.length === 0) { this._windowName = "_default" }
    this._widget.appendToDOM(domParent) 
    this.setupChildren()
    this.setupFinished()
  },

  // Can be overriden by to issue commands after window is build in html
  setupFinished: function() { 
    
  }
})


MLAB.GUI.WidgetControlFactory.registerWidgetControl("Box", MLAB.GUI.BoxControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Button", MLAB.GUI.ButtonControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Category", MLAB.GUI.CategoryControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("CheckBox", MLAB.GUI.CheckBoxControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("ComboBox", MLAB.GUI.ComboBoxControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Horizontal", MLAB.GUI.HorizontalControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("HyperText", MLAB.GUI.HyperTextControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Field", MLAB.GUI.FieldControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Label", MLAB.GUI.LabelControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("LineEdit", MLAB.GUI.LineEditControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Panel", MLAB.GUI.PanelControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("ProgressBar", MLAB.GUI.ProgressBarControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Separator", MLAB.GUI.SeparatorControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Slider", MLAB.GUI.SliderControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Splitter", MLAB.GUI.SplitterControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Table", MLAB.GUI.TableControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("TabView", MLAB.GUI.TabViewControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("TabViewItem", MLAB.GUI.TabViewItemControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Vertical", MLAB.GUI.VerticalControl)
MLAB.GUI.WidgetControlFactory.registerWidgetControl("Window", MLAB.GUI.WindowControl)
