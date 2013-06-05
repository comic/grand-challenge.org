
/** \class MLAB.GUI.Widget
 * 
 * 
 * TODO: the widget should know nothing about the control, it should be only
 * stored to be accessible in other code!!! 
 * @param control
 */
MLAB.GUI.deriveClass("Widget", MLAB.Core.Object, {
  Widget: function() {
    MLAB.GUI.Widget.super.constructor.call(this)
    this._domElement = null
    this._control = null
    this._children = []
    this._isVisibleToParent = true
    this._isEnabledToParent = true
    this._parentWidget = null
    
    // stores the style.display value of the DOM element when it is hidden,
    // so that it can be restored when it is shown again
    this._storedDisplayValue = null
    
    this._createDOMElement()
  },
  
  logError: function(message) {
    this._control.logError(message)
  },
  
  isActive: function() {
    return document.activeElement === this._domElement
  },
  
  removeFromParentWidget: function() {
    if (this._parentWidget !== null) {
      this._parentWidget._children.remove(this)
      this._parentWidget = null
    }
  },
  
  _setParentWidget: function(widget) {
    if (this._parentWidget !== null) {
      MLAB.Core.throwException("The parent widget is already set, a widget cannot have more than one parent.")
    }
    this._parentWidget = widget
  },
  
  parentWidget: function() {
    return this._parentWidget
  },
  
  labelWidget: function() {
    return null
  },
  
  setTextAlignment: function(alignment) {
    this._domElement.style.textAlign = alignment.toLowerCase()
  },
  
  setControl: function(control) {
    this._control = control
  },
  
  setId: function(id) {
    this._domElement.setAttribute("id", id)
  },
  
  _createDOMElement: function() {
    this._setDOMElement(document.createElement('div'))
  },
  
  _setDOMElement: function(domElement) {
    this._domElement = domElement
    this._domElement.widget = this
  },
  
  hide: function() {
    this.setVisible(false)
  },
  
  show: function() {
    this.setVisible(true)
  },
  
  setMargin: function(margin) {
    this._domElement.style.margin = margin + "px"
  },
  
  setWidth: function(width) {
    this._domElement.style.width = width + "px"
  },
  
  setHeight: function(height) {
    this._domElement.style.height = height + "px"
  },
  
  _childVisibilityChanged: function(childWidget, visible) {
    // can be reimplemented in a sub class
  },
  
  onShow: function() {
    // onShow is propagated when the widget all its parents got really visible
    // can be reimplemented in a sub class
  },
  
  _propagateOnShow: function() {
    this.onShow()
    for (var i=0; i<this._children.length; i++) {
      this._children[i]._propagateOnShow()
    }
  },
  
  setVisible: function(visible) {
    if (this._isVisibleToParent != visible) {
      this._isVisibleToParent = visible
      if (this._parentWidget) {
        this._parentWidget._childVisibilityChanged(this, visible)
      }
      // show the DOM elements only if the parent is visible
      if (!visible || this._parentWidget === null || this._parentWidget.isVisible()) {
        this._setDOMElementVisible(visible)
        this._propagateOnShow()
      }
    }
  },
  
  _setDOMElementVisible: function(visible) {
    // first show/hide the children to avoid flickering
    if (!visible || this._isVisibleToParent) {
      // show/hide the DOM elements of the child widgets
      for (var i=0; i<this._children.length; i++) {
        this._children[i]._setDOMElementVisible(visible)
      }
      MLAB.GUI.setDOMElementVisible(this._getDOMElement(), visible)
    }
  },
  
  /** \fn MLAB.GUI.Widget.isVisible
   * 
   * Returns if the widget is visible. It may return false
   * even if isVisibleToParent() returns true, because the parent may be invisible.  
   */
  isVisible: function() {
    return this._isVisibleToParent && (this._parentWidget === null || this._parentWidget.isVisible())
  },
  
  isVisibleToParent: function() {
    return this._isVisibleToParent
  },
  
  setEnabled: function(enabled) {
    if (this._isEnabledToParent != enabled) {
      this._isEnabledToParent = enabled
      // enable the DOM elements only if the parent is enabled
      if (!enabled || this._parentWidget === null || this._parentWidget.isEnabled()) {
        this._setDOMElementEnabled(enabled)
      }
    }
  },
  
  _setDOMElementEnabled: function(enabled) {
    if (!enabled || this._isEnabledToParent) {
      MLAB.GUI.setDOMElementEnabled(this._getDOMElement(), enabled)
      // enable/disable the DOM elements of the child widgets
      for (var i=0; i<this._children.length; i++) {
        this._children[i]._setDOMElementEnabled(enabled)
      }
    }
  },
  
  _isDOMElementEnabled: function() {
    return MLAB.GUI.isDOMElementEnabled(this._domElement)
  },
  
  /** \fn MLAB.GUI.Widget.isEnabled
   * 
   * Returns if the widget is enabled. It may return false
   * even if isEnabledToParent() returns true, because the parent may be disabled.  
   */
  isEnabled: function() {
    return this._isEnabledToParent && (this._parentWidget === null || this._parentWidget.isEnabled())
  },
  
  isEnabledToParent: function() {
    return this._isEnabledToParent
  },
  
  addStyleSheetClass: function(styleSheetClass) {
    MLAB.GUI.addStyleSheetClass(this._domElement, styleSheetClass)
  },
  
  removeStyleSheetClass: function(styleSheetClass) {
    MLAB.GUI.removeStyleSheetClass(this._domElement, styleSheetClass)
  },

  getControl: function() { return this._control },
  getStyle: function() { return this._domElement.style },
  // TODO: remove this function
  appendChild: function(child) {
    //console.error("WRONG APPEND CHILD CALLED")
    this._domElement.appendChild(child) 
  },
  
  addWidget: function(widget) {
    this._addWidgetToDOM(widget)
    this._handleWidgetAdded(widget)
  },
  
  _handleWidgetAdded: function(widget) {
    this._children.push(widget)
    // hide the child widget if this widget is hidden
    if (!this.isVisible()) {
      widget._setDOMElementVisible(false)
    }
    // disable the child widget if this widget is disabled
    if (!this.isEnabled()) {
      widget._setDOMElementEnabled(false)
    }
    this._childVisibilityChanged(widget, widget.isVisibleToParent())
  },
  
  _addWidgetToDOM: function(widget) {
    widget._setParentWidget(this)
    widget.appendToDOM(this._domElement)
  },
  
  removeWidget: function(widget) {
    this._children.remove(widget)
    widget._setParentWidget(null)
    this._removeWidgetFromDOM(widget)
  },
  
  _removeWidgetFromDOM: function(widget) {
    widget.removeFromDOM(this._domElement)
  },
  
  // promoted as public function, since it is a typical use-case to access the DOM element
  getDOMElement: function() { return this._domElement },
  _getDOMElement: function() { return this._domElement },
  
  appendToDOM: function(domParent) { 
    domParent.appendChild(this._domElement)
    // call onShow() initially, if we are visible 
    if (this.isVisible()) {
      this.onShow()
    }
  },
  
  removeFromDOM: function(domParent) { domParent.removeChild(this._domElement) },
  
  getGlobalPosition: function() { return MLAB.GUI.getGlobalPosition(this._domElement) },
  
  setToolTip: function(tooltip) {
    this._domElement.setAttribute("title", tooltip)
  },
})  


/** \class MLAB.GUI.Box
 * 
 */
MLAB.GUI.deriveClass("Box", MLAB.GUI.Widget, {
  Box: function() { 
    this._titleLabel = null
    MLAB.GUI.Box.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    this._setDOMElement(div)
    this._label = MLAB.GUI.WidgetFactory.create("Label")
    this._label.addStyleSheetClass("MLAB-GUI-BoxTitleLabel")
    this._label.setVisible(false)
    this.addWidget(this._label)
  },
  
  setTitle: function(title) {
    this._label.setVisible(true)
    this._label.setTitle(title)
  },
})


/** \class MLAB.GUI.HyperText
 * 
 */
MLAB.GUI.deriveClass("HyperText", MLAB.GUI.Widget, {
  HyperText: function() { 
    MLAB.GUI.HyperText.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    this._contentDiv = document.createElement("div")
    MLAB.GUI.addStyleSheetClass(this._contentDiv, "MLAB-GUI-HyperTextContent")
    var div = document.createElement("div")
    div.appendChild(this._contentDiv)
    this._setDOMElement(div)
  },
  
  setText: function(text) {
    this._contentDiv.innerHTML = text
  },
  
  appendText: function(text) {
    this._contentDiv.innerHTML += text
  },
})


/** \class MLAB.GUI.LineEdit
 * 
 */
MLAB.GUI.deriveClass("LineEdit", MLAB.GUI.Widget, {
  LineEdit: function() { 
    MLAB.GUI.LineEdit.super.constructor.call(this)
    this.registerSignal("returnPressed")
    this.registerSignal("textChanged")
    this._emitTextChangedTimer = null
    this._emitTextChangedWhileEditing = false
  },
  
  // TODO: to make the line edit readonly use the readonly attribute (similar to disabled)
  
  setEmitTextChangedWhileEditing: function(flag) {
    this._emitTextChangedWhileEditing = flag
  },
  
  _createDOMElement: function() {
    var input = document.createElement("input")
    input.onkeydown = this.callback("_handleInputKeyDown")
    input.onchange = this.callback("_emitTextChangedDelayed")
    this._setDOMElement(input)
  },
  
  _handleInputKeyDown: function(event) {
    if (event.keyCode === MLAB.Core.KeyEvent.DOM_VK_RETURN) {
      this.emit("returnPressed")
    } else if (this._emitTextChangedWhileEditing && !MLAB.Core.isTextlessKeyCode(event.keyCode)) {
      this._emitTextChangedDelayed()
    }
  },
  
  text: function() {
    var input = this._getDOMElement()
    return input.value
  },
  
  setText: function(text) {
    var input = this._getDOMElement()
    input.value = text
    this.emit("textChanged", input.value)
  },
  
  _emitTextChangedDelayed: function() {
    if (this._emitTextChangedTimer !== null) {
      window.clearTimeout(this._emitTextChangedTimer)
    }
    this._emitTextChangedTimer = window.setTimeout(this.callback("_emitTextChanged"), 350)
  },
    
  _emitTextChanged: function() {
    var input = this._getDOMElement()
    this.emit("textChanged", input.value)
  }
})

/** \class MLAB.GUI.Slider
 * 
 */
MLAB.GUI.deriveClass("Slider", MLAB.GUI.Widget, {
  Slider: function() {
    MLAB.GUI.Slider.super.constructor.call(this)
    this._minimumValue = 0
    this._maximumValue = Number.MAX_VALUE
    this._value = 0
    this._emitValueChangedWhileEditing = false
    this.registerSignal("valueChanged")
  },
  
  setEmitValueChangedWhileEditing: function(flag) {
    this._emitValueChangedWhileEditing = flag
  },
  
  setRange: function(min, max) {
    this._minimumValue = min
    this._maximumValue = max
  },
  
  setValue: function(value) {
    if (isNaN(value)) {
      MLAB.Core.throwException("Attempt to set the value to NaN.")
    }
    this._updateValue(Math.min(Math.max(value, this._minimumValue), this._maximumValue))
  },
  
  _updateValue: function(value) {
    this._value = value
    this._emitValueChanged()
  },
  
  _emitValueChanged: function() {
    this.emit("valueChanged", this._value)
  },
  
  getValue: function() {
    return this._value
  },
  
})

/** \class MLAB.GUI.NumberValidator
 * 
 */
MLAB.GUI.defineClass("NumberValidator", {
  NumberValidator: function() {
    // note that Number.MIN_VALUE is the smallest positive number closest to 0
    this._minValue = -Number.MAX_VALUE
    this._maxValue = Number.MAX_VALUE
  },
  
  minimumValue: function() { return this._minValue },
  maximumValue: function() { return this._maxValue },
  
  setAllowedRange: function(min, max) {
    this._minValue = min
    this._maxValue = max
  },
  
  validate: function(value) {
    var isValid = false
    if (value >= this._minValue && value <= this._maxValue) {
      isValid = true
    }
    return isValid
  },
})

/** \class MLAB.GUI.NumberEdit
 * 
 */
MLAB.GUI.deriveClass("NumberEdit", MLAB.GUI.Widget, {
  NumberEdit: function() {
    this._emitValueChangedTimer = null
    this._slider = null
    this._input = null
    this._value = 0
    this._emitValueChangedWhileEditing = false
    this._updateValueTimer = false
    this._isFloatValue = false
    this._useDoublePrecision = true
    this._validator = new MLAB.GUI.NumberValidator()
    this._validator.setAllowedRange(0, Number.MAX_VALUE)
    MLAB.GUI.NumberEdit.super.constructor.call(this)
    this.registerSignal("valueChanged")
    this.registerSignal("returnPressed")
  },
  
  setValidator: function(validator) {
    if (!("validate" in validator)) {
      MLAB.Core.throwException("NumberEdit.setValidator: the object has no validate() function.")
    }
    this._validator = validator
  },
  
  setUseDoublePrecision: function(flag) {
    this._useDoublePrecision = flag
    this._updateInputFromValue()
  },
  
  // TODO: 
  //       - deny inserting anything else than numbers and '.'
  
  setIsFloatValue: function(flag) {
    this._isFloatValue = flag
    if (this._slider) {
      this._slider.setIsFloatValue(flag)
    }
  },
  
  setEmitValueChangedWhileEditing: function(flag) {
    this._emitValueChangedWhileEditing = flag
    if (this._slider) {
      this._slider.setEmitValueChangedWhileEditing(flag)
    }
  },
  
  setRange: function(minimumValue, maximumValue) {
    this._validator.setAllowedRange(minimumValue, maximumValue)
    if (this._slider) {
      this._slider.setRange(this._validator.minimumValue(), this._validator.maximumValue())
    }
  },

  _createDOMElement: function() {
    this._input = document.createElement("input")
    this._input.onblur = this.callback("_handleFocusOut")
    this._input.onkeyup = this.callback("_handleInputKeyUp")
    this._input.onkeydown = this.callback("_handleInputKeyDown")
    this._input.onchange = this.callback("_emitValueChangedDelayed")
    
    var div = document.createElement("div")
    div.appendChild(this._input)
    this._setDOMElement(div)
  },
  
  setSliderEnabled: function(enabled) {
    if (enabled) {
      if (!this._slider) {
        this._slider = MLAB.GUI.WidgetFactory.create("Slider")
        this._slider.setRange(this._validator.minimumValue(), this._validator.maximumValue())
        this._slider.setEmitValueChangedWhileEditing(this._emitValueChangedWhileEditing)
        this._slider.addStyleSheetClass("MLAB-GUI-NumberEditSlider")
        this._slider.connect("valueChanged", this, "_sliderValueChanged")
        this._slider.setIsFloatValue(this._isFloatValue)
        this.addWidget(this._slider)
      }
    } else {
      if (this._slider) {
        this.removeWidget(this._slider)
        this._slider = null
      }
    }
  },
  
  _sliderValueChanged: function(value) {
    this._value = value
    this._updateInputFromValue()
    this._emitValueChanged()
  },
  
  _handleFocusOut: function(event) {
    if (!this._updateValue()) {
      this._input.value = this._value
    }
  },
  
  _handleInputKeyUp: function(event) {
    if (event.keyCode === MLAB.Core.KeyEvent.DOM_VK_ESCAPE) {
      // escape restores the original value. Note that this does not work when
      // the value is updated while editing
      // BUG: pressing escape down causes the web socket connection to be closed in firefox, but
      // it will hopefully be fixed soon: https://bugzilla.mozilla.org/show_bug.cgi?id=614304 
      event.preventDefault()
      this._input.value = this._value
    } else if (!MLAB.Core.isTextlessKeyCode(event.keyCode)) {
      if (this._emitValueChangedWhileEditing) {
        if (this._updateValue()) {
          this._emitValueChangedDelayed()
        } else {
          if (this._emitValueChangedTimer !== null) {
            window.clearTimeout(this._emitValueChangedTimer)
          }
        }
      } else {
        this._updateValueDelayed()
      }
    }
  },
  
  _handleInputKeyDown: function(event) {
    if (event.keyCode === MLAB.Core.KeyEvent.DOM_VK_RETURN) {
      if (this._updateValue()) {
        this.emit("returnPressed")
      }
    }
  },
  
  _updateValueDelayed: function() {
    if (this._updateValueTimer !== null) {
      window.clearTimeout(this._updateValueTimer)
    }
    this._updateValueTimer = window.setTimeout(this.callback("_updateValue"), 350)
  },
  
  _updateValue: function() {
    if (this._updateValueTimer !== null) {
      window.clearTimeout(this._updateValueTimer)
    }
    var ok = false
    var v = this._isFloatValue ? parseFloat(this._input.value) : parseInt(this._input.value)
    if ((this._validator === null) || this._validator.validate(v)) {
      this._value = v
      if (this._slider) {
        this._updateSliderValue(this._value)
      }
      MLAB.GUI.removeStyleSheetClass(this._input, "MLAB-GUI-InvalidNumberEditValue")
      this._updateInputFromValue()
      ok = true
    } else {
      MLAB.GUI.addStyleSheetClass(this._input, "MLAB-GUI-InvalidNumberEditValue")
    }
    return ok
  },
  
  getValue: function() {
    return this._value
  },
  
  _updateInputFromValue: function() {
    if (this._useDoublePrecision) {
      this._input.value = this._value
    } else {
      this._input.value = MLAB.Core.roundDoubleToFloat(this._value)
    }
  },
  
  _updateSliderValue: function(value) {
    var signalsBlocked = this._slider.blockSignals(true)
    this._slider.setValue(this._value)
    this._slider.blockSignals(signalsBlocked)
  },
  
  setValue: function(value) {
    if (isNaN(value)) {
      MLAB.Core.throwException("Attempt to set the value to NaN.")
    }
    if (value !== this._value) {
      this._value = value
      this._updateInputFromValue()
      if (this._slider) {
        this._updateSliderValue(this._value)
      }
      this._emitValueChanged()
    }
  },
  
  _emitValueChangedDelayed: function() {
    if (this._emitValueChangedTimer !== null) {
      window.clearTimeout(this._emitValueChangedTimer)
    }
    this._emitValueChangedTimer = window.setTimeout(this.callback("_emitValueChanged"), 350)
  },
    
  _emitValueChanged: function() {
    this.emit("valueChanged", this._value)
  }
})

/** \class MLAB.GUI.Label
 * 
 */
MLAB.GUI.deriveClass("Label", MLAB.GUI.Widget, {
  Label: function() { 
    this._image = null
    this._titleNode = null
    MLAB.GUI.Label.super.constructor.call(this)
    this._label = this._getDOMElement() 
  },
  
  _createDOMElement: function() {
    var span = document.createElement("span")
    this._setDOMElement(span)
  },
  
  setTitle: function(title) {
    if (this._titleNode !== null) {
      this._label.removeChild(this._titleNode)
    }
    this._titleNode = document.createTextNode(title)
    this._label.appendChild(this._titleNode)
  },
  
  title: function() {
    return (this._titleNode !== null) ? this._titleNode.nodeValue : null
  },
  
  setImageUrl: function(url) {
    if (this._image === null) {
      this._image = document.createElement("img")
      this._label.appendChild(this._image)
    }
    this._image.setAttribute("src", url)
  },
})

/** \class MLAB.GUI.Button
 * 
 */
MLAB.GUI.deriveClass("Button", MLAB.GUI.Widget, {
  Button: function() { 
    this._image = null
    this._activeOnImage = null 
    this._activeOffImage = null
    this._disabledOnImage = null
    this._disabledOffImage = null
    this._normalOnImage = null
    this._normalOffImage = null
    this._button = null
    this._label = null
    this._titleNode = null
    this._title = ""
    MLAB.GUI.Button.super.constructor.call(this)
    this.registerSignal("clicked")
    this.registerSignal("checkStateChanged")
    this._isCheckable = false
    this._isChecked = false
  },
  
  isChecked: function() {
    return this._isChecked
  },
  
  setChecked: function(checked) {
    if (!this._isCheckable) {
      MLAB.Core.throwException("This button is not checkable")
    }
    if (this._isChecked !== checked) {
      this._isChecked = checked
      this._updateStateImage()
      if (this._isChecked) {
        this.addStyleSheetClass("MLAB-GUI-Button-Checked")
      } else {
        this.removeStyleSheetClass("MLAB-GUI-Button-Checked")
      }
      this.emit("checkStateChanged", this._isChecked)
    }
  },
  
  setCheckable: function(isCheckable) {
    if (this._isCheckable !== isCheckable) {
      this._isCheckable = isCheckable
      if (this._isCheckable) {
        this._createLabelElement()
      } else {
        this._createButtonElement()
      }
    }
  },
  
  _createButtonElement: function() {
    var parentNode = null
    if (this._label) {
      parentNode = this._label.parentNode
    }
    this._button = document.createElement("button")
    this._button.onclick = this.callback("_onButtonClick")
    this._setDOMElement(this._button)
    this.addStyleSheetClass("MLAB-GUI-Button")
    if (parentNode) {
      parentNode.insertBefore(this._button, this._label)
      parentNode.removeChild(this._label)
    }
    if (this._label) {
      this._label = null
    }
    if (this._image !== null) {
      this._image.parentNode.removeChild(this._image)
      this._button.appendChild(this._image)
    }
    if (this._titleNode !== null) {
      this._titleNode.parentNode.removeChild(this._titleNode)
      this._button.appendChild(this._titleNode)
    }
  },
  
  _createLabelElement: function() {
    var parentNode = null
    if (this._button) {
      parentNode = this._button.parentNode
    }
    this._label = document.createElement("label")
    this._label.onclick = this.callback("_onButtonClick")
    this._setDOMElement(this._label)
    this.addStyleSheetClass("MLAB-GUI-Button")
    if (parentNode) {
      parentNode.insertBefore(this._label, this._button)
      parentNode.removeChild(this._button)
    }
    if (this._button) {
      this._button = null
    }
    if (this._image !== null) {
      this._image.parentNode.removeChild(this._image)
      this._label.appendChild(this._image)
    }
    if (this._titleNode !== null) {
      this._titleNode.parentNode.removeChild(this._titleNode)
      this._label.appendChild(this._titleNode)
    }
    if (this._isChecked) {
      this.addStyleSheetClass("MLAB-GUI-Button-Checked")
    }
  },
  
  _createDOMElement: function() {
    this._createButtonElement()
  },
  
  _onButtonClick: function() {
    if (this.isEnabled()) {
      if (this._isCheckable) {
        this.setChecked(!this._isChecked)
      }
      this.emit("clicked")
    }
  },
  
  setTitle: function(title) {
    this._title = title
    if (this._titleNode !== null) {
      this._titleNode.parentNode.removeChild(this._titleNode)
      this._titleNode = null
    }
    if (this._title !== "") {
      this._titleNode = document.createTextNode(title)
      if (this._button) {
        this._button.appendChild(this._titleNode)
      } else {
        this._label.appendChild(this._titleNode)
      }
    }
  },
  
  title: function() {
    return this._title
  },

  setImageUrl: function(url) {
    if (this._image === null) {
      this._image = new Image()
      var element = this._button ? this._button : this._label
      if (this._titleNode !== null) {
        element.insertBefore(this._image, this._titleNode)
      } else {
        element.appendChild(this._image)
      }
    }
    this._image.src = url
  },
  
  setActiveOnImage: function(imageUrl) { this._activeOnImage = imageUrl; this._updateStateImage() },
  setActiveOffImage: function(imageUrl) { this._activeOffImage = imageUrl; this._updateStateImage() },
  setDisabledOnImage: function(imageUrl) { this._disabledOnImage = imageUrl; this._updateStateImage() },
  setDisabledOffImage: function(imageUrl) { this._disabledOffImage = imageUrl; this._updateStateImage() },
  setNormalOnImage: function(imageUrl) { this._normalOnImage = imageUrl; this._updateStateImage() },
  setNormalOffImage: function(imageUrl) { this._normalOffImage = imageUrl; this._updateStateImage() },
  
  setEnabled: function(enabled) {
    MLAB.GUI.Button.super.setEnabled.call(this, enabled)
    this._updateStateImage()
  },

  _updateStateImage: function() {
    var image = null
    if (this.isActive()) {
      if (this._isChecked) {
        image = this._activeOnImage
      } else {
        image = this._activeOffImage
      }
    } else if (!this.isEnabled()) {
      if (this._isChecked) {
        image = this._disabledOnImage
      } else {
        image = this._disabledOffImage
      }
    } else {
      if (this._isChecked) {
        image = this._normalOnImage
      } else {
        image = this._normalOffImage
      }
    }
    if (image !== null) {
      this.setImageUrl(image)
    }
  },
})

/** \class MLAB.GUI.CheckBox
 * 
 */
MLAB.GUI.deriveClass("CheckBox", MLAB.GUI.Widget, {
  CheckBox: function() { 
    this._checkBox = null
    this._titleNode = null
    MLAB.GUI.CheckBox.super.constructor.call(this)
    this.registerSignal("stateChange")
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    this._checkBox = document.createElement("input")
    this._checkBox.type = "checkBox"
    this._checkBox.onchange = this.callback("_onCheckboxChange")
    div.appendChild(this._checkBox);
    this._setDOMElement(div)
  },
  
  _onCheckboxChange: function() {
    this.emit("stateChange", this.isChecked())
  },
  
  isChecked: function() {
    return this._checkBox.checked
  },
  
  setChecked: function(checked) {
    this._checkBox.checked = checked
    this.emit("stateChange", this.isChecked())
  },
  
  setTitle: function(title) {  
    var div = this._getDOMElement()
    if (this._titleNode !== null) {
      div.removeChild(this._titleNode)
    }
    this._titleNode = document.createTextNode(title)
    div.appendChild(this._titleNode)
  },  
})

/** \class MLAB.GUI.ComboBoxItem
 * 
 */
MLAB.GUI.defineClass("ComboBoxItem", {
  ComboBoxItem: function(title, value) { 
    this._title = title
    this._value = value
  },
  
  title: function() { return this.title },
  value: function() { return this._value },
})

/** \class MLAB.GUI.ComboBox
 * 
 */
MLAB.GUI.deriveClass("ComboBox", MLAB.GUI.Widget, {
  ComboBox: function() { 
    MLAB.GUI.CheckBox.super.constructor.call(this)
    this.registerSignal("currentItemChanged")
  },
  
  _createDOMElement: function() {
    this._select = document.createElement("select")
    this._select.onchange = this.callback("_onComboBoxChange")
    this._setDOMElement(this._select)
  },
  
  addItem: function(item) {
    var option = document.createElement("option")
    option.text = item._title
    option.value = item._value
    this._select.appendChild(option)
  },
  
  clearItems: function() {
    while (this._select.length > 0) {
      this._select.remove(0)
    }
  },
  
  _getOption: function(index) {
    if (index < this._select.length) {
      return this._select.options[i]
    }
    return null
  },
  
  itemText: function(index) {
    var option = this._getOption(index)
    if (option) {
      return option.text
    }
    return ''
  },
  
  itemValue: function(index) {
    var option = this._getOption(index)
    if (option) {
      return option.value
    }
    return null
  },
  
  setCurrentItem: function(value) {
    var options = this._select.options
    var optionToSelect = null
    for (var i=0; i<this._select.length; i++) {
      var o = options[i]
      if (o.value === value) {
        optionToSelect = o
      } else {
        o.selected = false
      }
    }
    if (optionToSelect) {
      optionToSelect.selected = true
    }
  },
  
  currentItem: function() {
    var options = this._select.options
    for (var i=0; i<this._select.length; i++) {
      if (options[i].selected) {
        return options[i].value
      }
    }
    return null
  },
  
  setCurrentIndex: function(index) {
    var options = this._select.options
    var optionToSelect = null
    for (var i=0; i<this._select.length; i++) {
      var o = options[i]
      if (i === index) {
        optionToSelect = o
      } else {
        o.selected = false
      }
    }
    if (optionToSelect) {
      optionToSelect.selected = true
    }
  },
  
  currentIndex: function() {
    var select = this._getDOMElement()
    return select.selectedIndex
  },
  
  _onComboBoxChange: function() {
    var index = this._select.selectedIndex
    this.emit("currentItemChanged", index >= 0 ? this._select.options[index].value : null)
  },
})

MLAB.GUI.deriveClass("Splitter", MLAB.GUI.Widget, {
  Splitter: function() {
    this._direction = MLAB.GUI.HORIZONTAL
    MLAB.GUI.Splitter.super.constructor.call(this)
  },
  
  setDirection: function(direction) {
    this._direction = direction
  },
  
})

MLAB.GUI.deriveClass("Table", MLAB.GUI.Widget, {
  Table: function() {
    this._table = null
    MLAB.GUI.Table.super.constructor.call(this)
    this._spacing = 0
    this._markLastColumn = false
    this._needFirstColumnResizingWhenShown = false
  },
  
  setSpacing: function(spacing) {
    this._spacing = spacing
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    this._table = document.createElement("table")
    div.appendChild(this._table)
    this._setDOMElement(div)
  },
  
  rowCount: function() {
    return this._table.rows.length
  },
  
  columnCount: function(row) {
    if (row < this._table.rows.length) {
      return this._table.rows[row].cells.length
    }
    return 0
  },
  
  _childVisibilityChanged: function(childWidget, visible) {
    var td = childWidget._getDOMElement().parentNode
    var tr = td.parentNode
    if (tr.cells.length === 1) {
      // case of vertical control
      MLAB.GUI.setDOMElementVisible(tr, visible)
    } else {
      // case of horizontal control
      MLAB.GUI.setDOMElementVisible(td, visible)
    }
  },
  
  addRow: function() {
    return this._table.insertRow(this._table.rows.length)
  },
  
  addWidget: function(row, column, widget, horizontalAlignment, verticalAlignment, columnSpan) {
    var tr = null
    while (row >= this._table.rows.length) {
      tr = this.addRow()
    }
    
    tr = this._table.rows[row]
    
    if (this._markLastColumn) {
      this._removeLastColumnClass(tr)
    }
    
    var td = null
    while (column >= tr.cells.length) {
      td = tr.insertCell(tr.cells.length)
    }
    td = tr.cells[column]
    widget._setParentWidget(this)
    widget.appendToDOM(td)
    if (horizontalAlignment && horizontalAlignment !== "auto") {
      td.style.textAlign = horizontalAlignment
    }
    if (verticalAlignment && verticalAlignment !== "auto") {
      td.style.verticalAlign = verticalAlignment 
    }

    if (columnSpan) {
      td.setAttribute("colspan", columnSpan.toString())
    }
    
    if (this._markLastColumn) {
      this._updateLastColumnClasses()
    }
    
    this._handleWidgetAdded(widget)
  },
  
  setMarkLastColumn: function(markLastColumn) {
    this._markLastColumn = markLastColumn
    if (this._markLastColumn) {
      this._updateLastColumnClasses()
    } else {
      for (var i=0; i<this._table.rows.length; i++) {
        this._removeLastColumnClass(this._table.rows[i])
      }
    }
  },
  
  _removeLastColumnClass: function(tableRow) {
    if (tableRow.cells.length > 0) {
      MLAB.GUI.removeStyleSheetClass(tableRow.cells[tableRow.cells.length-1], "MLAB-GUI-LastColumn")
    }
  },
  
  _updateLastColumnClasses: function() {
    var lastCells = []
    var maxColumnCount = 0
    
    for (var i=0; i<this._table.rows.length; i++) {
      var tr = this._table.rows[i]
      if (tr.cells.length > maxColumnCount) {
        maxColumnCount = tr.cells.length
        lastCells = [tr.cells[maxColumnCount-1]]
      } else if (tr.cells.length === maxColumnCount) {
        lastCells.push(tr.cells[maxColumnCount-1])
      } else if (tr.cells.length > 0){
        MLAB.GUI.removeStyleSheetClass(tr.cells[tr.cells.length-1], "MLAB-GUI-LastColumn")
      }
    }
    for (var i=0; i<lastCells.length; i++) {
      MLAB.GUI.addStyleSheetClass(lastCells[i], "MLAB-GUI-LastColumn")
    }
  },
  
  _setDOMElementVisible: function(visible) {
    MLAB.GUI.Table.super._setDOMElementVisible.call(this, visible)
    if (this.isVisible()) {
      this.resizeFirstColumnToMinimumWidth()
    }
  },
  
  resizeFirstColumnToMinimumWidth: function() {
    if (!this.isVisible()) {
      this._needFirstColumnResizingWhenShown = true
      return
    }
    var firstColumnWidth = 0
    var hasAnyElementInFirstColumn = false
    for (var i=0; i<this._table.rows.length; i++) {
      var cell = this._table.rows[i].cells[0]
      if ((cell.getAttribute("colspan") === null) && (cell.children.length > 0)) {
        hasAnyElementInFirstColumn = true
        var w = cell.children[0].offsetWidth
        if (w > firstColumnWidth) { firstColumnWidth = w }
      }
    }
    if (firstColumnWidth !== 0 || !hasAnyElementInFirstColumn) {
      for (var i=0; i<this._table.rows.length; i++) {
        var cell = this._table.rows[i].cells[0]
        if (cell.getAttribute("colspan") === null) {
          cell.style.width = firstColumnWidth
          if (firstColumnWidth === 0) {
            cell.style.padding = "0"
          }
        }
      }
    }
  },
  
})


/** \class MLAB.GUI.RemoteRenderingWidgetBase(MLAB.GUI.WidgetControl)
 * 
 */
MLAB.GUI.deriveClass("RemoteRenderingWidgetBase", MLAB.GUI.Widget, {
  RemoteRenderingWidgetBase: function() {
    MLAB.GUI.RemoteRenderingWidgetBase.super.constructor.call(this)
 
    this._maximumSize = [0,0]
    this._minimumSize = [0,0]
    this._sizeHint = [0,0]
    this._useSizeHintWidth = false
    this._useSizeHintHeight = false
    this._viewportSize = [-1, -1]
    
    this.registerSignal("viewportSizeChanged")
  },
  
  setImageData: function(mimeType, imageData, metaInformation) {
    MLAB.Core.throwException("RemoteRenderingWidgetBase,setImageData() not implemented")
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.slaveWasActivated
   * 
   * Called from the \ref MLAB.Core.RemoteRenderingSlave "slave" when it is added. If
   * this control is visible, then the slave is enabled. Otherwise the slave will
   * be enabled when the control is shown (_setVisible()).
   */
  slaveWasAdded: function() {
    this._updateSlaveState()
  },
  
  setCursorStyle: function(cursorStyle) {
    this._getDOMElement().style.cursor = cursorStyle
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.getViewportSize
   * 
   * Returns the viewport size.
   * 
   * \returns The viewport size as array with two elements: [width, height].
   */
  getViewportSize: function() {
    return this._viewportSize
  },
  
  initViewportSize: function(w, h) {
    this._viewportSize[0] = w
    this._viewportSize[1] = h
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.resizeViewport
   * 
   * Resizes the viewport.
   * 
   * \param w The new viewport width.
   * \param h The new viewport height.
   */
  resizeViewport: function(w, h) {
    this._viewportSize[0] = w
    this._viewportSize[1] = h
    this.emit("viewportSizeChanged", w, h)
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.setSizeHint
   * 
   * Sets the size hint for the viewport.
   * 
   * \param sizeHint An array with two elements is expected: [width, height]
   */
  setSizeHint: function(sizeHint) { 
    this._sizeHint = sizeHint
    if (this._sizeHint[0] <= 0) {
      this._useSizeHintWidth = false
    }
    if (this._sizeHint[1] <= 0) {
      this._useSizeHintHeight = false
    }
  },

  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.resizeViewportToSizeHint
   * 
   * This method resizes the viewport to the size hint, or the viewport size if
   * the size hint is invalid. MLAB.Core.RemoteRenderingSlave.setSizeHints() calls this function.
   */
  resizeViewportToSizeHint: function() {
    this.resizeViewport(this._useSizeHintWidth ? this._sizeHint[0] : this._viewportSize[0],
                        this._useSizeHintHeight ? this._sizeHint[1] : this._viewportSize[1])
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.setMaximumSize
   * 
   * Sets the maximum size of the viewport.
   * 
   * \param size An array with two elements is expected: [width, height]
   */
  setMaximumSize: function(size) {
    this._maximumSize = size
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.getMaximumSize
   * 
   * Returns the maximum size of the viewport.
   *  
   * \returns  An array with two elements: [width, height]
   */
  getMaximumSize: function() {
    return this._maximumSize
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.setMinimumSize
   * 
   * Sets the maximum size of the viewport.
   * 
   * \param size An array with two elements is expected: [width, height]
   */
  setMinimumSize: function(size) {
    this._minimumSize = size
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.getMinimumSize
   * 
   * Returns the minimum size of the viewport.
   * 
   * \returns An array with two elements: [width, height]
   */
  getMinimumSize: function() {
    return this._minimumSize
  },
  
  setUseSizeHintWidth: function(flag) {
    this._useSizeHintWidth = flag
  },
  
  setUseSizeHintHeight: function(flag) {
    this._useSizeHintHeight = flag
  },

  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.useSizeHintWidth
   * 
   * Returns true if the width of the size hint should be used.
   *
   * \returns A boolean value.
   */
  useSizeHintWidth: function() {
    return this._useSizeHintWidth
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.useSizeHintHeight
   * 
   * Returns true if the height of the size hint should be used.
   *
   * \returns A boolean value.
   */
  useSizeHintHeight: function() { 
    return this._useSizeHintHeight
  },
  
  /** \fn MLAB.GUI.RemoteRenderingWidgetBase.getViewport
   * 
   * Returns the viewport DOM element. Needs to be implemented by the concrete 
   * remote rendering control class. The default implementation throws an exception.
   * 
   * \return Returns the DOM element that is the viewport.
   */
  getViewport: function() {
    MLAB.Core.throwException("MLAB.GUI.RemoteRenderingWidgetBase.getViewport() is not implemented")
  },
  
  setRemoteRenderingSlave: function(slave) {
    this._slave = slave
    this._updateSlaveState()
  },
  
  _updateSlaveState: function() {
    if (this._slave && this._slave.isAdded()) {
      if (this.isVisible()) {
        this._slave.enable()
      } else {
        this._slave.disable()
      }
    }
  },
  
  /**
   * Sets the visibility of this widget. Calls MLAB.GUI.Widget.setVisible() and
   * enables/disables the slave according to the visibility (if the slave exists and is added).
   */
  _setDOMElementVisible: function(visible) {
    MLAB.GUI.RemoteRenderingWidgetBase.super._setDOMElementVisible.call(this, visible)
    this._updateSlaveState()
  },
})



MLAB.GUI.deriveClass("RemoteRenderingWidget", MLAB.GUI.RemoteRenderingWidgetBase, {
  RemoteRenderingWidget: function() {
    MLAB.GUI.RemoteRenderingWidget.super.constructor.call(this)
    this._imgObject = new Image()
    this._imgObject.onload = this.callback("_handleOnImageLoad")

    this.registerSignal("viewerRepainted")
  },
  
  getViewport: function() {
    return this._getDOMElement()
  },
  
  _createDOMElement: function() {
    var canvas = document.createElement("canvas")
    this._setDOMElement(canvas)
    this._setupEventHandler()
  },
  
  _handleOnImageLoad: function() {
    var canvasCtx = this.getViewport().getContext('2d')
    canvasCtx.clearRect(0,0,this._viewportSize[0],this._viewportSize[1])
    // draw the image onto the canvas using its context
    if (this._viewportSize[0] !== this._imgObject.width ||
        this._viewportSize[1] !== this._imgObject.height) {

      // scale the image to the size of the viewport,
      // keeping its aspect ratio
      var factor = this._viewportSize[0] / this._imgObject.width
      if (factor * this._imgObject.height > this._viewportSize[1]) {
        factor = this._viewportSize[1] / this._imgObject.height
      }
      var width  = Math.floor(this._imgObject.width * factor)
      var height = Math.floor(this._imgObject.height * factor)
      x = Math.floor((this._viewportSize[0] - width) / 2)
      y = Math.floor((this._viewportSize[1] - height) / 2)

      canvasCtx.drawImage(this._imgObject, x,y, width, height)
    } else {
      canvasCtx.drawImage(this._imgObject,0,0)
    }
    this.emit("viewerRepainted", this._metaInformation)
  },
  
  _setupEventHandler: function() {
    var canvas = this.getViewport()
    if (MLAB.Core.SystemInfo.isIOS() || MLAB.Core.SystemInfo.isAndroid()) {
      canvas.addEventListener("touchstart",  MLAB.Core.EventHandler.callback("touchStart"),  false)
      canvas.addEventListener("touchmove",   MLAB.Core.EventHandler.callback("touchMove"),   false)
      canvas.addEventListener("touchend",    MLAB.Core.EventHandler.callback("touchEnd"),    false)
      canvas.addEventListener("touchcancel", MLAB.Core.EventHandler.callback("touchCancel"), false)
    } else {
      canvas.addEventListener("mousedown", MLAB.Core.EventHandler.callback("handleLocalMouseEvent"), true)
      // mouseup must be handled globally, to handle drags ending outside the widget:
      // canvas.addEventListener("mouseup",   MLAB.Core.EventHandler.callback("handleLocalMouseEvent"), false)
      canvas.addEventListener("mousemove", MLAB.Core.EventHandler.callback("handleLocalMouseEvent"), false)
      canvas.addEventListener("mouseover", MLAB.Core.EventHandler.callback("handleLocalMouseEvent"), false)
      canvas.addEventListener("mouseout",  MLAB.Core.EventHandler.callback("handleLocalMouseEvent"), false)
      // canvas.onkeydown = MLAB.Core.EventHandler.callback("handleKeyEvent")
      // canvas.onkeyup = MLAB.Core.EventHandler.callback("handleKeyEvent")
      canvas.ondragstart = MLAB.Core.EventHandler.callback("dummyHandler")
      canvas.oncontextmenu = MLAB.Core.EventHandler.callback("dummyHandler")
    }
  },
  
  setImageData: function(mimeType, imageData, metaInformation) {
    this._metaInformation = metaInformation
    // trigger data loading on image object, its onload handler will then paint onto the canvas
    if (typeof(imageData) === "string") {
      // String contains Base64 encoded data
      this._imgObject.src = "data:" + mimeType + ";base64," + imageData
    } else {
      // imageData contains binary data (e.g. UInt8Array)
      this._imgObject.src = URL.createObjectURL(new Blob([imageData], {type: mimeType}))
    }
  },

  resizeViewport: function(w, h) {
    var canvas = this._getDOMElement()
    canvas.setAttribute('width', w)
    canvas.setAttribute('height', h)
    MLAB.GUI.RemoteRenderingWidget.super.resizeViewport.call(this, w, h)
  },
})


MLAB.GUI.deriveClass("Panel", MLAB.GUI.Widget, {
  Panel: function() {
    MLAB.GUI.Panel.super.constructor.call(this)
  }
})


MLAB.GUI.deriveClass("TabBar", MLAB.GUI.Widget, {
  TabBar: function() {
    this._tableRow = null
    this._activeCell = null
    MLAB.GUI.TabView.super.constructor.call(this)
    this.registerSignal("currentTabChanged")
    this.registerSignal("tabCloseRequested")
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    MLAB.GUI.addStyleSheetClass(div, "MLAB-GUI-TabBar")
    var table = document.createElement("table")
    MLAB.GUI.addStyleSheetClass(table, "MLAB-GUI-TabBarTable")
    div.appendChild(table)
    this._tableRow = table.insertRow(0)
    this._setDOMElement(div)
  },
  
  addTab: function(title) {
    var cell = this._tableRow.insertCell(this._tableRow.cells.length)
    var span = document.createElement("span")
    MLAB.GUI.addStyleSheetClass(span, "MLAB-GUI-TabBarItem")
    span.innerHTML = title
    cell.appendChild(span)
    cell.onmousedown = this.callback("_tabClicked")
    if (this._activeCell === null) {
      this._activateCell(cell)
    }
  },
  
  setTabTitle: function(index, title) {
    var ok = false
    if (index >= 0 && index < this._tableRow.cells.length) {
      var cell = this._tableRow.cells[index]
      this._getSpanFromCell(cell).innerHTML = title
      ok = true
    }
    return ok
  },
  
  removeTab: function(index) {
    var ok = false
    if (index >= 0 && index < this._tableRow.cells.length) {
      this._tableRow.deleteCell(i)
      ok = true
    }
    return ok
  },
  
  setTabEnabled: function(index, enabled) {
    if (index >= 0 && index < this._tableRow.cells.length) {
      var cell = this._tableRow.cells[index]
      MLAB.GUI.setDOMElementEnabled(cell, enabled)
    }
  },
  
  _getCellFromEvent: function(event) {
    return event.target.parentElement
  },
  
  _tabClicked: function(event) {
    var cell = this._getCellFromEvent(event)
    var isCellEnabled = this.isEnabled() && MLAB.GUI.isDOMElementEnabled(cell)
    if (event.button === 0 /*left mouse button*/) {
      event.preventDefault()
      if (isCellEnabled) {
        this._activateCell(cell)
      }
    } else if (event.button === 1 /*middle mouse button*/) {
      event.preventDefault()
      if (isCellEnabled) {
        this._closeCell(cell)
      }
    }
  },
  
  closeTab: function(index) {
    var ok = false
    if (index >= 0 && index < this._tableRow.cells.length) {
      this._closeCell(this._tableRow.cells[i])
      ok = true
    }
    return ok
  },
  
  _closeCell: function(cell) {
    this.emit("tabCloseRequested", cell ? this._cellIndex(cell) : -1)
  },
  
  activateTab: function(index) {
    var ok = false
    if (index >= 0 && index < this._tableRow.cells.length) {
      this._activateCell(this._tableRow.cells[index])
      ok = true
    }
    return ok
  },
  
  tabIndex: function(title) {
    for (var i=0; i<this._tableRow.cells.length; i++) {
      var cell = this._tableRow.cells[i]
      if (this._getSpanFromCell(cell).innerHTML === title) {
        return i
      }
    }
    return -1
  },
  
  _cellIndex: function(cell) {
    for (var i=0; i<this._tableRow.cells.length; i++) {
      if (this._tableRow.cells[i] === cell) {
        return i
      }
    }
    return -1
  },
  
  _getSpanFromCell: function(cell) {
    return cell.children[0]
  },
  
  _activateCell: function(cell) {
    if (this._activeCell !== cell) {
      if (this._activeCell !== null) {
        MLAB.GUI.removeStyleSheetClass(this._getSpanFromCell(this._activeCell), "MLAB-GUI-ActiveTabBarItem")
      }
      this._activeCell = cell
      if (cell) {
        MLAB.GUI.addStyleSheetClass(this._getSpanFromCell(cell), "MLAB-GUI-ActiveTabBarItem")
      }
      this.emit("currentTabChanged", cell ? this._cellIndex(cell) : -1)
    }
  },
})


MLAB.GUI.deriveClass("TabView", MLAB.GUI.Widget, {
  TabView: function(position) {
    this._tabStackDiv = null
    this._tabBar = null
    this._tabs = []
    this._activeTabIndex = -1
    this._position = position ? position : "top"
    MLAB.GUI.TabView.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    this._setDOMElement(div)
    if (this._position === "top") {
      this._tabBar = MLAB.GUI.WidgetFactory.create("TabBar")
      this._tabBar.connect("currentTabChanged", this, "_currentTabChanged")
      this._tabBar.connect("tabCloseRequested", this, "_tabCloseRequested")
      MLAB.GUI.TabView.super.addWidget.call(this, this._tabBar)
    }
    this._tabStackDiv = document.createElement("div")
    if (this._position !== "invisible") {
      MLAB.GUI.addStyleSheetClass(this._tabStackDiv, "MLAB-GUI-TabViewStack")
    }
    div.appendChild(this._tabStackDiv)
  },
  
  _addWidgetToDOM: function(widget) {
    if (widget === this._tabBar) {
      MLAB.GUI.TabView.super._addWidgetToDOM.call(this, widget)
    } else {
      widget._setParentWidget(this)
      widget.appendToDOM(this._tabStackDiv)
    }
  },
  
  addWidget: function(tabViewItem) {
    this._tabs.push(tabViewItem)
    if (this._tabBar) {
      this._tabBar.addTab(("title" in tabViewItem) ? tabViewItem.title() : "&nbsp;")    
    }
    MLAB.GUI.TabView.super.addWidget.call(this, tabViewItem)
    // hide the tab, if it is not the first one
    if (this._tabs.length !== 1) {
      tabViewItem.setVisible(false)
    } else {
      this._activeTabIndex = 0
    }
  },
  
  setTabEnabled: function(tabViewItem, enabled) {
    var index = this._getTabIndex(tabViewItem)
    if (index >= 0) {
      if (this._tabBar) {
        this._tabBar.setTabEnabled(index, enabled)
      }
      tabViewItem.setEnabled(enabled)
    }
  },

  setTabTitle: function(index, title) {
    if (this._tabBar) {
      this._tabBar.setTabTitle(index, title)
    }
  },
  
  setActiveTab: function(index) {
    if (this._tabBar) {
      this._tabBar.activateTab(index)
    } else {
      this._currentTabChanged(index)
    }
  },
  
  removeTab: function(widget) {
    var ok = false
    this.removeWidget(widget)
    var index = this._getTabIndex(widget)
    if (index >= 0) {
      if (this._tabBar.removeTab(index) === true) {
        ok = true
      }
    }
    return ok
  },
  
  closeTab: function(widget) {
    var ok = false
    var index = this._getTabIndex(widget)
    if (index >= 0) {
      if (this._tabBar) {
        this._tabBar.closeTab(index)
      } else {
        _tabCloseRequested(index)
      }
      ok = true
    }
    return ok
  },
  
  _tabCloseRequested: function(index) {
    if (index >= 0 && index === this._activeTabIndex) {
      this.setActiveTab(index > 0 ? index - 1 : 0)
      this.removeTab(this._tabs[index])
    }
  },
  
  _getTabIndex: function(widget) {
    for (var i=0; i<this._tabs.length; i++) {
      if (this._tabs[i] === widget) {
        return i
      }
    }
    return -1
  },
  
  tabCount: function() {
    return this._tabs.length
  },
  
  _currentTabChanged: function(index) {
    if (this._activeTabIndex !== -1) {
      this._tabs[this._activeTabIndex].hide()
    }
    if (index >= 0 && index < this._tabs.length) {
      this._tabs[index].show()
      this._activeTabIndex = index
    } else {
      this._activeTabIndex = -1
    }
  },
})

MLAB.GUI.deriveClass("TabViewItem", MLAB.GUI.Table, {
  TabViewItem: function() {
    this._title = "untitled"
    MLAB.GUI.TabViewItem.super.constructor.call(this)
  },
  
  setTitle: function(title) {
    this._title = title
  },
  
  title: function() {
    return this._title
  },
})

MLAB.GUI.WidgetFactory.registerWidgetClass("Box", MLAB.GUI.Box)
MLAB.GUI.WidgetFactory.registerWidgetClass("Button", MLAB.GUI.Button)
MLAB.GUI.WidgetFactory.registerWidgetClass("CheckBox", MLAB.GUI.CheckBox)
MLAB.GUI.WidgetFactory.registerWidgetClass("ComboBox", MLAB.GUI.ComboBox)
MLAB.GUI.WidgetFactory.registerWidgetClass("HyperText", MLAB.GUI.HyperText)
MLAB.GUI.WidgetFactory.registerWidgetClass("Label", MLAB.GUI.Label)
MLAB.GUI.WidgetFactory.registerWidgetClass("LineEdit", MLAB.GUI.LineEdit)
MLAB.GUI.WidgetFactory.registerWidgetClass("NumberEdit", MLAB.GUI.NumberEdit)
MLAB.GUI.WidgetFactory.registerWidgetClass("Panel", MLAB.GUI.Panel)
MLAB.GUI.WidgetFactory.registerWidgetClass("RemoteRenderingWidget", MLAB.GUI.RemoteRenderingWidget)
MLAB.GUI.WidgetFactory.registerWidgetClass("Table", MLAB.GUI.Table)
MLAB.GUI.WidgetFactory.registerWidgetClass("TabBar", MLAB.GUI.TabBar)
MLAB.GUI.WidgetFactory.registerWidgetClass("TabView", MLAB.GUI.TabView)
MLAB.GUI.WidgetFactory.registerWidgetClass("TabViewItem", MLAB.GUI.TabViewItem)
MLAB.GUI.WidgetFactory.registerWidgetClass("Widget", MLAB.GUI.Widget)
