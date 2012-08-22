//=============================================================================
// MLABField
//=============================================================================
function MLABField(name, type, options, moduleContext) {
  var self = this;
  
  this._moduleContext = moduleContext;
  this._name = name;
  this._type = type;
  this._options = options;
  this._value = '';
  this._listeners = new Array();
  this._valueSetStartTime = null;
  
  this.getType = function() { return self._type; }
  this.getOptions = function() { return self._options; }  
  this.getValue = function() { return self._value; }
  this.getName = function() { return self._name; }
  
  this.isBaseField = function() { return false; };
  this.isBoolField = function() { return false; };
  this.isColorField = function() { return false; };
  this.isDoubleField = function() { return false; };
  this.isEnumField = function() { return false; };
  this.isFloatField = function() { return false; };
  this.isIntegerField = function() { return false; };
  this.isMatrixField = function() { return false; }
  this.isNumberField = function() { return false; }
  this.isStringField = function() { return false; };
  this.isTriggerField = function() { return false; };
  this.isVectorField = function() { return false; };  
    
  this.addListener = function(listener) {
    if (listener) {
      self._listeners.push(listener);
    } else {
      mlabThrowException("MLABField.addListener: invalid field listener given: " + listener);
    }
  };
  
  this.setValue = function(value) {
    if (gApp.isFieldSyncronizationProfilingEnabled()) {
      self._valueSetStartTime = (new Date()).getTime();
    }
    // update the value and notfiy all client side field listeners,
    // because the server does not send another MLABModuleSetFieldValuesMessage.
    self.updateValue(value, true);
    var m = new MLABModuleSetFieldValuesMessage();
    m.setFieldData([[self._name, value, self._options]]);
    self._moduleContext.sendMessage(m);
  };

  this.updateValue = function(newValue, disableProfiling) {
    if (!disableProfiling && self._valueSetStartTime != null) {
      var d = new Date();
      self._moduleContext.log("Field sync time (" + self._name + " [" + self._type + "]" +
                              ", '" + self._value + "' - > '" + newValue + "'): " +
                              (d.getTime()-self._valueSetStartTime) + "ms");
      self._valueSetStartTime = null;
    }
    self._value = newValue;
    for (var i=0; i<self._listeners.length; i++) {
      try {
        self._listeners[i].fieldChanged(self);
      } catch (e) {
        self._moduleContext.logException(e);
      }
    }
  };
};


//=============================================================================
// MLABBaseField
//=============================================================================
function MLABBaseField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this._value = null;
  
  this._handler = null;

  this.isBaseField = function() { return true; };
}


//=============================================================================
// MLABBoolField
//=============================================================================
function MLABBoolField(name, type, options, moduleContext) {
  var self = this;

  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isBoolField = function() { return true; };
  
  this.getBoolValue = function() { 
    return mlabIsTrue(self._value.toLowerCase()); 
  };
  
  this.setBoolValue = function(flag) { 
    self.setValue(flag ? "TRUE" : "FALSE"); 
  };
}


//=============================================================================
// MLABColorField
//=============================================================================
function MLABColorField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isColorField = function() { return true; };
}


//=============================================================================
// MLABDoubleField
//=============================================================================
function MLABDoubleField(name, type, options, moduleContext) {
  var self = this;

  this.inheritFrom = MLABNumberField;
  this.inheritFrom(name, type, options, moduleContext);

  this.isDoubleField = function() { return true; };
}


//=============================================================================
// MLABEnumField
//=============================================================================
function MLABEnumField(name, type, options, moduleContext) {
  var self = this;
  
  this._items = [];  
  
  (function() {
    var l = type.split(",");
    if (l.length > 0) {
      if (l.length == 1) {
        // remove 'Enum(' and trailing ')' from item
        self._items.push(l[0].substr(5, l[0].length-6));
      } else {
        // remove 'Enum(' from first item
        self._items.push(l[0].substr(5));
        // add all other items except the last one
        if (l.length > 2) {
          for (var i=1; i<l.length-1; i++) {
            self._items.push(l[i]);
          }
        }
        // remove tailing ')' from last item
        var s = l[l.length-1];
        self._items.push(s.substr(0, s.length-1))
      }
    }
  }());
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, 'Enum', options, moduleContext);
  
  this.isEnumField = function() { return true; };  
  this.items = function() { return self._items; };  
  this.setCurrentItem = function(item) { self.setValue(item); };
}


//=============================================================================
// MLABFloatField
//=============================================================================
function MLABFloatField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABNumberField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isFloatField = function() { return true; };
}


//=============================================================================
// MLABIntegerField
//=============================================================================
function MLABIntegerField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABNumberField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isIntegerField = function() { return true; };
}


//=============================================================================
// MLABMatrixField
//=============================================================================
function MLABMatrixField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isMatrixField = function() { return true; };
}


//=============================================================================
// MLABNumberField
//=============================================================================
function MLABNumberField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this._maxValue = 0;
  this._minValue = 0;  
  this.getMaxValue = function() { return self._maxValue; }
  this.getMinValue = function() { return self._minValue; }  
  this.setMaxValue = function(value) { self._maxValue = value; }
  this.setMinValue = function(value) { self._minValue = value; }
  
  this.isNumberField = function() { return true; };
}


//=============================================================================
// MLABStringField
//=============================================================================
function MLABStringField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isStringField = function() { return true; };
}


//=============================================================================
// MLABTriggerField
//=============================================================================
function MLABTriggerField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isTriggerField = function() { return true; };
  
  this.trigger = function() { self.setValue(""); }
}


//=============================================================================
// MLABVectorField
//=============================================================================
function MLABVectorField(name, type, options, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABField;
  this.inheritFrom(name, type, options, moduleContext);
  
  this.isVectorField = function() { return true; };
}


//=============================================================================
// MLABModule
//=============================================================================
function MLABModule(name, moduleContext) {
  var self = this;
  
  this._moduleContext = moduleContext;  
  this._name = name;
  this._inputFields = new Object();
  this._outputFields = new Object();
  this._parameterFields = new Object();
  
  this.getName = function() { return self._name; };
  
  this._createField = function(name, type, flags) {
    var f = null;
    switch (type) {    
    case 'Bool':    f = new MLABBoolField(name, type, flags, self._moduleContext); break;
    case 'Color':   f = new MLABColorField(name, type, flags, self._moduleContext); break;
    case 'Double':  f = new MLABDoubleField(name, type, flags, self._moduleContext); break;
    case 'Float':   f = new MLABFloatField(name, type, flags, self._moduleContext); break;
    case 'Integer': f = new MLABIntegerField(name, type, flags, self._moduleContext); break;
    case 'Matrix':  f = new MLABMatrixField(name, type, flags, self._moduleContext); break;
    case 'MLBase':  f = new MLABBaseField(name, type, flags, self._moduleContext); break;
    case 'String':  f = new MLABStringField(name, type, flags, self._moduleContext); break;
    case 'Trigger': f = new MLABTriggerField(name, type, flags, self._moduleContext); break;
    case 'Vector2':
    case 'Vector3':
    case 'Vector4':
      f = new MLABVectorField(name, type, flags, self._moduleContext); 
      break;
      
    default:
      if (type.indexOf('Enum') == 0) {
        // special handling of the enum type string, which includes the enum items in brackets 
        f = new MLABEnumField(name, type, flags, self._moduleContext);
      } else {
        self._moduleContext.logError("MLABModule._createField: unhandled field type " + type);
        f = new MLABField(name, type, flags, self._moduleContext);
      }
    }
    return f;
  };
  
  this.setup = function(message) {
    for (var i=0; i<message.fieldData.length; i++) {
      var fData = message.fieldData[i];
      var flags = fData[2];
      var field = self._createField(fData[0], fData[1], flags);
      // these constants are defined in class MessageModuleInfo in mlabRemoteModuleMessages.h
      if (flags & 1) {
        self._inputFields[field.getName()] = field;
      }
      if (flags & 2) {
        self._outputFields[field.getName()] = field;
      }
      if (!((flags & 1) || (flags & 2))) {
        self._parameterFields[field.getName()] = field;
      }
    }
  };
  
  this.lookupField = function(fieldName) {
    // try to keep the same semantics as MLABModule::lookupField() in mlabModule.cpp here
    var f = null;
    if (fieldName in self._parameterFields) {
      f = self._parameterFields[fieldName];
    } else if (fieldName in self._inputFields) {
      f = self._inputFields[fieldName];
    } else if (fieldName in self._outputFields) {
      f = self._outputFields[fieldName];
    } 
    return f;
  };
  
  this.getFieldValue = function(fieldName) {
    var value = '';
    var f = lookupField(fieldName);
    if (f != null) {
      value = f.getValue();
    } else {
      self._moduleContext.logError("MLABModule.getFieldValue: no such field found: " + fieldName);
    }
    return value;
  };
  
  this.setFieldValue = function(fieldName, value) {
    var f = self.lookupField(fieldName);
    if (f) {
      var data = [[fieldName, value, 0]];
      var msg = new MLABModuleSetFieldValuesMessage();
      msg.setFieldData(data);
      self._moduleContext.sendMessage(msg);
    } else {
      self._moduleContext.logError("MLABModule.setFieldValue: no such field found: " + fieldName);
    }
  };

  this.updateFieldValues = function(message) {
    for (var i=0; i<message.fieldData.length; i++) {
      var fData = message.fieldData[i];
      var f = self.lookupField(fData[0]);
      if (f) {
        f.updateValue(fData[1]);
      } else {
        self._moduleContext.logError("MLABModule.updateFieldValues: no such field found: " + fData[0]);
      }
    }
  };
  /*
  this.registerFieldListener = function(fieldName, fieldListener) {
    var f = self.getField(fieldName);
    if (f) {
      f.addListener(fieldListener);
    } else {
      self._moduleContext.logError("MLABModule.registerFieldListener: no such field found: " + fieldName);
    }
  };*/
  
  // parse the interface, e.g. for getting min and max values of parameter fields
  this.parseInterface = function(mdlTree) {
    var parameters = mlabGetMDLChild(mdlTree, "Parameters");
    if (parameters && parameters.children) {
      for (var i=0; i<parameters.children.length; i++) {
        var fieldTree = parameters.children[i];
        if (fieldTree.name != "Field") { continue; }        
        var field = self.lookupField(fieldTree.value);
        if (field) {
          var maxTree = mlabGetMDLChild(fieldTree, "max");
          var minTree = mlabGetMDLChild(fieldTree, "min");
          if (field.isNumberField()) {
            if (field.isIntegerField()) {
              if (maxTree) { field.setMaxValue(parseInt(maxTree.value)); }
              if (minTree) { field.setMinValue(parseInt(minTree.value)); }
            } else {
              if (maxTree) { field.setMaxValue(parseFloat(maxTree.value)); }
              if (minTree) { field.setMinValue(parseFloat(minTree.value)); }
            }
          }
        } else {
          self._moduleContext.logError("MLABModule.parseInterface: field not found: " + fieldTree.value);
        }
      }
    }
  };
}


//=============================================================================
// Module context state ids
//=============================================================================
MLAB_MCSTATE_UNINITIALIZED = 0;
MLAB_MCSTATE_MODULE_CREATING_MODULE = 1;
MLAB_MCSTATE_ADDING_RENDERING_SLAVE = 2;
MLAB_MCSTATE_INITIALIZED = 3;


//=============================================================================
// MCState - base classe for module context states
//=============================================================================
function MCState(name, moduleContext) {
  var self = this;
  this._moduleContext = moduleContext;
  this._name = name;
  
  this.is = function(name) { return self._name == name; };
  
  this.handleMessageAndGetNextState = function(message) {
    switch (message.type) {
      case MLAB_MSG_MODULE_LOG_MESSAGE:
        gApp.appendDiagnosisMessage(message.message);
        break;
        
      case MLAB_MSG_MODULE_SET_FIELD_VALUES:
        self._moduleContext._module.updateFieldValues(message);
        break;
        
      default:
        self._moduleContext.logError("MCState '" + self._name + "' does not know how to handle message " + mlabGetMessageTypeName(message.type));
    }
    return null;
  };
  
  // duplicate function to be used in derived classes that overwrite handleMessageAndGetNextState()
  this.mcStateHandleMessageAndGetNextState = this.handleMessageAndGetNextState; 
}


//=============================================================================
// MCStateUninitialized - the initial module context state
//=============================================================================
function MCStateUninitialized(moduleContext) {
  var self = this;
  this.inheritFrom = MCState;
  this.inheritFrom("MCStateUninitialized", moduleContext);
}


//=============================================================================
// MCStateCreatingModule - the module context is creating the module
//=============================================================================
function MCStateCreatingModule(moduleContext) {
  var self = this;
  this.inheritFrom = MCState;
  this.inheritFrom("MCStateCreatingModule", moduleContext);
  
  this.handleMessageAndGetNextState = function(message) {
    var nextState = null;    
    switch (message.type) {
      case MLAB_MSG_MODULE_INFO:      
        if (message.status == 0) {
         // status == 0 means successful module creation
          nextState = new MCStateModuleReady(self._moduleContext);
        } else if (message.status == 4) {
          // status == 4 means authentication failed
          nextState = new MCStateUnauthenticated(self._moduleContext);
        } else {
          nextState = new MCStateFailedToCreateModule(self._moduleContext);
        }
        break;
        
      case MLAB_MSG_MODULE_PROCESS_INFORMATION:
        // this message is currently not handled
        break;

      default:
        nextState = self.mcStateHandleMessageAndGetNextState(message);
    }    
    return nextState;
  };
}


//=============================================================================
// MCStateAddPendingBaseFieldMessages - base class for states that add 
// base field as pending messages to the module context. The messages will
// be handled later when the rendering controls of the base fields are ready.
// TODO: base field messages for fields without rendering control are currently
// stored and not handled.
//=============================================================================
function MCStateAddPendingBaseFieldMessages(name, moduleContext) {
  var self = this;
  this.inheritFrom = MCState;
  this.inheritFrom(name, moduleContext);
  
  this.handleMessageAndGetNextState = function(message) {
    var mc = self._moduleContext;
    
    switch (message.type) {
      case MLAB_MSG_MODULE_BASE_FIELD_TYPE:
        mc._handleBaseFieldTypeMessage(message);
        break;
        
      case MLAB_MSG_ITEM_MODEL_ATTRIBUTES:
      case MLAB_MSG_ITEM_MODEL_ITEM_CHANGED:
      case MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED:
      case MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED:
      case MLAB_MSG_ITEM_MODEL_DATA_CHANGED:
      case MLAB_MSG_ITEM_MODEL_CHILDREN_DONE:
        // these messages are handled by a special handler:
        mc._handleBaseFieldHandlerMessage(message);

      case MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED:
      case MLAB_MSG_RENDERING_RENDERED_IMAGE:
      case MLAB_MSG_RENDERING_SET_SIZE_HINTS:
      case MLAB_MSG_RENDERING_SET_CURSOR_SHAPE:
        mc._addPendingBaseFieldMessage(message);
        break;
        
      default:
        self.mcStateHandleMessageAndGetNextState(message);
    }
  };
}


//=============================================================================
// MCStateModuleReady - the module context finished creating the module
//=============================================================================
function MCStateModuleReady(moduleContext) {
  var self = this;
  this.inheritFrom = MCStateAddPendingBaseFieldMessages;
  this.inheritFrom("MCStateModuleReady", moduleContext);
}


//=============================================================================
// MCStateMDLReady - the module context finished creating dom elements from
// the MDL panel of the module
//=============================================================================
function MCStateMDLReady(moduleContext) {
  var self = this;
  this.inheritFrom = MCStateAddPendingBaseFieldMessages;
  this.inheritFrom("MCStateMDLReady", moduleContext);
}


//=============================================================================
// MCStateUnauthenticated - the module context failed to create the module,
// because it did not provide the authentication data, or the provided 
// authentication data was invalid
//=============================================================================
function MCStateUnauthenticated(moduleContext) {
  var self = this;
  this.inheritFrom = MCState;
  this.inheritFrom("MCStateUnauthenticated", moduleContext);
  
  this.handleMessageAndGetNextState = function(message) {
    var nextState = null;    
    switch (message.type) {
      case MLAB_MSG_MODULE_INFO:      
        if (message.status == 0) {
         // status == 0 means successful module creation
          nextState = new MCStateModuleReady(self._moduleContext);
        } else if (message.status == 4) {
          // status == 4 means authentication failed
          nextState = new MCStateUnauthenticated(self._moduleContext);
        } else {
          self._moduleContext.logError("MCStateUnauthenticated: received unexpected message status: " + message.status);
        }
        break;
        
      default:
        nextState = self.mcStateHandleMessageAndGetNextState(message);
    }    
    return nextState;
  };
}


//=============================================================================
// MCStateFailedToCreateModule - the module context failed to create the 
// module due to an error
//=============================================================================
function MCStateFailedToCreateModule(moduleContext) {
  var self = this;
  this.inheritFrom = MCState;
  this.inheritFrom("MCStateFailedToCreateModule", moduleContext);
}


//=============================================================================
// MCStateRenderingSlavesActivated - the module context activated the
// remote rendering slaves
//=============================================================================
function MCStateRenderingSlavesActivated(moduleContext) {
  var self = this;
  this.inheritFrom = MCState;
  this.inheritFrom("MCStateRenderingSlavesActivated", moduleContext);
  
  this.handleMessageAndGetNextState = function(message) {
    var mc = self._moduleContext;
    
    switch (message.type) {
      case MLAB_MSG_MODULE_BASE_FIELD_TYPE:
        mc._handleBaseFieldTypeMessage(message);
        break;
        
      case MLAB_MSG_ITEM_MODEL_ATTRIBUTES:
      case MLAB_MSG_ITEM_MODEL_ITEM_CHANGED:
      case MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED:
      case MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED:
      case MLAB_MSG_ITEM_MODEL_DATA_CHANGED:
      case MLAB_MSG_ITEM_MODEL_CHILDREN_DONE:
        // these messages are handled by a special handler:
        mc._handleBaseFieldHandlerMessage(message);
        break;
        
      case MLAB_MSG_RENDERING_RENDER_SCENE_CHANGED:
      case MLAB_MSG_RENDERING_RENDERED_IMAGE:
      case MLAB_MSG_RENDERING_SET_CURSOR_SHAPE:
      case MLAB_MSG_RENDERING_SET_SIZE_HINTS:
        mc._handleBaseFieldMessage(message);
        break;
      
      default:
        self.mcStateHandleMessageAndGetNextState(message);
    }
  };
}


//=============================================================================
// MLABModuleContext - the module context creates a MLABRemoteManager instance
// that provides a web socket to communicate with a MeVisLab instance on the 
// server. It triggers the creation of the module that is specified in the 
// moduleDiv class attribute and creates dom elements from the modules MDL#
// panel.
//=============================================================================
function MLABModuleContext(moduleDiv, id, requiresLogin) {
  var self = this;
  
  this._id = id;
  this._div = moduleDiv;
  this._moduleName = moduleDiv.getAttribute("class");
  this._module = null;
  this._moduleReady = false;
  this._remoteRenderingControlMap = new Object();
  this._baseFieldControlMap = new Object();
  this._widgetControlFactory = new MLABWidgetControlFactory(this);
  this._requiresLogin = requiresLogin;
  this._remainingReconnects = 3
  
  this._isBodyVisible = false;
  this._state = new MCStateUninitialized(this);
    
  this.getId = function() { return self._id; }
  this.getDiv = function() { return self._div; };
  this.getModule = function() { return self._module; };
  
  this.showIDE = function() {
    self.sendGenericRequest("handleShowIDERequest", []);
  };
  
  this.setModuleContextReadyCallback = function(callback) {
    self._moduleReadyCallback = callback;
  };
  
  this.setModuleWindowCreatedCallback = function(callback) {
    self._moduleWindowCreatedCallback = callback;
  };
  
  this.createControl = function(mdlTree) {
    return self._widgetControlFactory.createControl(mdlTree);
  };
  
  this.registerWidgetControl = function(name, control) {
    self._widgetControlFactory.registerControl(name, control);
  };
  
  this.getRemoteRenderingControl = function(domElement) {
    for (var baseName in self._remoteRenderingControlMap) {
      var control = self._remoteRenderingControlMap[baseName];
      if (control.getViewport() == domElement) { return control; }
    }
    return null;
  };
  
  this.registerBaseFieldControl = function(baseName, control) {
    if (!(baseName in self._baseFieldControlMap)) {
      self._baseFieldControlMap[baseName] = control;
    }
    self._flushPendingBaseFieldMessages(control, baseName);
  };
  
  this.registerRemoteRenderingControl = function(baseName, control) {
    var map = self._remoteRenderingControlMap;
    if (!(baseName in map)) {
      map[baseName] = control;
      self._flushPendingBaseFieldMessages(control, baseName);
      if (self._state.is("MCStateRenderingSlavesActivated")) { 
        control.activateRenderingSlave(); 
      }
    } else {
      self.logError("A control for this base field exists already: " + baseName);
    }
  };
  
  this._addPendingBaseFieldMessage = function(message) {
    if (!self._pendingBaseFieldMessages) { self._pendingBaseFieldMessages = {}; }
    var map = self._pendingBaseFieldMessages;
    if (!(message.baseField in map)) { map[message.baseField] = []; }
    map[message.baseField].push(message);
    if (map[message.baseField].length > 20) {
      self.logError("More than 20 pending base field messages exist: " + message.baseField);
    }
    //if (console) {
    //  console.log("Pending base field message: " + message.type + ", " + message.baseField);
    //}
  };
  
  this._handleBaseFieldTypeMessage = function(message) {
    var baseField = self._module.lookupField(message.baseField);
    if (!baseField.isBaseField()) {
      baseField = null;
      // TODO: error message
    }
    if (message.baseType == "AbstractItemModel") {
      // create handler in base field
      baseField._handler = new MLABItemModelHandler(baseField, message.baseGeneration);
    } else if (message.baseType == "RemoteRendering") {
      // send desired quality settings for this base field:  
      var m = new MLABRenderingSetStreamingQualityMessage();
      m.setData(message.baseField, message.baseGeneration, gApp.getRenderQualitySettings());
      self.sendMessage(m);
  
      // remote rendering messages are handled differently:
      self._handleBaseFieldMessage(message);
    }
  }
  
  this._handleBaseFieldHandlerMessage = function(message) {
    var baseField = self._module.lookupField(message.baseField);
    var handler = null;
    if (baseField.isBaseField()) {
      handler = baseField._handler;
    }
    if (handler) {
      // no need to check the Base generation, since it can only be changed by the master
      handler.handleMessage(message);
    } else {
      // TODO: error message
    }
  }
  
  this._handleBaseFieldMessage = function(message) {
    var map = self._remoteRenderingControlMap;
    if (message.baseField in map) {
      map[message.baseField].handleBaseFieldMessage(message);
    } else if (message.baseField in self._baseFieldControlMap) {
      self._baseFieldControlMap[message.baseField].handleBaseFieldMessage(message);
    } else {
      self._addPendingBaseFieldMessage(message);
    }
  };
  
  this._flushPendingBaseFieldMessages = function(control, baseField) {
    var map = self._pendingBaseFieldMessages;
    if (map && (baseField in map)) {
      var l = map[baseField];      
      for (var i=0; i<l.length; i++) { control.handleBaseFieldMessage(l[i]); }
      delete map[baseField];
    }
  };

  this._flushPendingRemoteManagerLogs = function() {
    var formatAsHTML = gApp.showDiagnosisPanel();
    var l = self._pendingLogs;
    if (l) {
      for (var i=0; i<l.length; i++) {
        self._remoteManager.log(self._moduleName, l[i], formatAsHTML);
      }
    }
    l = self._pendingLogErrors;
    if (l) {
      for (var i=0; i<l.length; i++) {
        self._remoteManager.logError(self._moduleName, l[i], formatAsHTML);
      }
    }
    l = self._pendingLogExceptions;
    if (l) {
      for (var i=0; i<l.length; i++) {
        self._remoteManager.logException(self._moduleName, l[i], formatAsHTML);
      }
    }
  };
  
  this.handleConnected = function() {
    self.changeState(new MCStateCreatingModule(self));
    
    self._module = new MLABModule(self._moduleName, self);
    var message = new MLABModuleCreateMessage();
    message.setData(self._module.getName());
    self._remoteManager.sendMessage(message);
  };
  
  this.authenticate = function() {
    var message = new MLABModuleSetFieldValuesMessage();
    var d = gApp.getAuthentication();
    message.setFieldData([["user", d[0], 0], ["password", d[1], 0]]);
    self._remoteManager.sendMessage(message);
  };
  
  this.setBodyIsVisible = function() {
    self._isBodyVisible = true;
    if (self._state.is("MCStateMDLReady")) {
      self.changeState(new MCStateRenderingSlavesActivated(self));
    }
  };
  
  this.handleMessage = function(message) {
    if (parseInt(message.type) < 1020 || parseInt(message.type) > 1049) {
     // console.log("handling message: " + mlabGetMessageTypeName(message.type))
    }
    var nextState = self._state.handleMessageAndGetNextState(message);
    if (nextState != null) { self.changeState(nextState, message); }
  };
  
  this.changeState = function(newState, message) {
    self._state = newState;
    
    switch (newState._name) {
      case "MCStateModuleReady":
        self._module.setup(message);
        self._moduleReady = true;
        self._flushPendingRemoteManagerLogs();
        self.log("Module context ready.");
        self._notifyModuleReadyCallback(message.status);
        self.createWindows();
        break;
      
      case "MCStateCreatingModule":
        break;

      case "MCStateMDLReady":
        if (self._isBodyVisible) {
          self.changeState(new MCStateRenderingSlavesActivated(self));
        }
        break;

      case "MCStateUnauthenticated":
        self._requiresLogin = true;
        self._notifyModuleReadyCallback(message.status);
        break;
        
      case "MCStateRenderingSlavesActivated":
        self._activateRenderingSlaves();
        break;
        
      case "MCStateFailedToCreateModule":
        self.logError("Module status: " + message.status);
        self._notifyModuleReadyCallback(message.status);
        break;
        
      default:
        self.logError("Unhandled state: " + newState._name);
    }
  };
  
  this._activateRenderingSlaves = function() {
    for (var fieldName in self._remoteRenderingControlMap) {
      var control = self._remoteRenderingControlMap[fieldName];
      self._flushPendingBaseFieldMessages(control, fieldName);
      control.activateRenderingSlave();
    }
  };
  
  this.log = function(message) {
    if (self._moduleReady) {
      self._remoteManager.log(self._moduleName, message, /*formatAsHTML=*/gApp.showDiagnosisPanel());
    } else {
      if (!self._pendingLogs) { self._pendingLogs = []; }
      self._pendingLogs.push(message);
      //if (console) {
      //  console.log("Pending remote manager log: " + message);
      //}
    }
  };
  
  this.logError = function(message) {
    if (self._moduleReady) {
      self._remoteManager.logError(self._moduleName, message, /*formatAsHTML=*/gApp.showDiagnosisPanel()); 
    } else {
      if (!self._pendingLogErrors) { self._pendingLogErrors = []; }
      self._pendingLogErrors.push(message);
      if (console) {
        console.log("Pending remote manager log error: " + message);
      }
    }  
  };
  
  this.logException = function(message) {
    if (self._moduleReady) {
      self._remoteManager.logException(self._moduleName, message, /*formatAsHTML=*/gApp.showDiagnosisPanel());
    } else {
      if (!self._pendingLogExceptions) { self._pendingLogExceptions = []; }
      self._pendingLogExceptions.push(message);
      if (console) {
        console.log("Pending remote manager log exception: " + message);
      }
    }
  };

  this.disconnect = function() { self._remoteManager.close(); };

  this.getWebSocketPort = function(httpUrl) {
    var port = "4114";
    var request = new XMLHttpRequest();
    // do a synchronous request, because we need to know the web socket port now
    request.open("GET", httpUrl + "/Settings/webSocketPort", false);
    request.onreadystatechange = function() {
      if (request.readyState==4) {
        port = request.responseText;
      }
    };
    request.send(null);
    return port;
  };
  
  this.connect = function() {
    var hostname = gApp.getWebSocketHostName();
    if (!hostname) {
      hostname = window.location.hostname;
    }
    if (!hostname) {
      hostname = "127.0.0.1";
    }
    var port = gApp.getWebSocketPort();
    if (!port) {
      var httpUrl = window.location.protocol + "//" + hostname;
      var httpPort = window.location.port;
      if (httpPort) {
        httpUrl = httpUrl + ":" + httpPort;
      }
      port = self.getWebSocketPort(httpUrl);
    }
    var protocol = "ws://"
    if (window.location.protocol == "https:") {
      protocol = "wss://"
    }
    
    var socketUri = protocol + hostname + ":" + port + "/mevislab";
    try {
      self._remoteManager.close();
      self._remoteManager.setup(socketUri);
    } catch (e) {
      self.logException(e);
    }
  };
  
  this._notifyModuleReadyCallback = function(messageStatus) {
    if (self._moduleReadyCallback) { 
      self._moduleReadyCallback(self, messageStatus); 
    }
  };
  
  this.sendMessage = function(message) {
    self._remoteManager.sendMessage(message);
  };
  
  this.sendGenericRequest = function(functionName, arguments, responseHandler) {
    self._remoteManager.sendGenericRequest(functionName, arguments, responseHandler);
  };
  
  this.createWindows = function() {
    self.sendGenericRequest("handleRemoteMDLRequest", [], function(arguments) {
      try {
        var json = arguments[0];
        self._mdlTree = JSON.parse(json);
        var interfaceTree = mlabGetMDLChild(self._mdlTree, "Interface");
        self._module.parseInterface(interfaceTree);
        for (var i=0; i<self._mdlTree.children.length; i++) {
          var child = self._mdlTree.children[i];
          if (child.name == "Window") {
            var windowControl = self._widgetControlFactory.createWindow(child);
          }
        }
        self.log("Windows created.");
        
        self.changeState(new MCStateMDLReady(self));
        
        if (self._moduleWindowCreatedCallback) {
          self._moduleWindowCreatedCallback(self);
        }
      } catch (e) {
        self.logError("Failed to create window, see exception below.");
        self.logException(e);
      }
    });
  };
  
  this._remoteManager = new MLABRemoteManager();
  this._remoteManager.debugMessages = gApp.debugRemoteMessages(); 
  this._remoteManager.setConnectedCallback(self.handleConnected);
  this._remoteManager.setMessageReceivedCallback(self.handleMessage);
}
