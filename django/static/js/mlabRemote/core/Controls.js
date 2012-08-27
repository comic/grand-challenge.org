//=============================================================================
// MLABWidgetControl
//=============================================================================
function MLABWidgetControl(mdlTree, moduleContext) {
  var self = this;
  
  this._moduleContext = moduleContext;
  this._ctx = moduleContext.getModule();
  this._id = gApp.getNextWidgetControlID();

  this._mdlTree = mdlTree;
  this._domElement = null;
  this._field = null;
  
  this.getDomElement = function() { return self._domElement; }
  this.getField = function() { return self._field; }
  this.getId = function() { return self._id; }
  
  this.isFieldControl = function() { return false; }
  
  this.fieldChanged = function(field) {
    console.log("field changed:" + self._mdlTree.value);
  };
  
  this.getName = function() { return self._name; };
  
  // extends the id by the widget control id
  this.getElementId = function(id) {
    // do not include self._id in the element id, otherwise css rules cannot be applied,
    // because self._id is generated at runtime, it is not known when writing css rules
    return id + "_" + self._ctx.getModule().getName() + "_" + self.getName();
  };
  
  this.setupWidgetControl = function(className, parentControl) {
    if (self._mdlTree.value && self._mdlTree.value.length > 0) {
      var f = self._ctx.lookupField(self._mdlTree.value);
      if (f) { 
        self._field = f; 
        f.addListener(self);
      }
    }
    
    self._name = self.getMDLAttribute("name", null);
    if (self._name) {
      className += " " + self._name;
    }
    self._domElement = document.createElement('div');
    self._domElement.setAttribute("class", className);
    
    self._domElement.mlabControl = self;
    
    self._isEnabled = mlabIsTrue(self.getMDLAttribute("enabled", "yes"));
    self._isVisible = mlabIsTrue(self.getMDLAttribute("visible", "yes"));
    
    self._parent = parentControl;
  };
  
  this.appendChild = function(childControl) {
    self._domElement.appendChild(childControl._domElement);
  };
  
  this.setupTypicalTags = function() { 
    var w = self.getMDLAttribute("w", null);
    if (w) { self._domElement.style.width = w + "px"; }
    var h = self.getMDLAttribute("h", null);
    if (h) { self._domElement.style.height = h + "px"; }
  };
  
  this.setupChildren = function() {
    try {
      if (self._mdlTree.children) {
        for (var i=0; i<self._mdlTree.children.length; i++) {
          var c = self._moduleContext.createControl(self._mdlTree.children[i]);
          if (c) { self.setupChild(c); }
        }
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
  
  this.setupChild = function(child) {
    child.setup(self);
    child.setupTypicalTags();
    self.appendChild(child);
    child.handleAppendedToDom();
    child.setupChildren();
  };
  
  this.handleAppendedToDom = function() {
    
  };
  
  this.getMDLAttribute = function(attributeName, defaultValue) {
    if (self._mdlTree.children) {
      for (var i=0; i<self._mdlTree.children.length; i++) {
        var child = self._mdlTree.children[i];
        if (child.name == attributeName) {
          return child.value;
        }
      }
    }
    return defaultValue;
  };
  
  this.getMDLFieldAttribute = function(attributeName) {
    var field = null;
    var fieldName = self.getMDLAttribute(attributeName);
    if (fieldName) {
      field = self._moduleContext.getModule().lookupField(fieldName);
      if (!field) {
        self._moduleContext.logError("MLABWidgetControl.getMDLFieldAttribute: field not found: " + fieldName);
      }
    }
    return field;
  };
  
  this.getWindowControl = function() {
    var result = null;
    var c = self;
    while (c && (c._mdlTree.name != "Window")) {
      c = c._parent;
    }
    if (c && c._mdlTree.name == "Window") {
      result = c;
    }
    return result;
  };
  
  this.getName = function() {
    var name = '';
    var c = mlabGetMDLChild(self._mdlTree, "name");
    if (c) { name = c.value; }
    return name;
  };
  
  this.getType = function() {
    return self._mdlTree.name;
  };
};


//=============================================================================
// MLABFrameControl
//=============================================================================
function MLABFrameControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.widgetControlSetupTypicalTags = this.setupTypicalTags;
  this.setupTypicalTags = function() {
    self.widgetControlSetupTypicalTags();
    var margin = self.getMDLAttribute("margin", "2");
    self._table.style.margin = margin + "px";
    if (self.getMDLAttribute("w", null) != null) {
      self._table.style.width = self._domElement.style.width;
    } 
    if (self.getMDLAttribute("h", null) != null) {
      self._table.style.height = self._domElement.style.height;
    }
    
    self._spacing = self.getMDLAttribute("spacing", "2");
  };
    
  this._setTableCellAttributes = function(child, tableCell) {
    var alignX = child.getMDLAttribute("alignX", null);
    if (alignX) {
      alignX = alignX.toLowerCase();
      if (alignX != "auto") {
        tableCell.style.textAlign = alignX;
      }
    }
    var alignY = child.getMDLAttribute("alignY", null);
    if (alignY) {
      alignY = alignY.toLowerCase();
      if (alignY != "auto") {
        tableCell.style.verticalAlign = alignY;
      }
    }
  };
}


//=============================================================================
// MLABHorizontalControl
//=============================================================================
function MLABHorizontalControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABFrameControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupHorizontalControl = function(parentControl) {
    self.setupWidgetControl("MLABHorizontalControl", parentControl);
    self._table = document.createElement("table");
    self._row = self._table.insertRow(0);
    var verticalAlign = null;
    var verticalAlignTree = mlabGetMDLChild(self._mdlTree, "alignY");
    if (verticalAlignTree) {
      verticalAlign = verticalAlignTree.value;
    }
    self._row.style.verticalAlign = verticalAlign ? verticalAlign : "top";
    self._domElement.appendChild(self._table);    
  };
  
  this.appendChild = function(child) {
    var tableCell = self._row.insertCell(-1);
    if (self._row.cells.length > 1) {
      // set the right padding of the previous cell to emulate spacing
      self._row.cells[self._row.cells.length-2].style.paddingRight = self._spacing + "px";
    }
    tableCell.appendChild(child._domElement);
    self._setTableCellAttributes(child, tableCell);
  };
}


//=============================================================================
// MLABFieldControl
//=============================================================================
function MLABFieldControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.isFieldControl = function() { return true; }
  
  // The default implementation exchanges the field dom element with a label.
  // The setup<Type>Field functions may changes this function.
  this._disabledLabelDomElement = null;
  this._setEditableFunction = function(editable) {
    if (!editable) {
      if (!self._disabledLabelDomElement) {
        self._disabledLabelDomElement = document.createElement("div");
        self._disabledLabelDomElement.setAttribute("class", "DisabledFieldControlLabel");
      }
      self._disabledLabelDomElement.innerHTML = self.getField().getValue();
      
      var parentNode = self._fieldDomElement.parentNode;
      parentNode.removeChild(self._fieldDomElement);
      parentNode.appendChild(self._disabledLabelDomElement);
    } else {
      var parentNode = self._disabledLabelDomElement.parentNode;
      parentNode.removeChild(self._disabledLabelDomElement);
      parentNode.appendChild(self._fieldDomElement);
    }
  };
  
  this.setup = this.setupFieldControl = function(parentControl) {
    self.setupWidgetControl("MLABFieldControl", parentControl);
        
    var table = document.createElement("table");
    self._tableRow = table.insertRow(0);
    self._domElement.appendChild(table);

    if (self._field) {
      if      (self._field.isBoolField())    { self._setupBoolField(); }
      else if (self._field.isColorField())   { self._setupColorField(); }
      else if (self._field.isDoubleField())  { self._setupDoubleField(); }
      else if (self._field.isEnumField())    { self._setupEnumField(); }
      else if (self._field.isFloatField())   { self._setupFloatField(); }
      else if (self._field.isIntegerField()) { self._setupIntegerField(); }
      else if (self._field.isStringField())  { self._setupStringField(); }
      else if (self._field.isTriggerField()) { self._setupTriggerField(); }
      else if (self._field.isVectorField())  { self._setupVectorField(); }
      else {
        self._setupStringField();
      }
    } else {
      self._moduleContext.logError("MLABFieldControl.setup: no field has been specified");
    }
  };
  
  this.setupTypicalTags = function() {
    if (!self._field) { return; }
    
    if (self._fieldDomElement) {
      var w = self.getMDLAttribute("w", null);
      if (w) { self._fieldDomElement.style.width = w + "px"; }
      var h = self.getMDLAttribute("h", null);
      if (h) { self._fieldDomElement.style.height = h + "px"; }
      
      var textAlign = self.getMDLAttribute("textAlign", null);
      if (textAlign) {
        self._fieldDomElement.style.textAlign = textAlign.toLowerCase();
      }
    }

    // TODO: c++ MLABFieldControl uses MLABModule::translate() on the title
    self._title = self.getMDLAttribute("title", null);
    if (!self._title) { 
      self._title = mlabGetAutomaticFieldTitle(self._field.getName(), /*splitUppercase=*/true);
      self._hasAutomaticTitle = true;
    } else {
      self._hasAutomaticTitle = false;
    }
    
    self._tableRow.insertCell(0).appendChild(self._fieldDomElement);
    
    if (self._field.isTriggerField()) {
      self._fieldDomElement.value = self._title;
    } else {
      var titleFieldName = self.getMDLAttribute("titleField", null);
      if (titleFieldName) {
      self._titleField = self._ctx.lookupField(titleFieldName);
        if (self._titleField) {
          self._titleField.addListener(self);
          self._titleFieldChanged();
        } else {
          self._moduleContext.logError("MLABFieldControl.setupTypicalTags: the given title field " +
                                       "is not found by the module context: " + titleFieldName);
        }
      }

      // ako: add class to enable making labels invisible via css
      self._labelDomElement = document.createElement("div");
      self._labelDomElement.innerHTML = self._title + (self._hasAutomaticTitle ? ":" : "");
      self._tableRow.insertCell(0).appendChild(self._labelDomElement);
    }
  };
  
  this.handleAppendedToDom = function() {
    self._isEditable = true;
    self._editField = self.getMDLFieldAttribute("editField");
    if (self._editField) {
      self._editField.addListener(self);
      self._editFieldChanged();
    } else {
      self.setEditable(mlabIsTrue(self.getMDLAttribute("edit", "yes")));
    }
  };
  
  this._editFieldChanged = function() {
    self.setEditable(mlabIsTrue(self._editField.getValue()));
  };
  
  this.setEditable = function(editable) {
    if (self._isEditable != editable) {
      self._isEditable = editable;
      if (self._setEditableFunction) {
        self._setEditableFunction(editable);
      } else {
        self._moduleContext.logError("MLABFieldControl.setEditable: _setEditableFunction is null");
      }
    }
  };
  
  this._setupBoolField = function() {
    var input = document.createElement("input");
    input.type = "checkbox";
    if (self.getField().getBoolValue()) { input.checked = true; }
    input.onchange = self._onCheckboxChange;
    self._fieldDomElement = input;
    self._setEditableFunction = function(editable) {
      input.disabled = !editable;
    };
  };
  
  this._onCheckboxChange = function() {
    var input = self._fieldDomElement;
    self._field.setBoolValue(input.checked);
  };
  
  this._setupEnumField = function() { 
    var select = document.createElement("select");
    var enumItems = self._field.items();
    for (var i=0; i<enumItems.length; i++) {
      var option = document.createElement("option");
      option.innerHTML = enumItems[i];
      if (self._field.getValue() == enumItems[i]) { option.selected = true; }
      select.appendChild(option);
    }
    select.onchange = self._onComboBoxChange;
    self._fieldDomElement = select;
  };
  
  this._onComboBoxChange = function() {
    var select = self._fieldDomElement;
    var item = null;
    for (var i=0; i<select.length; i++) {
      if (select.options[i].selected) {
        item = select.options[i].innerHTML;
        break;
      }
    }
    if (item != null) {
      self._field.setCurrentItem(item);
    } else {
      self._moduleContext.logError("MLABFieldControl._onComboBoxChange: no selected option found, field: " + self._field.getName());
    }
  };
  
  this._setupStringField = function() {
    var input = document.createElement("input");
    input.value = self._field.getValue();
    input.onkeydown = self._onLineEditKeyDown;
    self._fieldDomElement = input;
  }
  
  this._onLineEditKeyDown = function(event) {    
    if (event.keyCode == KeyEvent.DOM_VK_RETURN) {
      var input = self._fieldDomElement;
      self._field.setValue(input.value);
    }
  };
  
  this._setupNumberField = function() {
    self._setupStringField();
  };
  
  this._numberFieldChanged = function() {
    self._fieldDomElement.value = self._field.getValue();
  };
  
  this._setupDoubleField = function() { self._setupNumberField(); }  
  this._setupFloatField = function() { self._setupNumberField(); }
  this._setupIntegerField = function() { self._setupNumberField(); }
  
  this._setupTriggerField = function() { 
    var button = document.createElement("input");
    button.type = "button";
    button.onclick = self._onButtonClick;
    self._fieldDomElement = button;
  }
  
  this._onButtonClick = function() { self._field.trigger(); };
  
  // by default, other field types are displayed as a string field
  this._setupColorField = function() { self._setupStringField(); }    
  this._setupVectorField = function() { self._setupStringField(); }
  
  this._titleFieldChanged = function() {
    self._title = self._titleField.getValue();
    self._labelDomElement.innerHTML = self._title;
  };
  
  this.fieldChanged = function(field) {
    if (field == self._field) {
      if (self._disabledLabelDomElement) {
        self._disabledLabelDomElement.innerHTML = self._field.getValue();
      }
      if (field.isBoolField()) {
        var input = self._fieldDomElement;
        input.checked = field.getBoolValue();
      
      } else if (field.isEnumField()) {
        var select = self._fieldDomElement;
        for (var i=0; i<select.length; i++) {
          if (select.options[i].innerHTML == field.getValue()) {
            select.options[i].selected = true;
          } else {
            select.options[i].selected = false;
          }
        }
      } else if (field.isNumberField()) {
        self._numberFieldChanged();
      } else if (field.isStringField()) {
        self._fieldDomElement.value = field.getValue();
      }
    } else if (field == self._titleField) {
      self._titleFieldChanged();
    } else if (field == self._editField) {
      self._editFieldChanged();
    } else {
      self._moduleContext.logError("MLABFieldControl.fieldChanged: unexpected field: " + field.getName() + ":" + field.getType());
    }
  };
}


//=============================================================================
// MLABLineEditControl
//=============================================================================
function MLABLineEditControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupLineEditControl = function(parentControl) {
    self.setupWidgetControl("MLABLineEditControl", parentControl);
  };
}


//=============================================================================
// MLABRemoteRenderingControl
//=============================================================================
function MLABRemoteRenderingControl(mdlTree, moduleContext) {
  var self = this;
  
  this._useStreaming = gApp.shouldUseStreaming();
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this._highQualityTimerId = null;
  this._hasSceneChangedAgain = false;
  this._isUpdatePending = false;
  this._renderingSlaveAdded = false;
  
  // the module context actives the rendering control in a certain state.
  // then the rendering slave can be added, if the base update was already received.
  this._isActivated = false;
  this._isBaseFieldUpdated = false;
  
  this._pendingBaseFieldMessages = [];
  
  this._cursorShapes = {};

  this._sizeHint = [0,0];
  this._maximumSizeHint = [0,0];
  this._useSizeHintWidth = false;
  this._useSizeHintHeight = false;
  
  // the remote rendering module supports more than one slave for the rendered
  // image, so we could have multiple images of the same scene with different
  // dimensions in the dom
  this._remoteRenderingSlaveID = 1;

  this.getBaseField = function() { return self._baseField; }
  this.getViewport = function() { return self._canvas; }
  this.getRemoteRenderingSlaveID = function() { return self._remoteRenderingSlaveID; };
  
  this.setup = this.setupRemoteRenderingControl = function(parentControl) {
    self.setupWidgetControl("MLABRemoteRenderingControl", parentControl);
    self._baseField = self._mdlTree.value;
    self._canvas = document.createElement("canvas");
    self._canvasCtx = self._canvas.getContext('2d'); 
    self._imgObject = new Image();
    self._imgObject.onload = function() {  
      self._canvasCtx.clearRect(0,0,self._imgWidth,self._imgHeight);
      // draw the image onto the canvas using its context
      if (self._imgWidth != self._imgObject.width) {
        // scale images which have a different size
        self._canvasCtx.drawImage(self._imgObject,0,0, self._imgWidth, self._imgHeight)
      } else {
        self._canvasCtx.drawImage(self._imgObject,0,0)
      }
    };  
    self._domElement.appendChild(self._canvas);
    self._moduleContext.registerRemoteRenderingControl(self._baseField, self);
  };
  
  this.setupTypicalTags = function() {
    var w = self.getMDLAttribute("w", "-1");
    var h = self.getMDLAttribute("h", "-1");
    self._useSizeHintWidth = false;
    self._useSizeHintHeight = false;
    if (w == "-1") { w = "400"; self._useSizeHintWidth = true; }
    if (h == "-1") { h = "400"; self._useSizeHintHeight = true; }
    self.resizeViewport(w, h);
  };
  
  this._addPendingBaseFieldMessage = function(message) {
    self._pendingBaseFieldMessages.push(message);
  };
  
  this._flushPendingBaseFieldMessages = function() {
    // flush pending base field messages first
    var l = self._pendingBaseFieldMessages;
    self._pendingBaseFieldMessages = [];
    for (var i=0; i<l.length; i++) { self.handleBaseFieldMessage(l[i]); }
  };
  
  this.handleBaseFieldMessage = function(message) {
    if (!self._renderingSlaveAdded &&
        (message.type != MLAB_MSG_MODULE_BASE_FIELD_TYPE)) {
      self._addPendingBaseFieldMessage(message);
      return;
    } else {
      if (self._pendingBaseFieldMessages.length > 0) {
        self._flushPendingBaseFieldMessages();
      }
    }
    
    switch (message.type) {
      case MLAB_MSG_MODULE_BASE_FIELD_TYPE:
        if (!self._isBaseFieldUpdated) {
          self._isBaseFieldUpdated = true;
          self._addRenderingSlaveIfPossible();
        }
        break;
      
      case MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED:
        self.remoteSceneChanged(message);
        break;
        
      case MLAB_MSG_RENDERING_RENDERED_IMAGE:
        if (self._useStreaming) {
          // send acknowledge for the received image:
          var baseGeneration = 1; // TODO: should this be a global, incremented value?
          var m = new MLABRenderingRenderedImageAcknowledgeMessage();
          m.setData(self._baseField, baseGeneration, self._remoteRenderingSlaveID);
          self._moduleContext.sendMessage(m);
        }
        self.remoteImageReceived(message);
        break;
        
      case MLAB_MSG_RENDERING_SET_CURSOR_SHAPE:
        self.remoteCursorReceived(message);
        break;
      
      case MLAB_MSG_RENDERING_SET_SIZE_HINTS:
        self.setSizeHints(message);
        break;
        
      default:
        self._moduleContext.logError("MLABRemoteRenderinControl.handleBaseFieldMessage: unhandled message " + message.type);
        break;
      }
  };
  
  this.activateRenderingSlave = function() {
    if (self._isActivated) { return };    
    self._isActivated = true;
    self._addRenderingSlaveIfPossible();
  }
  
  this._addRenderingSlaveIfPossible = function() {
    if (self._renderingSlaveAdded || !self._isActivated || !self._isBaseFieldUpdated) {
      return;
    }    
    self._renderingSlaveAdded = true;
    systemInfo = gApp.getSystemInfo();
    if (systemInfo.isIOS() || systemInfo.isAndroid()) {
      self._canvas.addEventListener("touchstart",  gApp.getEventHandler().touchStart,  false);
      self._canvas.addEventListener("touchmove",   gApp.getEventHandler().touchMove,   false);
      self._canvas.addEventListener("touchend",    gApp.getEventHandler().touchEnd,    false);
      self._canvas.addEventListener("touchcancel", gApp.getEventHandler().touchCancel, false);
    } else {
      // install event handlers:
      self._canvas.addEventListener("mousedown", gApp.getEventHandler().handleLocalMouseEvent, true);
      //self._canvas.addEventListener("mouseup",   gApp.getEventHandler().handleLocalMouseEvent, false);
      self._canvas.addEventListener("mousemove", gApp.getEventHandler().handleLocalMouseEvent, false);
      self._canvas.addEventListener("mouseover", gApp.getEventHandler().handleLocalMouseEvent, false);
      self._canvas.addEventListener("mouseout",  gApp.getEventHandler().handleLocalMouseEvent, false);
      self._canvas.addEventListener("dblclick", gApp.getEventHandler().handleLocalMouseEvent, false);
      // self._canvas.onkeydown = gApp.getEventHandler().handleKeyEvent;
      // self._canvas.onkeyup = gApp.getEventHandler().handleKeyEvent;
      self._canvas.ondragstart = gApp.getEventHandler().dummyHandler;
      self._canvas.oncontextmenu = gApp.getEventHandler().dummyHandler;
    }
    
    var baseGeneration = 1; // TODO: should this be a global, incremented value?
    
    var m = new MLABRenderingSlaveAddedMessage();
    m.setData(self._baseField, baseGeneration, self._remoteRenderingSlaveID);
    self._moduleContext.sendMessage(m);
    
    // send the render size we require:
    var m = new MLABRenderingSetRenderSizeMessage();
    m.setData(self._baseField, baseGeneration, self._remoteRenderingSlaveID, self._imgWidth, self._imgHeight);
    self._moduleContext.sendMessage(m);

    if (self._useStreaming) {
      var m = new MLABRenderingRenderStartStreamingMessage();
      m.setData(self._baseField, baseGeneration, self._remoteRenderingSlaveID);
      self._moduleContext.sendMessage(m);
    } else {
      // request the initial image
      self.requestImageUpdate(baseGeneration, false);
    }
  };
  
  this.requestImageUpdate = function(baseGeneration, highQuality) {
    self._isUpdatePending = true;
    
    var m = new MLABRenderingRenderRequestMessage();
    m.setData(self._baseField, baseGeneration, self._remoteRenderingSlaveID, highQuality?1:0);
    self._moduleContext.sendMessage(m);
  };
  
  this.remoteSceneChanged = function(message) {
    if (!self._useStreaming) {
      // request a new image (currently in low quality only)
      if (self._isUpdatePending) {
        // request updated image delayed
        self._hasSceneChangedAgain = true;
      } else {
        self.requestImageUpdate(message.baseGeneration, false);
      }
    }
  };
  
  this.remoteImageReceived = function(message) {
    // clear old timer if it exists
    if (self._highQualityTimerId != null) {
      window.clearTimeout(self._highQualityTimerId);
      self._highQualityTimerId = null;
    }

    if (!self._useStreaming) {
      if (self._hasSceneChangedAgain) {
        // scene has changed again in the meantime, request updated image
        self._hasSceneChangedAgain = false;
        var m = new MLABRenderingRenderRequestMessage();
        m.setData(self._baseField, message.baseGeneration, self._remoteRenderingSlaveID, 0);
        self._moduleContext.sendMessage(m);
      
      } else {
        // we may request an updated image directly now
        self._isUpdatePending = false;
                 
        if (!message.fullQuality) {
          // create new timer to request high quality image:
          self._highQualityTimerId = window.setTimeout(
              function () { self.requestImageUpdate(message.baseGeneration, true)}, 
              500);
        }
      }
    }    
    // It is faster to set the image after the new request has been sent above.
    var mimeType = (message.fullQuality ? "image/png" : "image/jpeg");

    // trigger data loading on image object, its onload handler will then paint
    // onto the canvas
    self._imgObject.src = "data:" + mimeType + ";base64," + message.imageData;
  };
  
  this.setSizeHints = function(message)
  {
    self._sizeHint = message.sizeHint;
    self._maximumSizeHint = message.maximumSizeHint;
    if (self._sizeHint[0] <= 0) {
      self._useSizeHintWidth = false;
    }
    if (self._sizeHint[1] <= 0) {
      self._useSizeHintHeight  = false;
    }

    // if no width or height is given in the MDL, then use the size hint now
    if (self._useSizeHintWidth || self._useSizeHintHeight) {
      var w = self._useSizeHintWidth ? self._sizeHint[0] : self._imgWidth;
      var h = self._useSizeHintHeight ? self._sizeHint[1] : self._imgHeight;
      this.resizeViewport(w, h);

      var baseGeneration = 1; // TODO: should this be a global, incremented value?
      // send the render size we require:
      var m = new MLABRenderingSetRenderSizeMessage();
      m.setData(self._baseField, baseGeneration, self._remoteRenderingSlaveID, self._imgWidth, self._imgHeight);
      self._moduleContext.sendMessage(m);
    }
  }
  
  this.resizeViewport = function(w, h)
  {
    self._canvas.setAttribute('width', w + "px");
    self._canvas.setAttribute('height', h + "px");
    self._imgWidth = w;
    self._imgHeight = h;
    
    // TODO: if we want to allow dynamic resizing of the viewer in the future,
    //       we need to send a new SetRenderSize message to the server here.
  }
  
  this.remoteCursorReceived = function(message) {
    var cursorStyle = ""
    if (message.hasQCursor) {
      // use cursor shape provided in message
      switch (message.shape) {
      case  0: cursorStyle = "default";     break;
      case  1: cursorStyle = "n-resize";    break;
      case  2: cursorStyle = "crosshair";   break;
      case  3: cursorStyle = "wait";        break;
      case  4: cursorStyle = "text";        break;
      case  5: cursorStyle = "ns-resize";   break;
      case  6: cursorStyle = "ew-resize";   break;
      case  7: cursorStyle = "nesw-resize"; break;
      case  8: cursorStyle = "nwse-resize"; break;
      case  9: cursorStyle = "move";        break;
      case 10: cursorStyle = "none";        break;
      case 11: cursorStyle = "row-resize";  break;
      case 12: cursorStyle = "col-resize";  break;
      case 13: cursorStyle = "pointer";     break;
      case 14: cursorStyle = "not-allowed"; break;
      case 15: cursorStyle = "help";        break;
      case 16: cursorStyle = "wait";        break;
      case 17: cursorStyle = "cell";        break; // no direct match  // better: -moz-grab
      case 18: cursorStyle = "all-scroll";  break; // no direct match  // better: -moz-grabbing
      case 24:
        // bitmap cursor, construct cursor style with data url:
        cursorStyle = "url(data:image/png;base64," + message.imageData + ") " + message.hotSpot + " " + message.unknown + ", default";
        break;
      default:
        self._moduleContext.logError("Unhandled cursor shape: " + message.shape);
      }
      if (cursorStyle.length > 0) {
        // remember cursor shape
        self._cursorShapes[message.shapeID] = cursorStyle;
      }
    } else {
      // use remembered cursor style
      cursorStyle = self._cursorShapes[message.shapeID];
    }
    
    // set cursor style on tag
    if (cursorStyle) { self._canvas.style.cursor = cursorStyle; }
  };
}


//=============================================================================
// MLABListViewControl
//=============================================================================
function MLABListViewControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupListViewControl = function(parentControl) {
    self.setupWidgetControl("MLABListViewControl", parentControl);
    
    self._rowSeparator = mlabGetMDLChild(self._mdlTree, "rowSeparator");
    if (!self._rowSeparator) { self._rowSeparator = '\n'; }
    
    self._select = document.createElement("select");
    self._select.setAttribute("size", "10");
    
    self._domElement.appendChild(self._select);
    
    var currentChangedCommandTree = mlabGetMDLChild(self._mdlTree, "currentChangedCommand");
    if (currentChangedCommandTree) {
      self._currentChangedCommand = currentChangedCommandTree.value;
      self._select.onchange = self.selectionChanged;
    }

    self.fieldChanged(self._field);
  };
  
  this.fieldChanged = function(field) {
    try {
      while (self._select.length > 0) {
        self._select.remove(0);
      }
      var items = field.getValue().split(self._rowSeparator);
      for (var i=0; i<items.length; i++) {
        var option = document.createElement("option");
        option.innerHTML = items[i];
        self._select.add(option, null);
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
  
  this.selectionChanged = function(event) {
    try {
      if (self._select.selectedIndex < self._select.length) {
        var arguments = [self._currentChangedCommand,
                         {"texts": [self._select.options[self._select.selectedIndex].value]}];
        self._moduleContext.sendGenericRequest("handleRemoteListViewCurrentChanged", arguments);
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
}

//=============================================================================
// MLABButtonControl
//=============================================================================
function MLABButtonControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupButtonControl = function(parentControl) {
    self.setupWidgetControl("MLABButtonControl", parentControl);
   
    var imageUrl = null;
    var imageTree = mlabGetMDLChild(self._mdlTree, "image");
    if (imageTree) {
      imageUrl = mlabTranslatePath(imageTree.value);
    }
    
    var title = null;
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      title = titleTree.value;
    } else {
      title = self._field.getName();
    }
    
    self._button = document.createElement("button");
    self._domElement.appendChild(self._button);
    
    if (title) {
      self._button.innerHTML = title;
    }
    if (imageUrl) {
      var img = document.createElement("image");
      img.setAttribute("src", imageUrl);
      self._button.appendChild(img);
    }
    
    var commandTree = mlabGetMDLChild(self._mdlTree, "command");
    if (commandTree) {
      self._command = commandTree.value;
    } else {
      self._command = null;
    }
    
    self._button.onclick = self._onButtonClick; 
  };
  
  this._onButtonClick = function() {
    if (self._command) {
      self._moduleContext.sendGenericRequest(self._command, []);
    }
  };
}

//=============================================================================
// MLABSliderControl
//=============================================================================
function MLABSliderControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupSliderControl = function(parentControl) {
    self.setupWidgetControl("MLABSliderControl", parentControl);
   
    var title = null;
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      title = titleTree.value;
    }
    
    self._slider = document.createElement("div");
    self._domElement.appendChild(self._slider);
    
    if (title) {
      self._slider.innerHTML = title;
    }
    
    var commandTree = mlabGetMDLChild(self._mdlTree, "command");
    if (commandTree) {
      self._command = commandTree.value;
    } else {
      self._command = null;
    }
    
  };
  
  this.fieldChanged = function(field) {
    //console.log(field.value);
  };
}


//=============================================================================
// MLABCheckBoxControl
//=============================================================================
function MLABCheckBoxControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupCheckBoxControl = function(parentControl) {
    self.setupWidgetControl("MLABCheckBoxControl", parentControl);
   
    var title = null;
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      title = titleTree.value;
    }
    
    self._checkbox = document.createElement("div");
    self._domElement.appendChild(self._checkbox);
    
    if (title) {
      self._checkbox.innerHTML = title;
    }
    
    var commandTree = mlabGetMDLChild(self._mdlTree, "command");
    if (commandTree) {
      self._command = commandTree.value;
    } else {
      self._command = null;
    }
    
  };
  
  this.fieldChanged = function(field) {
    //console.log(field.value);
  };
}


//=============================================================================
// MLABComboBoxControl
//=============================================================================
function MLABComboBoxControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupComboBoxControl = function(parentControl) {
    self.setupWidgetControl("MLABComboBoxControl", parentControl);
    
    self._select = document.createElement("select");
    self._select.setAttribute("size", "1");
    self._select.onchange = self.selectionChanged;

    self._domElement.appendChild(self._select);
    
    var activatedCommandTree = mlabGetMDLChild(self._mdlTree, "activatedCommand");
    if (activatedCommandTree) {
      self._activatedCommand = activatedCommandTree.value;
    } else {
      self._activatedCommand = null;
    }
    
    var comboFieldTree = mlabGetMDLChild(self._mdlTree, "comboField");
    if (comboFieldTree) {
      var separatorTree = mlabGetMDLChild(self._mdlTree, "comboSeparator");
      if (separatorTree) {
        self._comboSeparator = separatorTree.value;
      } else {
        self._comboSeparator = ",";
      }
      self._comboField = self._ctx.lookupField(comboFieldTree.value);
      if (self._comboField != null) {
        self._comboField.addListener(self);
        self.fieldChanged(self._comboField);
      } else {
        self._moduleContext.logError("comboField not found: " + comboFieldTree.value);
      }
      self._useItems = false;
    } else {
      self._useItems = true;
    }
    
    if (self._useItems) {
      var items = mlabGetMDLChild(self._mdlTree, "items");
      if (items) {
        // TODO: setup from items ...
        var items = [];
        self._setupItems(items);
      } else {
        self._moduleContext.logError("MLABComboBoxControl: no comboField nor combobox items given");
      }
    }

    // TODO: enum field support is not implemented!
    if (self._field) {
      self.fieldChanged(self._field);
    }
  };
  
  this._setupItems = function(items) {
    while (self._select.length > 0) {
      self._select.remove(0);
    }
    for (var i=0; i<items.length; i++) {
      var option = document.createElement("option");
      option.innerHTML = items[i];
      self._select.add(option, null);
    }
  };
  
  this.fieldChanged = function(field) {
    try {
      var value = field.getValue();
      if (typeof(value) != 'undefined') {
        if (field == self._comboField) {
          var items = value.split(self._comboSeparator);
          self._setupItems(items);
        } else if (field == self._field) {
          var optionToSelect = null;
          for (i=0; i<self._select.options.length; i++) {
            var o = self._select.options[i];
            if (o.text != value) {
              o.selected = false;
            } else {
              optionToSelect = o;
            }
          }
          if (optionToSelect) {
            optionToSelect.selected = true;
          }
        }
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
  
  this.selectionChanged = function(event) {
    try {
      if (self._select.selectedIndex < self._select.length) {
        var currentItem = self._select.options[self._select.selectedIndex].value;
        if (self._field) {
          self._field.setValue(currentItem);
        }
        if (self._activatedCommand) {
          var arguments = [self._activatedCommand, currentItem];
          self._moduleContext.sendGenericRequest("handleRemoteComboBoxItemActivated", arguments);
        }
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
}


//=============================================================================
// MLABLabelControl
//=============================================================================
function MLABLabelControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupLabelControl = function(parentControl) {
    self.setupWidgetControl("MLABLabelControl", parentControl);
    
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      self._domElement.innerHTML = titleTree.value;
    }
  };
  
  this.fieldChanged = function(field) {
    self._domElement.innerHTML = field.getValue();
  };
}


//=============================================================================
// MLABVerticalControl
//=============================================================================
function MLABVerticalControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABHorizontalControl;
  this.inheritFrom(mdlTree, moduleContext, moduleContext);
  
  this.setup = this.setupVerticalControl = function(parentControl) {
    self.setupWidgetControl("MLABVerticalControl", parentControl);
    
    self._table = document.createElement("table");
    self._domElement.appendChild(self._table);
  };
  
  // overwrite setupChildren() to set the minimum size for the first column
  this._setupChildrenHorizontalControl = this.setupChildren;
  this.setupChildren = function() {
    self._setupChildrenHorizontalControl();
    
    var firstColumnWidth = 0;
    for (var i=0; i<self._table.rows.length; i++) {
      var cell = self._table.rows[i].cells[0];
      if ((cell.getAttribute("colspan") == null) && (cell.children.length > 0)) {
        var w = cell.children[0].offsetWidth;
        if (w > firstColumnWidth) { firstColumnWidth = w; }
      }
    }
    for (var i=0; i<self._table.rows.length; i++) {
      var cell = self._table.rows[i].cells[0];
      if (cell.getAttribute("colspan") == null) {
        cell.style.width = firstColumnWidth;
      }
    }
  };
  
  // overwrite appendChild() to insert each child in a new row. 
  // field controls are specially added to the table, so that they get aligned.
  this.appendChild = function(child) {
    if (self._table.rows.length > 0) {
      // set the bottom padding of the previous row to emulate spacing
      self._table.rows[self._table.rows.length-1].cells[0].style.paddingBottom = self._spacing + "px";
    }
    var tableRow = self._table.insertRow(-1);
    var tableCell = tableRow.insertCell(0);
    if (child.isFieldControl()) {
      child._fieldDomElement.style.display = "inline";
      tableCell.appendChild(child._fieldDomElement);
      self._setTableCellAttributes(child, tableCell);
      tableCell = tableRow.insertCell(0);
      if (child._labelDomElement) {
        child._labelDomElement.style.display = "inline";
        tableCell.appendChild(child._labelDomElement);
      }
      self._setTableCellAttributes(child, tableCell);
      
    } else {
      tableCell.setAttribute("colspan", "2");
      tableCell.appendChild(child._domElement);
      self._setTableCellAttributes(child, tableCell);
    }
  };
}


//=============================================================================
// MLABWindowControl
//=============================================================================
function MLABWindowControl(mdlTree, moduleContext) {
  var self = this;

  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);

  this.setup = this.setupWindowControl = function(parentControl) {
    self.setupWidgetControl("MLABWindowControl", parentControl);
  }; 
  
  // Can be overriden by framework implementation to issue commands after window is build in html
  this.setupFinished = function() {};
}


//=============================================================================
// MLABWidgetControlFactory
//=============================================================================
function MLABWidgetControlFactory(moduleContext) {
  var self = this;
  
  this._moduleContext = moduleContext;

  this.controls = new Object();

  this.getControl = function(controlName) {
    var c = self.controls[controlName];
    if (c != 'undefined') {
      return c;
    }
    return null;
  };

  this.createWindow = function(mdlTree) {
    if (mdlTree.name == "Window") {
      var c = self.createControl(mdlTree);
      if (c) {
        try {
          c.setup(null);
          c.setupTypicalTags();
          var parentDiv = null;
          if (mdlTree.value.length > 0) {
            parentDiv = document.getElementById("Window_" + mdlTree.value);
          }
          if (!parentDiv) { parentDiv = self._moduleContext.getDiv(); }
          parentDiv.appendChild(c._domElement);
          c.setupChildren();
          c.setupFinished();
        } catch(e) {
          self._moduleContext.logError("Failed to setup window control, see exception below");
          self._moduleContext.logException(e);
        }
      } else {
        self._moduleContext.logError("The framework does not provide an MDL Window control");
      }
    } else {
      self._moduleContext.logError('MDL tree is no window: "' + mdlTree.name + '"');
    }
  };

  this.createControl = function(mdlTree) {
    var c = self.getControl(mdlTree.name);
    if (c) {
      try {
        return new c(mdlTree, self._moduleContext);
      } catch (e) {
        self._moduleContext.logError("Failed to create widget control: " + mdlTree.name + ", see exception below");
        self._moduleContext.logException(e);
      }
    }
    // else do not issue an error, because the tree may not be a widget control,
    // but an attribute. the validator on the server has already verified the
    // mdl, so it must be ok.
    return null;
  };

  this.registerControl = function(controlName, control) {
    if (self.getControl(controlName) == null) {
      self.controls[controlName] = control;
    } else {
      self._moduleContext.logError('Failed to register control "' + controlName + '": ' +
                                   'another control with the same name was already registered');
    }
  };
}
