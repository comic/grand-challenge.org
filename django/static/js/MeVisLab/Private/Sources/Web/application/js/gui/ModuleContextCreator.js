/** \class MLAB.Core.ModuleContextCreator
 * 
 */
MLAB.GUI.deriveClass("ModuleContextCreator", MLAB.Core.Object, {
  ModuleContextCreator: function() {
    MLAB.GUI.ModuleContextCreator.super.constructor.call(this)
    this.registerSignal("modulesAreReady")
    this.registerSignal("hideLoadDialog")
    this.registerSignal("windowCreated")
    this.registerSignal("moduleProvidesPlugin")
    this._authenticationManager = null
    this._pendingModuleContexts = [] // contains all newly created module contexts 
                                     // until they are connected to the server
    
    // TODO: create an application settings object that is used here
    this._loginRequired = false
    this._logger = null
    this._modules = []
    this._renderSettings = null
    this._connectionSettings = null
    this._debugRemoteMessages = false
    this._logDiagnosisMessages = false
  },

  setAuthenticationManager: function(authenticationManager) { this._authenticationManager = authenticationManager },
  setRenderSettings: function(renderSettings) { this._renderSettings = renderSettings },
  setLogger: function(logger) { this._logger = logger },
  setLogDiagnosisMessages: function(flag) { this._logDiagnosisMessages = flag },
  setDebugRemoteMessages: function(debugRemoteMessages) { this._debugRemoteMessages = debugRemoteMessages },
  setConnectionSettings: function(connectionSettings) { this._connectionSettings = connectionSettings },
  
  /** \fn MLAB.Core.ModuleContextCreator.hasAnyModule
   * 
   * Returns true if any module was created.
   * 
   * \return A boolean value.
   */
  hasAnyModule: function() { return this._modules.length > 0 },

  /** \fn MLAB.Core.ModuleContextCreator._createModuleContext
   *
   * This method creates an MLAB.Core.ModuleContext instance. The module type must be the ID of the DOM element.
   * Optionally it may also include an instance name. If the module requires authentication a login dialog
   * will be shown when the web socket connection to the module is established. A callback function 
   * that is called when all module windows have been created from the MDL can also be given.
   * 
   * \param data An object with at least the "module" attribute and optional an "instanceName" attribute.
   * \return An MLABModule instance or null if it could not be created.
   */
  _createModuleContext: function(data) {
    this._logger.log("Creating module " + data.module + ".")
    var module = null
    try {
      var moduleType = data.module
      var moduleName = data.instanceName
      if (typeof(moduleName) === "undefined") {
        moduleName = moduleType
      }
      module = this.createModule(moduleType, moduleName)
    } catch (e) {
      this._logger.logException(e)
    }
    return module
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.getMeVisLabData
   * 
   * Returns custom data attributes with the given tag name.
   */
  getMeVisLabData: function(tagName) {
    var dataList = []
    var domElements = document.querySelectorAll('[' + tagName + ']')
    for (var i=0; i<domElements.length; i++) {
      try {
        var data = eval('({' + domElements[i].getAttribute(tagName) + '})')
        data.domElement = domElements[i]
        dataList.push(data)
      } catch(e) {
        this._logger.logException(e)
      }
    }
    return dataList
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.createModuleContexts
   * 
   * Creates module contexts for all DOM elements that have the given name. Calls _createModuleContext()
   * for each of these DOM elements.
   * 
   * \param domElementName DOM element name for module context elements. It may be either "createmacro" or "createmacro_authenticated".
   * \return true if at least one module context has been created, false otherwise.
   */
  createModuleContexts: function() {
    var modules = []
    var macrosToCreate = this.getMeVisLabData("data-mevislab-create-macro")
    for (var i=0; i<macrosToCreate.length; i++) {
      var macro = macrosToCreate[i]
      if ((typeof(macro.authentication) === "boolean") && macro.authentication) {
        this._loginRequired = true
      }
      var module = this._createModuleContext(macro)
      if (module) {
        modules.push(module)
      }
    }
    return modules
  },
  
  /** \fn MLAB.Core.ModuleContextCreator._handleModuleContextReady
   * 
   * This method is passed as a callback to MLAB.Core.ModuleContext.setModuleContextReadyCallback().
   * It manages finished and failed module context creation. It also shows a login dialog if a 
   * module context is not ready because of missing authentication. If all module contexts are
   * ready, then the module contexts are ready callback is called (see setModuleContextsReadyCallback()).
   * 
   * \param moduleContext An MLAB.Core.ModuleContext instance.
   * \param moduleCreationStatus The module context creation status. See MLAB.Core.ModuleInfoMessage for possible values.
   */
  _handleModuleContextReady: function(moduleContext, moduleCreationStatus) {    
    this._pendingModuleContexts.remove(moduleContext)
    
    // collect all unauthenticated module contexts. if all contexts finished
    // connecting, then re-request authentication and retry those contexts
    if (moduleCreationStatus === 4) {
      this._authenticationManager.addUnauthenticatedModuleContext(moduleContext)
    } else if (moduleCreationStatus === 0) {
      var webTree = moduleContext.getModule().getMDLTree().get("Web")
      if (webTree) {
        for (var i=0; i<webTree.count(); i++) {
          var child = webTree.child(i)
          if (child.getName().toLowerCase() == "plugin") {
            this.emit("moduleProvidesPlugin", MLAB.Core.translatePath(child.getValue()), moduleContext.getModule())
          }
        }
      }
    }
    
    if (this._pendingModuleContexts.length === 0) {
      if (this._authenticationManager.hasAnyUnauthenticatedModuleContext()) {
        this._loginRequired = true
        this.emit("hideLoadDialog")
        
        this._pendingModuleContexts = this._authenticationManager.getUnauthenticatedModuleContexts() 
        
        // authentication failed, re-request authentication data
        this._authenticationManager.requestAuthentication()
        
      } else {
        // all contexts are authenticated or do not need any authentication
        this._logger.setModuleContextsReady()
        this.emit("modulesAreReady")
      }
    }
  },
  
  createGUIFromMDL: function() {
    this._createGUIFromDOMElements()
  },
  
  /** \fn MLAB.Core.ModuleContextCreator._createGUIFromDOMElements
   */
  _createGUIFromDOMElements: function() {
    var panels = this.getMeVisLabData("data-mevislab-show-panel")
    for (var i=0; i<panels.length; i++) {
      var panel = panels[i]
      var moduleName = panel.module
      var windowName = panel.window
      var module = this.getModule(moduleName)
      if (module) {
        module.showPanel(windowName, panel.domElement)
      } else {
        this._logger.logError("No such module found: " + moduleName)
      }
    }
    
    var windows = this.getMeVisLabData("data-mevislab-show-window")
    for (var i=0; i<windows.length; i++) {
      var window = windows[i]
      var moduleName = window.module
      var windowName = window.window
      var module = this.getModule(moduleName)
      if (module) {
        module.showWindow(windowName, window.domElement)
      } else {
        this._logger.logError("No such module found: " + moduleName)
      }
    }
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.createModule
   */
  createModule: function(moduleType, moduleName) {
    if (!moduleName) {
      moduleName = moduleType
    }
    var module = this.getModule(moduleName)
    if (!module) {
      module = new MLAB.Core.Module(moduleName, moduleType)
      this._modules.push(module)
      this._logger.addModule(module)
      module.setWindowController(new MLAB.GUI.WindowController())
      module.connectSignal("windowCreated", this, "windowCreated")
      var moduleContext = module.getModuleContext()
      this._pendingModuleContexts.push(moduleContext)
      moduleContext.setRenderSettings(this._renderSettings)
      moduleContext.connect("moduleIsReady", this, "_handleModuleContextReady")
      moduleContext.setLogDiagnosisMessages(this._logDiagnosisMessages)
      moduleContext.setDebugRemoteMessages(this._debugRemoteMessages)
      moduleContext.openConnection(this._connectionSettings)
    } else {
      this._logger.logError("A module with this name exists already: " + moduleName)
    }
    return module
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.destroyModule
   */
  destroyModule: function(moduleName) {
    var module = null
    for (var i=0; i<this._modules.length; i++) {
      if (this._modules[i].getName() === moduleName) {
        module = this._modules.splice(i, 1)[0]
        break
      }
    }
    if (module) {
      module.destroy()
      this._logger.removeModule(module)
    } else {
      this._logger.logError("Module not found: " + moduleName)
    }
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.getModule
   * 
   * \param moduleName The module name.
   * \return Returns the MLABModule or null if it was not found.
   */
  getModule: function(moduleName) {
    for (var i=0; i<this._modules.length; i++) { 
      if (this._modules[i].getName() === moduleName) {
        return this._modules[i]
      }
    }
    return null
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.disconnectModules
   * 
   * Calls MLABModule.closeConnection() for each module.
   */
  disconnectModules: function() {
    for (var i=0; i<this._modules.length; i++) {
      this._modules[i].getModuleContext().closeConnection()
    }
  },
  
  /** \fn MLAB.Core.ModuleContextCreator.notifyBodyIsVisible
   * 
   * Calls MLABModule.setBodyIsVisible() on each module.
   */
  notifyBodyIsVisible: function() {
    for (var i=0; i<this._modules.length; i++) {
      this._modules[i].getModuleContext().setBodyIsVisible()
    }
  },

  /** \fn MLAB.Core.ModuleContextCreator.showIDEs
   * 
   * Calls MLABModule.showIDE() on each module.
   */
  showIDEs: function() {
    for (var i=0; i<this._modules.length; i++) {
      this._modules[i].showIDE()
    }
  },
})
