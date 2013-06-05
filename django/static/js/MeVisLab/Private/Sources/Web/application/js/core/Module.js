/** \class MLAB.Core.Module(MLAB.Core.Object)
 * 
 * The Module class
 */
MLAB.Core.deriveClass("Module", MLAB.Core.Object, {
  Module: function(name, type) {
    MLAB.Core.Module.super.constructor.call(this)
    this.registerSignal("windowCreated")
    
    this._moduleContext = new MLAB.Core.ModuleContext(this)
    this._name = name
    this._type = type
    this._inputFields = new Object()
    this._outputFields = new Object()
    this._parameterFields = new Object()
    this._windowController = null
    this._mdlTree = null
  },
  
  setWindowController: function(windowController) {
    this._windowController = windowController
    this._windowController.setModule(this)
    this._windowController.connectSignal("windowCreated", this, "windowCreated")
  },
  
  getModuleContext: function() { return this._moduleContext },
  
  destroy: function() {
    this._windowController.destroy()
    this._inputFields = null
    this._outputFields = null
    this._parameterFields = null
    this._moduleContext.closeConnection()
    this._moduleContext = null
  },
  
  isWidgetControl: function(mdlTag) { return this._moduleContext.isWidgetControl(mdlTag) },
  
  /** \fn MLAB.Core.Module.control
   * 
   * Returns the first widget control with the given name. null is returned if none is found. 
   * 
   * \param controlName The control name.
   * \return An MLABWidgetControl instance or null if none was found.
   */
  control: function(controlName) { return this._windowController.control(controlName) },
  
  /** \fn MLAB.Core.Module.getMDLTree
   * 
   * Returns the MDL tree of this module, or null if it was not yet retrieved from the MeVisLab process.
   * 
   * \return The MDL tree or null. 
   */
  getMDLTree: function() { return this._mdlTree },
  
  /** \fn MLAB.Core.Module.setMDLTree
   * 
   * Sets the MDL tree. Do not call this function, it needs only to be called once by MLAB.Core.ModuleContext
   * and is part of the module initialization.
   * 
   * \param mdlTree The MDL tree for this module.
   */
  setMDLTree: function(mdlTree) { 
    this._mdlTree = mdlTree
    var interfaceTree = this._mdlTree.get("Interface")
    this._parseInterface(interfaceTree)
  },
  
  /** \fn MLAB.Core.Module.getInputFields
   * 
   * Returns the input fields.
   * 
   * \return The input fields as a list of fist.
   */
  getInputFields: function() { return this._inputFields },
  
  /** \fn MLAB.Core.Module.getParameterFields
   * 
   * Returns the parameter fields.
   * 
   * \return The parameter fields as a list of fist.
   */
  getParameterFields: function() { return this._parameterFields },
  
  /** \fn MLAB.Core.Module.getOutputFields
   * 
   * Returns the output fields.
   * 
   * \return The output fields as a list of fist.
   */
  getOutputFields: function() { return this._outputFields },
  
  /** \fn MLAB.Core.Module.getName
   * 
   * Returns the name of this module.
   * 
   * \return The name of this module.
   */
  getName: function() { return this._name },
  
  /** \fn MLAB.Core.Module.getType
   * 
   * Returns the type of this module.
   * 
   * \return The type of this module.
   */
  getType: function() { return this._type },
  
  /** \fn MLAB.Core.Module.createControl
   * 
   * Creates a control for the given MDL tree by calling MLABWindowController.createControl().
   * Returns the control or null if it could not be created.
   * 
   * \param mdlTree The MDL tree.
   */
  createControl: function(mdlTree) {
    return this._windowController.createControl(mdlTree)
  },
  
  /** \fn MLAB.Core.Module.sendMessage
   * 
   * Sends the message via the web socket connection to MeVisLab by calling MLAB.Core.ModuleContext.sendMessage().
   * 
   * \param message The message.
   */
  sendMessage: function(message) {
    this._moduleContext.sendMessage(message)
  },
  
  /** \fn MLAB.Core.Module.sendGenericRequest
   * 
   * Sends a generic request via the web socket connection to MeVisLab by calling MLAB.Core.ModuleContext.sendGenericRequest().
   * 
   * \see MLAB.Core.RemoteManager.sendGenericRequest()
   * 
   * \param functionName The script function that should be called in the module of the MeVisLab process.
   * \param arguments The arguments list for the function to be called.
   * \param responseHandler An optional callback function that is called if the reply to this request is received. 
   */
  sendGenericRequest: function(functionName, args, responseHandler) {
    this._moduleContext.sendGenericRequest(functionName, args, responseHandler)
  },
  
  /** \fn MLAB.Core.Module.sendBaseFieldMessage
   * 
   * Creates a base field message using the provided class and data and sends it to the module in
   * the MeVisLab process using MLAB.Core.ModuleContext.sendMessage().
   * 
   * \param baseFieldMessageClass The message class. See \ref RemoteMessages for possible messages.
   * \param data A mapping object containing the attributes that required by the message, e.g.: {pox_x: 10, pox_y: 52}
   */
  sendBaseFieldMessage: function(field, baseFieldMessage, data) {
    if (field.isBaseField()) {
      var m = new baseFieldMessage(field)
      m.setData(data)
      this._moduleContext.sendMessage(m)
    } else {
      MLAB.Core.throwException("Field is not a base field: " + field.getName() + ": " + field.getType())
    }
  },
  
  showDialog: function(windowName, windowContainer) {
    return this._windowController.showDialog(windowName, windowContainer)
  },
  
  /** \fn MLAB.Core.Module.createWindow
   * 
   * Calls MLABWindowController.createWindow() on the window controller instance. If
   * a window container is given, then the window control DOM element is appended to it.
   * 
   * \param windowName The optinal name of the window. If it is not given, then the default window is created. 
   * \param windowContainer Optional DOM element.
   * \return An MLABWindowControl instance, or null if it could not be created.
   */
  createWindow: function(windowName, windowContainer) {
    return this._windowController.createWindow(windowName, windowContainer)
  },
  
  createPanel: function(windowName, windowContainer) {
    return this._windowController.createPanel(windowName, windowContainer)
  },
  
  showPanel: function(windowName, windowContainer) {
    return this._windowController.showPanel(windowName, windowContainer)
  },
  
  hidePanel: function(windowName) {
    return this._windowController.hidePanel(windowName)
  },
  
  /** \fn MLAB.Core.Module.showWindow
   * 
   * Calls MLABWindowController.showWindow() on the window controller instance. If
   * a window container is given, then the window control DOM element is appended to it.
   * 
   * \param windowName The optional name of the window. If it is not given, then the default window is shown. 
   * \param windowContainer Optional DOM element. If the window needs to be created it is appended to it.
   * \return An MLABWindowControl instance, or null if it could not be created.
   */
  showWindow: function(windowName, windowContainer) {
    return this._windowController.showWindow(windowName, windowContainer)
  },
  
  hideWindow: function(windowName) {
    this._windowController.hideWindow(windowName)
  },
  
  getWindow: function(windowName) {
    return this._windowController.getWindow(windowName) 
  },
  
  /** \fn MLAB.Core.Module.showIDE
   * 
   * Shows the MeVisLab IDE on the server for this module.
   * 
   * \ingroup Debugging
   */
  showIDE: function() {
    this.getModuleContext().showIDE()
  },
  
  /** \fn MLAB.Core.Module._createAndAddField
   * 
   * Creates a field from the given arguments. The arguments are usually taken from the data
   * of the MLAB.Core.ModuleInfoMessage.
   * 
   * \param name The field name string.
   * \param type The field type string.
   * \param flags 
   */
  _createAndAddField: function(name, type, flags, fieldMap) {
    if (name in fieldMap) {
      MLAB.Core.throwException("A field with the same name has already been added: " + name)
    }
    
    var f = null
    switch (type) {    
    case 'Bool':    f = new MLAB.Core.BoolField(); break
    case 'Color':   f = new MLAB.Core.ColorField(); break
    case 'Double':  f = new MLAB.Core.DoubleField(); break
    case 'Float':   f = new MLAB.Core.FloatField(); break
    case 'Integer': f = new MLAB.Core.IntegerField(); break
    case 'Matrix':  f = new MLAB.Core.MatrixField(); break
    case 'MLBase':  f = new MLAB.Core.BaseField(); break
    case 'String':  f = new MLAB.Core.StringField(); break
    case 'Trigger': f = new MLAB.Core.TriggerField(); break
    case 'Vector2':
    case 'Vector3':
    case 'Vector4':
      f = new MLAB.Core.VectorField()
      break
      
    default:
      if (type.indexOf('Enum') === 0) {
        // special handling of the enum type string, which includes the enum items in brackets 
        f = new MLAB.Core.EnumField()
        ;(function() {
          var items = []
          var l = type.split(",")
          if (l.length > 0) {
            if (l.length === 1) {
              // remove 'Enum(' and trailing ')' from item
              items.push(new MLAB.Core.EnumItem(l[0].substr(5, l[0].length-6)))
            } else {
              // remove 'Enum(' from first item
              items.push(new MLAB.Core.EnumItem(l[0].substr(5)))
              // add all other items except the last one
              if (l.length > 2) {
                for (var i=1; i<l.length-1; i++) {
                  items.push(new MLAB.Core.EnumItem(l[i]))
                }
              }
              // remove tailing ')' from last item
              var s = l[l.length-1]
              items.push(new MLAB.Core.EnumItem(s.substr(0, s.length-1)))
            }
          }
          f.setItems(items)
        })()
        type = 'Enum'
      } else {
        this.logError("MLABModule._createField: unhandled field type " + type)
        f = new MLAB.Core.Field()
      }
    }
    f.setup(name, type, flags, this)
    fieldMap[name] = f
  },
  
  createBaseFieldHandler: function(baseField) {
    return MLAB.Core.BaseFieldHandlerFactory.createHandler(baseField)
  },
  
  addInputField: function(name, type, flags) {
    this._createAndAddField(name, type, flags, this._inputFields)
  },
  
  addOutputField: function(name, type, flags) {
    this._createAndAddField(name, type, flags, this._outputFields)
  },
  
  addParameterField: function(name, type, flags) {
    this._createAndAddField(name, type, flags, this._parameterFields)
  },
  
  getRemoteRenderingControl: function(domElement) {
    return this._windowControll.getRemoteRenderingControl(this, domElement)
  },
  
  fieldValueChanged: function(field) {
    var m = new MLAB.Core.ModuleSetFieldValuesMessage()
    field.setLastChangeSerialID(MLAB.Core.ModuleSetFieldValuesMessage.LastSerialID)
    m.setData([{name: field.getName(), value: field.stringValue(), flags: field.getFlags()}])
    this.sendMessage(m)
  },
  
  /** \fn MLAB.Core.Module.field
   * 
   * Searches for a field with the given name and returns it if it was found,
   * or null if it is not found.
   */
  field: function(fieldName) {
    // try to keep the same semantics as MLABModule::lookupField() in mlabModule.cpp here
    var f = null
    if (fieldName in this._parameterFields) {
      f = this._parameterFields[fieldName]
    } else if (fieldName in this._inputFields) {
      f = this._inputFields[fieldName]
    } else if (fieldName in this._outputFields) {
      f = this._outputFields[fieldName]
    } 
    return f
  },

  /** \fn MLAB.Core.Module.updateFieldValues
   * 
   * Updates the field values from the given message data.
   * 
   * \implementationdetail
   * 
   * \param message Any subclass of MLAB.Core.ModuleFieldValuesBaseMessage.
   */
  updateFieldValues: function(message) {
    for (var i=0; i<message.fieldData.length; i++) {
      var fData = message.fieldData[i]
      var f = this.field(fData[0])
      if (f) {
        if (message.serialID >= f.lastChangeSerialID()) {
          f.updateStringValue(fData[1])
        }
        // drop outdated updates silently
      } else {
        this.logError("MLABModule.updateFieldValues: no such field found: " + fData[0])
      }
    }
  },
  
  updateFieldMinMaxValues: function(message) {
    for (var i=0; i<message.fieldData.length; i++) {
      var fData = message.fieldData[i]
      var f = this.field(fData.name)
      if (f) {
        if (fData.minValue.length > 0) {
          f.setMinValueAsString(fData.minValue)
        }
        if (fData.maxValue.length > 0) {
          f.setMaxValueAsString(fData.maxValue)
        }
      } else {
        this.logError("MLABModule.updateFieldMinMaxValues: no such field found: " + fData[0])
      }
    }
  },

  registerFieldListener: function(fieldName, fieldListener) {
    var f = this.field(fieldName)
    if (f) {
      f.addListener(fieldListener)
    } else {
      this.logError("MLABModule.registerFieldListener: no such field found: " + fieldName)
    }
  },
  
  // parse the interface, e.g. for getting min and max values of parameter fields
  _parseInterface: function(mdlTree) {
    var parameters = mdlTree.get("Parameters")
    if (parameters && parameters.count() >= 0) {
      for (var i=0; i<parameters.count(); i++) {
        var fieldTree = parameters.child(i)
        if (fieldTree.getName() !== "Field") { continue }
        var field = this.field(fieldTree.getValue())
        if (field) {
          var maxTree = fieldTree.get("max")
          var minTree = fieldTree.get("min")
          if (field.isNumberField()) {
            if (field.isIntegerField()) {
              if (maxTree) { field.setMaxValue(parseInt(maxTree.getValue())) }
              if (minTree) { field.setMinValue(parseInt(minTree.getValue())) }
            } else {
              if (maxTree) { field.setMaxValue(parseFloat(maxTree.getValue())) }
              if (minTree) { field.setMinValue(parseFloat(minTree.getValue())) }
            }
          }
        } else {
          this.logError("MLABModule.parseInterface: field not found: " + fieldTree.getValue())
        }
      }
    }
  },
  
  log: function(message, prefix) { this._moduleContext.log(message, prefix) },
  logError: function(error, prefix) { this._moduleContext.logError(error, prefix) },
  logException: function(exception, prefix) { this._moduleContext.logException(exception, prefix) },
})
