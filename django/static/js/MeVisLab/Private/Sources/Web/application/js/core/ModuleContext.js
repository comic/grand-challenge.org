/** \defgroup ModuleContextStates Module Context States
 * 
 * The MLAB.Core.ModuleContext has different states, each state expects certain remote messages
 * and handles them accordingly.
 * The initial state is MLAB.Core.MCStateUninitialized. Later MLAB.GUI.Application will call MLAB.Core.ModuleContext.connect()
 * which creates the web socket connection using the MLAB.Core.RemoteManager of the module context.<br><br>
 * If the connection was successfully created, then the module context sends a MLAB.Core.ModuleCreateMessage to MeVisLab 
 * and changes its state to MLAB.Core.MCStateCreatingModule. After MeVisLab sends a MLAB.Core.ModuleInfoMessage after it 
 * has finished the creating the module. MLAB.Core.MCStateCreatingModule then handles this message. Depending on 
 * the message status, the next state will be either MLAB.Core.MCStateModuleReady (everything is ok and the module is ready), 
 * MLAB.Core.MCStateUnauthenticated (the module requires authentication by username and password), or 
 * MLAB.Core.MCStateFailedToCreateModule.<br><br>
 * In case of MLAB.Core.MCStateFailedToCreateModule nothing will be done further. MLAB.Core.MCStateUnauthenticated notifies 
 * that the module requires authentication and behaves like MLAB.Core.MCStateCreatingModule.<br><br>
 * If MLAB.Core.MCStateModuleReady gets the current state, then it creates the fields (see \ref Fields), notifies
 * the module context that the module is ready, and sends a generic request to the module in MeVisLab
 * to retrieve the MDL tree for the window creation. If the reply to this request is received, then 
 * the widget controls are created and the current state is changed to MLAB.Core.MCStateMDLReady. If the html body
 * is already visible or when it gets visible, then the remote rendering slaves are activated and the
 * current and final state is MLAB.Core.MCStateRenderingSlavesActivated.
 */


/** \class MLAB.Core.MCState
 * 
 * This is the base class for module context states.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.defineClass("MCState", {
  MCState: function(moduleContext) {
    this._moduleContext = moduleContext
    this._statusCode = -2
  },
  
  setStatusCode: function(statusCode) { this._statusCode = statusCode },
  
  /** \fn MLAB.Core.MLAB.Core.MCState.run
   * 
   * This method is called when this is state is made current.
   */
  run: function() { },
  
  /** \fn MLAB.Core.MLAB.Core.MCState.handleMessageAndGetNextState
   * 
   * Handles the given remote message in the appropriate way for the current state.
   * 
   * \param message The remote message. See \ref RemoteMessages.
   */
  handleMessageAndGetNextState: function(message) {
    if (message.isBaseFieldMessage()) {
      this._moduleContext._handleBaseFieldMessage(message)
    } else {
      switch (message.type) {
        case MLAB.Core.MSG_MODULE_LOG_MESSAGE:
          // log all messages except the ones that were sent from the web client to MeVisLab,
          // because those were already handled
          var text = MLAB.Core.getTextContent(message.message)
          var webMsgRegExp = /(\w+\s+)?\d+-\d+-\d+\s+\d+:\d+:\d+\s+[\s\w]+:\s+\[WEB\]/
          var m = text.match(webMsgRegExp)
          if (!m) {
            this._moduleContext.logDiagnosisMessage(message.message)
          }
          break
          
        case MLAB.Core.MSG_MODULE_SET_FIELD_VALUES:
          this._moduleContext.getModule().updateFieldValues(message)
          break
        
        case MLAB.Core.MSG_MODULE_FIELDS_MIN_MAX_CHANGED:
          this._moduleContext.getModule().updateFieldMinMaxValues(message)
          break
          
        default:
          this.logError("Unknown message: " + MLAB.Core.getMessageTypeName(message.type))
      }
    }
    return null
  },

  logError: function(message) { this._moduleContext.logError(this._name + ": " + message) },  
  log: function(message) { this._moduleContext.log(this._name + ": " + message) },
})


/** \class MLAB.Core.MLAB.Core.MCStateUninitialized(MLAB.Core.MCState)
 * 
 * This module context state is initially active.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateUninitialized", MLAB.Core.MCState, {
  MCStateUninitialized: function(moduleContext) {
    MLAB.Core.MCStateUninitialized.super.constructor.call(this, moduleContext)
  },
})


/** \class MLAB.Core.MCStateCreatingModule(MLAB.Core.MCState)
 * 
 * This module context state is active when the module is being created.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateCreatingModule", MLAB.Core.MCState, {
  MCStateCreatingModule: function(moduleContext) {
    MLAB.Core.MCStateCreatingModule.super.constructor.call(this, moduleContext)
  },
  
  handleMessageAndGetNextState: function(message) {
    var nextState = null
    switch (message.type) {
      case MLAB.Core.MSG_MODULE_INFO:
        if (message.status === 0) {
         // status === 0 means successful module creation
          nextState = new MLAB.Core.MCStateModuleReady(this._moduleContext)
        } else if (message.status === 4) {
          // status === 4 means authentication failed
          nextState = new MLAB.Core.MCStateUnauthenticated(this._moduleContext)
        } else {
          nextState = new MLAB.Core.MCStateFailedToCreateModule(this._moduleContext)
        }
        nextState.setStatusCode(message.status)
        break
        
      case MLAB.Core.MSG_MODULE_PROCESS_INFORMATION:
        // this message is currently not handled
        break

      default:
        nextState = MLAB.Core.MCStateCreatingModule.super.handleMessageAndGetNextState.call(this, message)
    }    
    return nextState
  },
})

/** \class MLAB.Core.MCStateUnauthenticated(MLAB.Core.MCStateCreatingModule)
 * 
 * This module context state is active when the module could not be created, because
 * the required authentication data is missing or invalid.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateUnauthenticated", MLAB.Core.MCState, {
  MCStateUnauthenticated: function(moduleContext) {
    MLAB.Core.MCStateUnauthenticated.super.constructor.call(this, moduleContext)
  },
  
  run: function() {
    this._moduleContext.notifyModuleRequiresAuthentication(this._statusCode)
  },
})

/** \class MLAB.Core.MCStateFailedToCreateModule(MLAB.Core.MCState)
 * 
 * This module context state is active when the module could not be created due to an error.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateFailedToCreateModule", MLAB.Core.MCState, {
  MCStateFailedToCreateModule: function(moduleContext) {
    MLAB.Core.MCStateFailedToCreateModule.super.constructor.call(this, moduleContext)
  },
})

/** \class MLAB.Core.MCStateModuleReady(MLAB.Core.MCState)
 * 
 * This module context state is active when the module was created and authentication was successful.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateModuleReady", MLAB.Core.MCState, {
  MCStateModuleReady: function(moduleContext) {
    MLAB.Core.MCStateModuleReady.super.constructor.call(this, moduleContext)
  },
  
  run: function(module, message) {
    this._createFields(module, message)
    this._requestMDL(module)
  },
  
  _createFields: function(module, message) {
    for (var i=0; i<message.fieldData.length; i++) {
      var fieldName = message.fieldData[i][0]
      var fieldType = message.fieldData[i][1]
      var options   = message.fieldData[i][2]
      // these constants are defined in class MessageModuleInfo in mlabRemoteModuleMessages.h
      // (options & 4 == non-persistent field, currently not handled)
      if ((options & 1) && (options & 2)) { 
        module.addParameterField(fieldName, fieldType, options) 
      } else if (options & 1) {
        module.addInputField(fieldName, fieldType, options)
      } else if (options & 2) {
        module.addOutputField(fieldName, fieldType, options)
      } else {
        MLAB.Core.throwException("Unexpected option flag: " + option) 
      }
    }
  },
  
  _setKnownWidgetControls: function(controlNames) {
    var l = []
    for (var i=0; i<controlNames.length; i++) {
      var n = controlNames[i]
      // ignore non-GUI controls which we do not handle
      if (!(n in ["Colors", "DefineStyle", "Execute", "FieldListener", "EventFilter"])) {
        l.push(n)
      }
    }
    this._moduleContext._setKnownWidgetControls(l)
  },

  _setMDLReady: function() {
    this._moduleContext.changeState(new MLAB.Core.MCStateMDLReady(this._moduleContext))
    this._moduleContext.setModuleReady(this._statusCode)
  },
  
  _requestMDL: function(module) {
    this._moduleContext.sendGenericRequest("handleRemoteMDLRequest", [], function(args) {
      var json = JSON.parse(args[0])
      module.setMDLTree(new MLAB.Core.Tree(json))
      
      if (this._moduleContext._areKnownWidgetControlsSet()) {
        this._setMDLReady()
      } else {
        this._moduleContext.sendGenericRequest("handleWidgetControlNamesRequest", [], function(args) {
          this._setKnownWidgetControls(args[0])
          this._setMDLReady()
        }.bind(this))
      }
    }.bind(this))
  },
})

/** \class MLAB.Core.MCStateMDLReady(MLAB.Core.MCState)
 * 
 * This module context state is active when all widget controls and DOM elements
 * are created from the MDL script.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateMDLReady", MLAB.Core.MCState, {
  MCStateMDLReady: function(moduleContext) {
    MLAB.Core.MCStateMDLReady.super.constructor.call(this, moduleContext)
  },
  
  run: function() {
    if (this._moduleContext.isBodyVisible()) {
      this._moduleContext.changeState(new MLAB.Core.MCStateRenderingSlavesActivated(this._moduleContext))
    }
  },
})

/** \class MLAB.Core.MCStateRenderingSlavesActivated(MLAB.Core.MCState)
 * 
 * This module context state is active when the remote rendering slaves are activated.
 * 
 * \ingroup ModuleContextStates
 */
MLAB.Core.deriveClass("MCStateRenderingSlavesActivated", MLAB.Core.MCState, {
  MCStateRenderingSlavesActivated: function(moduleContext) {
    MLAB.Core.MCStateRenderingSlavesActivated.super.constructor.call(this, moduleContext)
  },
  
  run: function(module) {
    var inputFields = module.getInputFields()
    for (var fieldName in inputFields) {
      var field = inputFields[fieldName]
      if (field.isBaseField() && field.getBaseType() === "RemoteRendering") {
        field.getHandler().addRenderingSlaves()
      }
    }
  },
})

/** \class MLAB.Core.ModuleContextLogger
 * 
 */
MLAB.Core.defineClass("ModuleContextLogger", {
  ModuleContextLogger: function() {  
    this._module = null
    this._remoteManager = null
    this._logDiagnosisMessages = false
    this._moduleReady = false
  },

  setModule: function(module) { this._module = module },
  setLogDiagnosisMessages: function(flag) { this._logDiagnosisMessages = flag },
  setRemoteManager: function(remoteManager) { 
    this._remoteManager = remoteManager
    this._remoteManager.setConsoleLogger(this)
  },
  
  
  logConsoleMessage: function(message) {
    if (typeof(console) !== "undefined") {
      this._manageConsoleLogGroup()
      console.log(message)
    }
  },
  
  logConsoleWarn: function(message) {
    if (typeof(console) !== "undefined") {
      this._manageConsoleLogGroup()
      console.warn(message)
    }
  },
  
  logConsoleError: function(message) {
    if (typeof(console) !== "undefined") {
      this._manageConsoleLogGroup()
      console.error(message)
    } else {
      alert("An error occurred and no logging console is available: " + message)
    }
  },
  
  logConsoleInfo: function(message) {
    if (typeof(console) !== "undefined") {
      this._manageConsoleLogGroup()
      console.info(message)
    }
  },
  
  _closeConsoleGroupDelayed: function ()  {
    return window.setTimeout(function() { console.hasOpenGroup = false; console.groupEnd() }, 1000)
  },
  
  _manageConsoleLogGroup: function() {
    var isCurrentGroup = (console.currentMeVisLabModule === this._module.getName())
    if (!isCurrentGroup) {
      if (console.closeConsoleTimerId) {
        window.clearTimeout(console.closeConsoleTimerId)
        delete console.closeConsoleTimerId
      }
      if (console.hasOpenGroup) {
        console.groupEnd()
        console.hasOpenGroup = false
      }
    }
    if (!console.hasOpenGroup) {
      console.hasOpenGroup = true
      console.group(this._module.getName())
      console.currentMeVisLabModule = this._module.getName()
      console.closeConsoleTimerId = this._closeConsoleGroupDelayed()
    }
  },

  logDiagnosisMessage: function(message) {
    // remove html tags from the diagnosis message
    var text = MLAB.Core.getTextContent(message)
    var typeRegExp = /(\w+\s+)?\d+-\d+-\d+\s+\d+:\d+:\d+\s+([\s\w]+):/
    var m = text.match(typeRegExp)
    if (m) {
      if (m[m.length-1].indexOf("Error") >= 0) {
        this.logConsoleError(text)
      } else if (m[0].indexOf("Warning") >= 0) {
        this.logConsoleWarn(text)
      } else {
        if (this._logDiagnosisMessages) {
          this.logConsoleInfo(text)
        }
      }
    } else {
      this.logConsoleError("typeRegExp did not match " + text + ":\n" + typeRegExp.pattern)
    }
  },
  
  log: function(message, prefix) {
    if (this._moduleReady) {
      this._remoteManager.log(message, prefix)
    } else {
      if (!this._pendingLogs) { this._pendingLogs = [] }
      this._pendingLogs.push([message, prefix])
      //this.logConsoleMessage("Pending remote manager log: " + message)
    }
  },
  
  logError: function(message, prefix) {
    if (this._moduleReady) {
      this._remoteManager.logError(message, prefix)
    } else {
      if (!this._pendingLogErrors) { this._pendingLogErrors = [] }
      this._pendingLogErrors.push([message, prefix])
      this.logConsoleError("Pending remote manager log error: " + message)
    }  
  },
  
  logException: function(exception, prefix) {
    if (this._moduleReady) {
      this._remoteManager.logException(exception, prefix)
    } else {
      if (!this._pendingLogExceptions) { this._pendingLogExceptions = [] }
      this._pendingLogExceptions.push([exception, prefix])
      this.logConsoleError("Pending remote manager log exception: " + exception)
    }
  },
  
  flushPendingRemoteManagerLogs: function() {
    this._moduleReady = true
    var l = this._pendingLogs
    if (l) {
      for (var i=0; i<l.length; i++) {
        this._remoteManager.log(l[i][0], l[i][1])
      }
    }
    l = this._pendingLogErrors
    if (l) {
      for (var i=0; i<l.length; i++) {
        this._remoteManager.logError(l[i][0], l[i][1])
      }
    }
    l = this._pendingLogExceptions
    if (l) {
      
      for (var i=0; i<l.length; i++) {
        this._remoteManager.logException(l[i][0], l[i][1])
      }
    }
  },
})


/** \class MLAB.Core.ModuleContext
 * 
 * The module context is the communication interface between the MLABModule, MLABWidgetControl, and MLAB.Core.Field
 * on the client side and the MeVisLab process and module instance on the server side.
 * It creates a MLAB.Core.RemoteManager instance that provides a web socket to communicate 
 * with the MeVisLab instance on the server. It triggers the creation of the given module
 * and creates widget controls from the modules MDL tree.
 */
MLAB.Core.deriveClass("ModuleContext", MLAB.Core.Object, {
  ModuleContext: function(module) {
    MLAB.Core.ModuleContext.super.constructor.call(this)
    this.registerSignal("moduleIsReady")
    this._knownWidgetControls = []
    this._moduleReady = false
    this._remainingReconnects = 3
    this._module = module
    this._renderSettings = null
    this._logger = new MLAB.Core.ModuleContextLogger()
    this._logger.setModule(this._module)
    this._isBodyVisible = false
    this._state = new MLAB.Core.MCStateUninitialized(this)
    this._connected = false
    
    this._remoteManager = new MLAB.Core.RemoteManager()
    this._remoteManager.setConnectedCallback(this.callback("handleConnected"))
    this._remoteManager.setDisconnectedCallback(this.callback("handleDisconnected"))
    this._remoteManager.setMessageReceivedCallback(this.callback("handleMessage"))
    window.addEventListener("beforeunload", this.callback("handleUnload"))

    this._logger.setRemoteManager(this._remoteManager)
  },

  setRenderSettings: function(settings) { this._renderSettings = settings },
  
  /** \fn MLAB.Core.ModuleContext.getRenderSettings
   * 
   * Returns the render quality settings.
   * 
   * \return An MLAB.Core.RenderSettings instance.
   * \ingroup RemoteRendering 
   */
  getRenderSettings: function() { return this._renderSettings },
  
  setLogDiagnosisMessages: function(flag) { this._logger.setLogDiagnosisMessages(flag) },
  
  logDiagnosisMessage: function(message) { this._logger.logDiagnosisMessage(message) },
  
  /** \fn MLAB.Core.ModuleContext._areKnownWidgetControlsSet
   * 
   * Returns true if the known widget controls array is not empty. See _setKnownWidgetControls().
   * 
   * \return A boolean value.
   */
  _areKnownWidgetControlsSet: function() { return this._knownWidgetControls.length > 0 },
  
  /** \fn MLAB.Core.ModuleContext._setKnownWidgetControls
   * 
   * Sets the known widget controls. This method is called when the reply to the get MDL request has been received.
   * 
   * \param controls An array with the control names.
   */
  _setKnownWidgetControls: function(controls) { this._knownWidgetControls = controls },
  
  /** \fn MLAB.Core.ModuleContext.isWidgetControl
   * 
   * Returns true if the given MDL tag is the name of a widget control. Note that this method
   * requires that the known widget controls are set (_setKnownWidgetControls()).
   * 
   * \return A boolean value.
   */
  isWidgetControl: function(mdlTag) { return this._knownWidgetControls.indexOf(mdlTag) >= 0 },
 
  /** \fn MLAB.Core.ModuleContext.isBodyVisible 
   * 
   * Returns true if the html body is already visible.
   */
  
  isBodyVisible: function() { return this._isBodyVisible },

  getState: function() { return this._state },
  
  /** \fn MLAB.Core.ModuleContext.getModule
   * 
   * Returns the managed MLABModule.
   */
  getModule: function() { return this._module },
  
  /** \fn MLAB.Core.ModuleContext.showIDE
   * 
   * Send the show IDE request to the MeVisLab process on the server
   * to show the MeVisLab IDE. Note that this is a debugging feature,
   * you need to have access to the server to view the IDE.
   */
  showIDE: function() {
    this.sendMessage(new MLAB.Core.ModuleShowIDEMessage())
  },

  _handleBaseFieldMessage: function(message) {
    var baseField = this._module.field(message.baseField)
    if (baseField) {
      if (baseField.isBaseField()) {
        baseField.handleMessage(message)
      } else {
        this.logError("Field is not a base field: " + baseField.getName() + " " + baseField.type())
      }
    } else {
      this.logError("Field not found: " + message.baseField)
    }
  },
  
  handleConnected: function() {
    this.changeState(new MLAB.Core.MCStateCreatingModule(this))
    this._connected = true

    var message = new MLAB.Core.ModuleCreateMessage()
    message.setData({module: this._module.getType()})
    this._remoteManager.sendMessage(message)
  },
  
  handleDisconnected: function(ev) {
    if (!this._connected) {
      window.alert("The connection was rejected by the server.\nPerhaps you should try again later.")
    } else {
      var msg = "The connection was closed by the server.\n"
      if (ev.reason) {
        msg += "Reason: " + ev.reason + "\n"
      }
      msg += "\nPlease reload the page to reconnect."
      window.alert(msg)
      this._connected = false
    }
  },
  
  handleUnload: function() {
    // close connection when leaving the page, this does some cleanup
    // (and avoids the alert above)
    if (this._connected) {
      this.closeConnection()
    }
    // return nothing, we don't want to open a dialog
  },
  
  authenticate: function(username, password) {
    var message = new MLAB.Core.ModuleSetFieldValuesMessage()
    message.setData([{name: "user", value: username, flags: 0}, {name: "password", value: password, flags: 0}])
    this._remoteManager.sendMessage(message)
  },
  
  /** \fn MLAB.Core.ModuleContext.setBodyIsVisible
   * 
   * Notifies the module context that the body of the web page is visible. If the MDL
   * parsing and widget control generation is already finished, then the module context state 
   * is changed to MLAB.Core.MCStateRenderingSlavesActivated and the remote rendering controls start rendering
   * and interaction handling.
   */
  setBodyIsVisible: function() {
    this._isBodyVisible = true
    if (this._state.getClassName() === "MLAB.Core.MCStateMDLReady") {
      this.changeState(new MLAB.Core.MCStateRenderingSlavesActivated(this))
    }
  },
  
  /** \fn MLAB.Core.ModuleContext.handleMessage
   * 
   * Handles the given remote message. This function is registered as a callback
   * using MLAB.Core.RemoteManager.setMessageReceivedCallback(). The message is passed
   * to the current module context state to be handled. As a result the current
   * state may change.
   * 
   * \see MLAB.Core.MCState.handleMessageAndGetNextState()
   * 
   * \param message The remote message. See \ref RemoteMessages
   */
  handleMessage: function(message) {
    var nextState = this._state.handleMessageAndGetNextState(message)
    if (nextState !== null) { this.changeState(nextState, message) }
  },
  
  setModuleReady: function(statusCode) {
    this._moduleReady = true
    this._logger.flushPendingRemoteManagerLogs()
    this.log("Module context ready: " + this._module.getName() + " [" + this._module.getType() + "].")
    this.emitModuleReady(statusCode)
  },
  
  notifyModuleRequiresAuthentication: function(statusCode) {
    this.emitModuleReady(statusCode)
  },
  
  notifyModuleCreationFailed: function(statusCode) {
    this.logError("Module status: " + statusCode)
    this.emitModuleReady(statusCode)
  },
  
  changeState: function(newState, message) {
    this._state = newState
    try {
      this._state.run(this._module, message)
    } catch (e) {
      this.logError("Caught exception while running the current state, see exception below.")
      this.logException(e)
    }
  },
  
  log: function(message, prefix) { this._logger.log(message, prefix) },
  
  logError: function(message, prefix) { this._logger.logError(message, prefix) },
  
  logException: function(exception, prefix) { this._logger.logException(exception, prefix) },

  /** \fn MLAB.Core.ModuleContext.closeConnection
   * 
   * Closes the web socket connection.
   */
  closeConnection: function() {
    this._remoteManager.setDisconnectedCallback(null)
    this._remoteManager.closeConnection()
    this._connected = false
  },
  
  /** \fn MLAB.Core.ModuleContext.openConnection
   * 
   * See MLARemoteManager.openConnection()
   * 
   * \param connectionSettings An MLAB.Core.ConnectionSettings object.
   */
  openConnection: function(connectionSettings) {
    this._remoteManager.openConnection(connectionSettings)
  },
  
  emitModuleReady: function(messageStatus) {
    this.emit("moduleIsReady", this, messageStatus)
  },
  
  sendMessage: function(message) {
    this._remoteManager.sendMessage(message)
  },
  
  sendGenericRequest: function(functionName, args, responseHandler) {
    this._remoteManager.sendGenericRequest(functionName, args, responseHandler)
  },
  
  setDebugRemoteMessages: function(flag) {
    this._remoteManager.setDebugMessages(flag)
  },
})
