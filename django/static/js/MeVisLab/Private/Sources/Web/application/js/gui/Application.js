// add remove() function to builtin Array class for convenience 
Array.prototype.remove = function(element) {
  var idx = this.indexOf(element)
  if (idx !== -1) {
    return this.splice(idx, 1)
  }
  return null
}

/** \class MLABApp
 * 
 *  The global application variable. 
 */
var MLABApp = (function() {
  function mlabSetupApplication(creatingModuleContextsCallback, args) {
    
    /** \class MLAB.GUI.ApplicationLogger
     * 
     */
    MLAB.GUI.defineClass("ApplicationLogger", {
      ApplicationLogger: function() {
        this._modules = []
        this._pendingLogMessages = []
        this._pendingLogErrors = []
        this._pendingLogExceptions = []
        this._areModuleContextsReady = false
      },
      
      setModuleContextsReady: function() { 
        this._areModuleContextsReady = true
        this._flushPendingLogMessages()
        this._flushPendingLogErrors()
        this._flushPendingLogExceptions()
      },
      
      addModule: function(module) {
        this._modules.push(module)
      },
      
      removeModule: function(module) {
        this._modules.remove(module)
      },
      
      log: function(message) {
        if (typeof(console) !== "undefined") {
          console.info(message)
        }
        if (!this._areModuleContextsReady && (this._modules.length === 0)) {
          this._pendingLogMessages.push(message)
        } else {
          for (var i=0; i<this._modules.length; i++) {
            this._modules[i].log(message, "[WEB]")
          }
        }
      },
      
      _canFlushLogsMessage: function(logList) {
        return logList.length > 0 && this._areModuleContextsReady && (this._modules.length > 0)
      },
      
      _flushPendingLogMessages: function() {
        if (this._canFlushLogsMessage(this._pendingLogMessages)) {
          for (var i=0; i<this._pendingLogMessages.length; i++) {
            for (var j=0; j<this._modules.length; j++) {
              this._modules[j].log(this._pendingLogMessages[i], "[WEB]")
            }
          }
          this._pendingLogMessages = []
        }
      },
      
      logError: function(message) {
        if (typeof(console) !== "undefined") {
          console.error(message)
        } else {
          alert("An error occurred and no logging console is available: " + exception)
        }
        if (!this._areModuleContextsReady && this._modules.length === 0) {
          this._pendingLogErrors.push(message)
        } else {
          for (var i=0; i<this._modules.length; i++) {
            this._modules[i].logError(message, "[WEB]")
          }
        }
      },
      
      _flushPendingLogErrors: function() {
        if (this._canFlushLogsMessage(this._pendingLogErrors)) {
          for (var i=0; i<this._pendingLogErrors.length; i++) {
            for (var j=0; j<this._modules.length; j++) {
              this._modules[j].logError(_pendingLogErrors[i], "[WEB]")
            }
          }
          this._pendingLogErrors = []
        }
      },
      
      logException: function(exception) {
        if (typeof(console) !== "undefined") {
          console.error(exception)
        } else {
          alert("An error occurred and no logging console is available: " + exception)
        }
        if (!this._areModuleContextsReady && this._modules.length === 0) {
          this._pendingLogExceptions.push(exception)
        } else {
          for (var i=0; i<this._modules.length; i++) {
            this._modules[i].logException(exception, "[WEB]")
          }
        }
      },
      
      _flushPendingLogExceptions: function() {
        if (this._canFlushLogsMessage(this._pendingLogExceptions)) {
          for (var i=0; i<this._pendingLogExceptions.length; i++) {
            for (var j=0; j<this._modules.length; j++) {
              this._modules[j].logException(this._pendingLogExceptions[i], "[WEB]")
            }
          }
          this._pendingLogExceptions = []
        }
      },
    })
    
  
    /** \class MLAB.GUI.ApplicationSettings
     * 
     */
    MLAB.GUI.defineClass("ApplicationSettings", {
      ApplicationSettings: function() {
        this._logDiagnosisMessages = false
        this._urlToMLABRoot = null
        this._pluginsToLoad = []
        this._showIDE = false
        this._debugRemoteMessages = false
      },
      
      /** \fn MLAB.GUI.ApplicationSettings.debugRemoteMessages
       * 
       * Returns true if remote messages are being printed to the debugging console.
       * 
       * \ingroup Debugging
       */
      debugRemoteMessages: function() { return this._debugRemoteMessages },
      
      getPluginsToLoad: function() { return this._pluginsToLoad },
      showIDE: function() { return this._showIDE },
      logDiagnosisMessages: function() { return this._logDiagnosisMessages },
    
      setupFromArguments: function(args) {
        this._urlToMLABRoot = MLABApp.autodetectURLToMLABRoot(args)
  
        if ("debugRemoteMessages" in args) { this._debugRemoteMessages = true }
        if ("diagnosis" in args) { this._logDiagnosisMessages = true }
        if ("plugins" in args) { this._pluginsToLoad = args["plugins"].split(",") }
        if ('showIDE' in args) { this._showIDE = true }
      },
      
      /** \fn MLAB.GUI.Application.getURLToMLABRoot
       * 
       * Returns the url to MLAB_ROOT. The url is by default 
       * window.location.protocol + '//' + window.location.host + '/Packages'. It can be
       * set by using url arguments, e.g. http://www.myserver.de/index.html?mlabRoot=http://www.myserver.de/Packages.
       * As all url arguments, it can also be set by using the arguments parameter of
       * initialize().
       * 
       * \returns Returns the url to MLAB_ROOT.
       */
      getURLToMLABRoot: function() { return this._urlToMLABRoot },
    })
    
    /** \class MLAB.GUI.PluginBase
     * 
     */
    MLAB.GUI.deriveClass("PluginBase", MLAB.Core.Object, {
      PluginBase: function() {
        this._cssUrls = []
        this._jsUrls = []
        this._resourceManager = null
        this._resourcesBaseUrl = null
        this._module = null
      },
      
      /** \fn MLAB.GUI.PluginBase.setModule
       * 
       * Sets the module that loaded this plugin.
       * 
       * \param module An MLAB.Core.Module instance.
       */
      setModule: function(module) {
        this._module = module
      },
      
      /** \fn MLAB.GUI.PluginBase.module
       * 
       * Returns the module that loaded this plugin.
       * 
       * \return Returns an MLAB.Core.Module instance.
       */
      module: function() {
        return this._module
      },
    
      /** \fn MLAB.GUI.PluginBase.initialize
       * 
       * This method is called <b>before</b> the JavaScript and CSS files of the plugin have been loaded. The application arguments
       * are all passed to this method to allow plugins to evaluate custom arguments. You can override this method
       * in a sub class, by default it does nothing.  
       * 
       * \param applicationArguments The application arguments. See also MLAB.GUI.ApplicationSettings and MLAB.Core.RenderSettings. 
       */
      initialize: function(applicationArguments) {
        // can be reimplememented in a subclass to initialize the plugin by parsing the arguments
      },
      
      /** \fn MLAB.GUI.PluginBase.setCSSUrls
       * 
       * Sets the URLs of the CSS files provided by the plugin. They can be absolute or relative to
       * the URL of the plugin file. Relative URLs are resolved using the base URL given by setResourcesBaseUrl().
       * 
       * \param urls An array containing the urls to CSS files.
       */
      setCSSUrls: function(urls) {
        this._cssUrls = urls
      },
      
      /** \fn MLAB.GUI.PluginBase.setJSUrls
       * 
       * Sets the URLs of the JavaScript files provided by the plugin. They can be absolute or relative to
       * the URL of the plugin file. Relative URLs are resolved using the base URL given by setResourcesBaseUrl().
       * 
       * \param urls An array containing the urls to JavaScript files.
       */
      setJSUrls: function(urls) {
        this._jsUrls = urls
      },
      
      /** \fn MLAB.GUI.PluginBase.setResourcesBaseUrl
       * 
       * Sets the base URL for resolving relative resource URLs. This method should only be called by
       * MLAB.GUI.Application. It sets the URL to the directory URL of the plugin file.
       * 
       * \param url The base URL for resolving relative resource URLs.
       */
      setResourcesBaseUrl: function(url) {
        this._resourcesBaseUrl = url
      },
      
      /** \fn MLAB.GUI.PluginBase.setResourcesBaseUrl
       * 
       * Returns the resources base URL. See also setResourcesBaseUrl().
       * 
       * \return Returns the resources base URL.
       */
      resourcesBaseUrl: function() {
        return this._resourcesBaseUrl
      },
      
      /** \fn MLAB.GUI.PluginBase.load
       * 
       * Loads all resources and calls setup() and the given callback function when all resources have finished loading.
       * 
       * \param finishedLoadingCallback A callback function that is called when all resources have finished loading.
       */
      load: function(finishedLoadingCallback) {
        this._resourceManager = new MLAB.Core.ResourceManager(this._resourcesBaseUrl)
        this._resourceManager.loadResources(this._jsUrls, this._cssUrls, (function() {
          this.setup()
          finishedLoadingCallback()
        }).bind(this))
        
      },
  
      /** \fn MLAB.GUI.PluginBase.setup
       * 
       * This method is called <b>after</b> the JavaScript and CSS files of the plugin have finished loading. 
       * You can override this method in a sub class. By default it does nothing. 
       */
      setup: function() {
        // can be reimplememented in a subclass to setup the plugin after
        // the css and js files have been loaded
      },
    })
    
    /** \class MLAB.GUI.Application
     * 
     * The application class manages the steps to create the web application. It evaluates the
     * (url) arguments, loads the core resources, instantiates and loads plugins, notifies 
     * connected objects about certain states, and creates specified modules.
     * 
     * \htmlonly
     * <h2>Signals</h2>
     * <ul>
     *   <li>creatingModuleContexts<p>is emitted when the application start creating module contexts.</p></li>
     *   <li>modulesAreReady</li>
     *   <li>moduleWindowCreated</li>
     *   <li>hideLoadDialog</li>
     *   <li>showLoadDialog</li>
     * </ul>
     * \endhtmlonly
     */
    MLAB.GUI.deriveClass("ApplicationSingleton", MLAB.Core.Object, {
      ApplicationSingleton: function() {
        MLAB.GUI.ApplicationSingleton.super.constructor.call(this)
        this.registerSignal("showLoadDialog")
        this.registerSignal("hideLoadDialog")
        this.registerSignal("modulesAreReady")
        this.registerSignal("allPluginsLoaded")
        this.registerSignal("creatingModuleContexts")
        this.registerSignal("moduleWindowCreated")
        this._logger = new MLAB.GUI.ApplicationLogger()
        this._areModuleContextsCreated = false
  
        this._renderSettings = null
        this._connectionSettings = null
        this._settings = new MLAB.GUI.ApplicationSettings()
        this._arguments = null
        
        this._authenticationManager = null
        
        this._plugins = []
        this._pendingPlugins = []
        this._pendingPluginEntries = []
      
        // Note: the order is important here, because of dependencies between the objects in these scripts, 
        //       so e.g. do not sort these modules alphabetically!
        this._coreScripts = ["core/Utilities.js", "core/RemoteMessages.js", "core/RemoteManager.js", 
                             "core/Event.js", "core/BaseFieldHandlerFactory.js", "core/Fields.js", "core/FieldExpressions.js",
                             "core/ItemModelHandler.js", "core/Module.js", "core/ModuleContext.js", 
                             "core/RemoteRenderingSlave.js", "core/RemoteRenderingBaseHandler.js",
                             "core/RemoteCallInterfaceHandler.js", "core/RenderSettings.js",
                             "core/BinaryDataStream.js"]
        this._guiScripts = ["gui/WidgetControlFactory.js", "gui/Controls.js", "gui/ButtonGroupControls.js", 
                            "gui/ItemModelViewControl.js", "gui/ModuleContextCreator.js", "gui/RemoteRenderingControl.js",
                            "gui/WindowController.js", "gui/WidgetFactory.js", "gui/Widgets.js",
                            "gui/IconItemViewControl.js", "gui/IconItemView.js",
                            "gui/AuthenticationManager.js"]
        document.body.onunload = this.callback("shutdown")
      },
      
      logger: function() { return this._logger },
      
      getSettings: function() { return this._settings },
      
      /** \fn MLAB.GUI.Application.showError
       * Displays an error as an alert.
       */
      showError: function(message) {
        alert(message) 
      },
      
      /** \fn MLAB.GUI.Application.getArguments
       * 
       * Returns the application arguments, which may be specified as url arguments or as
       * attributes of the arguments object that is passed to initialize().
       * 
       * The supported arguments are:
       * <table>
       *  <tr><td>debugRemoteMessages</td><td>Enables debugging remote messages. See \ref Debugging.</td></tr>
       *  <tr><td>diagnosis</td><td>Enables logging of diagnosis messages to the console. See \ref Debugging.</td></tr>
       *  <tr><td>plugins</td><td>Additional plugins to load (comma separated list)</td></tr>
       *  <tr><td>urlToMLABRoot</td><td>The root url to the MeVisLab packages</td></tr>
       *  <tr><td>showIDE</td><td>Show the MeVisLab IDE on loading</td></tr>
       * </ul>
       */
      getArguments: function() { return this._arguments },
      
      _prependResourcesBaseUrl: function(resourcesBaseUrl, resourceUrls) {
        var newUrls = []
        for (var i=0; i<resourceUrls.length; i++) {
          newUrls.push(resourcesBaseUrl + resourceUrls[i])
        }
        return newUrls
      },
      
      /** \fn MLAB.GUI.Application.initialize
       * 
       * Initializes the global application instance. The initialization callback is called
       * after all plugins have been loaded. The arguments is an optional map containing
       * any of the arguments that may also be specified as url arguments. See also getArguments().
       * 
  
       * \param arguments An optional object with attributes that are handled like page arguments.
       */
      initialize: function(args) {
        this._arguments = args
        this._settings.setupFromArguments(this._arguments)
  
        var resourcesBaseUrl = this._settings.getURLToMLABRoot() + 'MeVisLab/Private/Sources/Web/application/'
        var scripts = this._prependResourcesBaseUrl(resourcesBaseUrl + 'js/', this._coreScripts.concat(this._guiScripts))        
        var styles = [resourcesBaseUrl + 'css/default.css']
  
        this._resourceManager = new MLAB.Core.ResourceManager(this._settings.getURLToMLABRoot())
        this._resourceManager.loadResources(scripts, styles, this.callback("_handleCoreModulesLoaded"))
      },
    
      /** \fn MLAB.GUI.Application._handleCoreModulesLoaded
       * 
       * This is called after the core modules (core and gui)  have been loaded. It
       * creates singletons and starts loading the framework resources.
       */
      _handleCoreModulesLoaded: function() {
        if (this._settings.logDiagnosisMessages()) {
          this._logger.log("Core modules loaded.")
        }
        MLAB.Core.EventHandler.setLogger(this._logger)
        this._connectionSettings = new MLAB.Core.ConnectionSettings()
        this._connectionSettings.setupFromArguments(this._arguments)      
        this._renderSettings = new MLAB.Core.RenderSettings()
        this._renderSettings.setupFromArguments(this._arguments)
        // set the default authentication manager
        this.setAuthenticationManager(new MLAB.GUI.AuthenticationManager())
        
        this._loadPluginEntries()
      },
      
      _loadPluginEntries: function() {
        // load plugins
        this._pendingPluginEntries = this._settings.getPluginsToLoad()
        this._loadNextPluginEntry()
      },
      
      _addPluginEntry: function(pluginEntry, module) {
        this._pendingPluginEntries.push({url: pluginEntry, module: module})
      },
      
      _loadNextPluginEntry: function() { 
        if (this._pendingPluginEntries.length === 0) {
          this._allPluginEntriesLoaded()
        } else {
          var resource = new MLAB.Core.ScriptResource(this._pendingPluginEntries[0].url,
                                                       this._resourceManager.getResourcesBaseUrl())
          this._currentlyLoadingPluginEntry = this._pendingPluginEntries[0]
          this._pendingPluginEntries = this._pendingPluginEntries.slice(1)
          this._resourceManager.loadResources([resource.url()], [], this.callback("_loadNextPluginEntry"))
          // the plugin script must define a PluginBase derived class and load it into the application,
          // so the pluginEntry is one js file and the plugin specifies which other resource will be loaded
        }
      },
      
      loadPlugin: function(plugin) {
        var baseUrl = this._currentlyLoadingPluginEntry.url.split('/')
        var firstIndex = this._settings.getURLToMLABRoot().split('/').length-1
        baseUrl = this._resourceManager.getResourcesBaseUrl() + baseUrl.slice(firstIndex, baseUrl.length-1).join('/')
        plugin.setModule(this._currentlyLoadingPluginEntry.module)
        plugin.setResourcesBaseUrl(baseUrl)
        plugin.initialize(this._arguments)
        this._pendingPlugins.push(plugin)
      },
  
      _loadNextPlugin: function() {
        if (this._pendingPlugins.length === 0) {
          // modules may specify additional plugins, so do not call _allPluginsLoaded()
          // if the module contexts are not created
          if (this._areModuleContextsCreated) {
            this._allPluginsLoaded()
          } else {
            this._startCreatingModuleContexts()
          }
        } else {
          var plugin = this._pendingPlugins[0]
          this._pendingPlugins = this._pendingPlugins.slice(1)
          plugin.load(this.callback("_loadNextPlugin"))
        }
      },
      
      _allPluginEntriesLoaded: function() {
        this._loadNextPlugin()
      },
      
      showLoadDialog: function() {
        this.emit("showLoadDialog")
      },
      
      hideLoadDialog: function() {
        this.emit("hideLoadDialog")
      },
      
      /** \fn MLAB.GUI.Application._createModuleContextCreator
       * 
       */
      _createModuleContextCreator: function() {
        var moduleContextCreator = new MLAB.GUI.ModuleContextCreator()
        moduleContextCreator.setAuthenticationManager(this._authenticationManager)
        moduleContextCreator.setConnectionSettings(this._connectionSettings)
        moduleContextCreator.setDebugRemoteMessages(this._settings.debugRemoteMessages())
        moduleContextCreator.connect("hideLoadDialog", this, "hideLoadDialog")
        moduleContextCreator.setLogger(this._logger)
        moduleContextCreator.setLogDiagnosisMessages(this._settings.logDiagnosisMessages())
        moduleContextCreator.connect("modulesAreReady", this, "_modulesAreReady")
        moduleContextCreator.connectSignal("windowCreated", this, "moduleWindowCreated")
        moduleContextCreator.setRenderSettings(this._renderSettings)
        moduleContextCreator.connect("moduleProvidesPlugin", this, "_addPluginEntry")
        return moduleContextCreator
      },
      
      _startCreatingModuleContexts: function() {     
        // hide the body, so that the user does not see the building up of the DOM
        MLAB.GUI.addStyleSheetClass(document.body, "MLAB-GUI-HiddenDOMElement")
        this._moduleContextCreator = this._createModuleContextCreator()
        this.emit("creatingModuleContexts")
        if (this._settings.logDiagnosisMessages()) {
          this._logger.log("Creating module contexts.")
        }
        this._createModuleContexts()
      },
     
      _modulesAreReady: function() {
        this._areModuleContextsCreated = true
        // load plugin entries that are specified by modules,
        // calls _allPluginsLoaded() if no plugins if were specified
        // or after all plugins have been loaded
        this._loadNextPluginEntry()
      },
      
      /** \fn MLAB.GUI.Application._allPluginsLoaded
       * 
       * This is called when all plugins have been loaded. The application
       * initialization is now finished, so it calls the callback that was provided
       * in initialize().
       */
      _allPluginsLoaded: function() {
        if (this._settings.logDiagnosisMessages()) {
          this._logger.log("Plugins loaded.")
        }
        this.emit("allPluginsLoaded")
        this._moduleContextCreator.createGUIFromMDL()
        this._notifyModulesAreReady()
      },
      
      _createModuleContexts: function() {
        this._moduleContextCreator.createModuleContexts()
        if (!this._moduleContextCreator.hasAnyModule()) {
          this.showError("No modules exist in the html document")
        }
      },
      
      /** \fn MLAB.GUI.Application._notifyModulesAreReady
       * 
       * \param modules An array of MLABModule instances.
       */
      _notifyModulesAreReady: function() {
        try {
          this.emit("modulesAreReady")
        } catch(e) {
          this._logger.logException(e)
        }
        // show the body, all module panels are created now
        MLAB.GUI.removeStyleSheetClass(document.body, "MLAB-GUI-HiddenDOMElement")
        this._moduleContextCreator.notifyBodyIsVisible()
        
        if (this._settings.showIDE()) {
          this._moduleContextCreator.showIDEs()
        }
      },
      
      /** \fn MLAB.GUI.Application.shutdown
       * 
       * Shuts the application down by disconnecting all module contexts. 
       */
      shutdown: function() {
        this._moduleContextCreator.disconnectModules()
      },
      
      /** \fn MLAB.GUI.Application.destroyModule
       */
      destroyModule: function(moduleName) {
        this._moduleContextCreator.destroyModule(moduleName)
      },
      
      /** \fn MLAB.GUI.Application.createModule
       * \param moduleWindowCreatedCallback A callback
       */
      createModule: function(moduleType, moduleName) {
        return this._moduleContextCreator.createModule(moduleType, moduleName)
      },
      
      /** MLAB.GUI.Application.module
       * 
       * \param moduleName The module name.
       * \return Returns the MLABModule or null if it was not found.
       */
      module: function(moduleName) {
        return this._moduleContextCreator.getModule(moduleName)
      },
  
      setAuthenticationManager: function(authenticationManager) {
        if (this._authenticationManager !== null) {
          this._authenticationManager.disconnect("authenticateModuleContexts", this, "showLoadDialog")
        }
        this._authenticationManager = authenticationManager
        this._authenticationManager.setLogger(this._logger)
        this._authenticationManager.connect("authenticateModuleContexts", this, "showLoadDialog")
      },
    })
    
    MLAB.GUI.Application = new MLAB.GUI.ApplicationSingleton()
    if (creatingModuleContextsCallback) {
      MLAB.GUI.Application.connectCallback("creatingModuleContexts", creatingModuleContextsCallback)
    }
    MLAB.GUI.Application.initialize(args)
  }
  
  
  // return MLABApp here
  return {
    /** \fn MLABApp.runApplication()
     * 
     * This function runs the given application.
     * 
     * \param applicationName The application name. It is included in the URL for the web socket connection. It is evaluated
     *                        by the MeVisLabWorkerService when it runs in proxy mode, otherwise it is ignored.
     * \param appliationMacro The name of the application macro module.
     * \param arguments A dictionary containing arguments for the settings. See MLAB.GUI.ApplicationSettings, MLAB.Core.RenderSettings,
     *                  MLAB.Core.ConnectionSettings, and MLAB.GUI.PluginBase.initialize() for more information.
     */
    runApplication: function(applicationName, applicationMacro, args) {
      this._applicationName = applicationName
      this._applicationMacro = applicationMacro
      this._applicationMacroName = applicationMacro
      if (args) {
        if ((typeof(args["application"]) !== "undefined") &&
            (args["application"] !== this._applicationName)) {
          throw "MLABApp.runApplication(): the given application name does not match the application setting"
        }
      } else {
        args = {}
      }
      args["application"] = this._applicationName
      if ("moduleName" in args) {
        this._applicationMacroName = args['moduleName']
      }
      var creatingModuleContextsCallback = this._createApplicationMacro.bind(this) 
      this.initialize(creatingModuleContextsCallback, args)
    },
    
    _createApplicationMacro: function() {
      MLAB.GUI.Application.createModule(this._applicationMacro, this._applicationMacroName)
    },

    autodetectURLToMLABRoot: function(args) {
      var urlToMLABRoot
      if ("urlToMLABRoot" in args) {
        urlToMLABRoot = args["urlToMLABRoot"]
      } else {
        var parts = window.location.pathname.split('/')
        if (parts.length > 3 && parts[1] === "Applications") {
          urlToMLABRoot = "/Applications/" + parts[2] + "/"   // proxy mode
        } else {
          urlToMLABRoot = "/Packages/"  // non-proxy mode
        }
      }
      if (urlToMLABRoot[urlToMLABRoot.length-1] !== '/') { urlToMLABRoot = urlToMLABRoot+'/' }
      return urlToMLABRoot
    },
    
    initialize: function(creatingModuleContextsCallback, args) {
      var appArguments = this._parseArguments(args)
      
      this._urlToJSResources = this.autodetectURLToMLABRoot(appArguments) + "MeVisLab/Private/Sources/Web/application/js/"
   
      this._bootstrapScripts = ["core/Namespace.js", "core/Object.js", "core/ResourceLoader.js", 
                                "core/SystemInfo.js", "gui/Namespace.js", "core/Timer.js"]
      this._bootstrapFinishedCallback = (function() {
        if (document.readyState !== "complete") {
          window.setTimeout(this._bootstrapFinishedCallback.bind(this), 100)
        } else {
          this._setupApplication(creatingModuleContextsCallback, appArguments)
        }
      }).bind(this)
  
      this._bootstrap()
    },
  
    /** \fn MLABApp._parseArguments
     * 
     * Parse the page arguments.
     * 
     * \param arguments An optional object with attributes that are handled like page arguments. 
     */
    _parseArguments: function(args) {
      var tmp = window.location.href.split('?')
      tmp = tmp.splice(1, tmp.length-1)
      tmp = tmp.join('?').split('&')
      var cleanArgs = new Object()
      for (var i=0; i<tmp.length; i++) {
        var items = tmp[i].split('=')
        if (items.length > 1) {
          cleanArgs[items[0]] = unescape(items.splice(1, items.length-1).join('='))
        } else {
          cleanArgs[tmp[i]] = '1'
        }
      }
      if (typeof(args) !== "undefined") {
        for (key in args) {
          cleanArgs[key] = args[key]
        }
      }
      return cleanArgs
    },
      
    _loadNextBootstrapScript: function() {
      if (this._bootstrapScripts.length == 0) {
        this._bootstrapFinishedCallback()
        return
      }
      var script = this._bootstrapScripts[0]
      this._bootstrapScripts = this._bootstrapScripts.slice(1)
      var element = document.createElement("script")
      element.setAttribute("type", "text/javascript")
      element.src = this._urlToJSResources + script
      element.onload = this._loadNextBootstrapScript.bind(this)
      element.onerror = this._loadNextBootstrapScript.bind(this)
      document.getElementsByTagName("head")[0].appendChild(element)
    },
      
    _bootstrap: function() {
      this._loadNextBootstrapScript()
    },
  
    _setupApplication: mlabSetupApplication,
  }
})()
