Array.prototype.remove = function(element) {
  var idx = this.indexOf(element);
  if (idx != -1) {
    return this.splice(idx, 1);
  }
  return null;
}





//=============================================================================
// MLABSystemInfo
//=============================================================================
function MLABSystemInfo() {
  // Returns the version of Internet Explorer or a -1
  // (indicating the use of another browser).
  this.getInternetExplorerVersion = function() {
    var rv = -1; // Return value assumes failure.
    if (navigator.appName == 'Microsoft Internet Explorer') {
      var ua = navigator.userAgent;
      var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
      if (re.exec(ua) != null) {
        rv = parseFloat( RegExp.$1 );
      }
    }
    return rv;
  };

  // since IE9 might run in compatibility mode, we check >=7
  this.isIE9 = function() {
    return this.getInternetExplorerVersion()>=7;
  };

  // check of IOS devices
  this.isIOS = function() {
    return (/iphone|ipad|ipod/i.test(navigator.userAgent.toLowerCase()));
  };
  
  this.isMacOS = function() {
    return navigator.platform.indexOf("Mac") >= 0;
  };
  
  this.isLinux = function() {
    return navigator.platform.indexOf("Linux") >= 0;
  };
  
  this.isWindows = function() {
    return navigator.platform.indexOf("Win") >= 0;
  };
}


//=============================================================================
// MLABResource
//=============================================================================
function MLABResource(type, url, attributes) {
  this.type = type;
  this.url = url;
  this.attributes = attributes;
}


//=============================================================================
// MLABScriptResource
//=============================================================================
function MLABScriptResource(name) {
  var url = "/static/"+name;
  if (!name.match(/(^(http|https|file):.*)/i)) {
      //url = "/static/js/" + name.replace(".", "/") + ".js";
  }
  this.inheritFrom = MLABResource;
  this.inheritFrom("script", url, {"type": "text/javascript"});
}


//=============================================================================
// MLABCssResource
//=============================================================================
function MLABCssResource(name) {
  var url = "/static/"+name;
  if (!name.match(/(^(http|https|file):.*)/i)) {
    //url = "/static/css/" + name.replace(".", "/") + ".css";
  }
  this.inheritFrom = MLABResource;
  this.inheritFrom("link", url, {"rel": "stylesheet", "type": "text/css"});
}


//=============================================================================
// MLABResourceLoader
//=============================================================================
function MLABResourceLoader(resourceList, loadingFinishedCallback) {
  var self = this;
  
  this._pendingResources = resourceList;
  this._loadingFinishedCallback = loadingFinishedCallback;
  
  this.resourceLoaded = function(resource) {
    self._pendingResources.remove(resource);
    if (self._pendingResources.length == 0) {
      self._loadingFinishedCallback();
    }
  };
  
  this.loadResource = function(resource) {
    try {
      var element = document.createElement(resource.type);
      for (var attribute in resource.attributes) {
        element.setAttribute(attribute, resource.attributes[attribute]);
      }
      
      if (resource.type != "link") {
        element.src = resource.url;
        element.onload = function() {
          self.resourceLoaded(resource);
        };
        element.onerror = function() {
          self.resourceLoaded(resource);
        };
        document.getElementsByTagName("head")[0].appendChild(element);
      } else {
        // css links do not emit onload
        element.href = resource.url;
        document.getElementsByTagName("head")[0].appendChild(element);
        self.resourceLoaded(resource);
      }
    } catch(e) {      
      gApp.logException(e);
    }
  };
  
  this.loadResources = function() {
    for (var i=0; i<self._pendingResources.length; i++) {
      // TODO: can the array be modified because the onload handler removes loaded resources
      // while this loop is active, or does this loop prevent event handling?
      self.loadResource(self._pendingResources[i]);
    }
  };
}


//=============================================================================
// MLABResourceManager
//=============================================================================
function MLABResourceManager() {
  var self = this;
  
  this._loadedScriptModules = new Array();
  this._loadedCssModules = new Array();
  this._activeResourceLoader = null;
  
  this.loadResources = function(scriptModules, cssModules, loadingFinishedCallback, loader) {
    var resourceList = new Array();
    
    for (var i=0; i<scriptModules.length; i++) {
      if (self._loadedScriptModules.indexOf(scriptModules[i]) == -1) {
        self._loadedScriptModules.push(scriptModules[i]);
        resourceList.push(new MLABScriptResource(scriptModules[i]));
      }
    }
    
    for (var i=0; i<cssModules.length; i++) {
      if (self._loadedCssModules.indexOf(cssModules[i]) == -1) {
        self._loadedCssModules.push(cssModules[i]);
        resourceList.push(new MLABCssResource(cssModules[i]));
      }
    }
    
    // TODO: can this happen?
    if (self._activeResourceLoader != null) {
      alert("resource loader already active");
    }
    
    if (!loader) {
      loader = MLABResourceLoader;
    }
    self._activeResourceLoader = new loader(resourceList, function() { self.resourcesLoaded(); loadingFinishedCallback(); });
    self._activeResourceLoader.loadResources();
  };
  
  this.resourcesLoaded = function() {
    delete self._activeResourceLoader;
    self._activeResourceLoader = null;
  };
}


//=============================================================================
// MLABApplication
//=============================================================================
function MLABApplication() {
  var self = this;
  app = this;
  
  this._loginRequired = false;
  
  this._pendingModuleContexts = []; // contains all newly created module contexts 
                                    // until they are connected to the server
  this._moduleContexts = [];
  this._nextModuleContextID = 0;
  
  this._showDiagnosisPanel = false;
  this.showDiagnosisPanel = function() { return self._showDiagnosisPanel; }

  this._useStreaming = true;
  this.shouldUseStreaming = function() { return self._useStreaming; }
    
  this._isReady = false;  
  this.isReady = function() { return self._isReady; }
  
  this.getSystemInfo = function() { return self._systemInfo; };
  this.showError = function(message) { alert(message); };
  
  this._lastWidgetControlID = 0;  
  this.getNextWidgetControlID = function() {
    var id = self._lastWidgetControlID;
    self._lastWidgetControlID += 1;
    return id;
  };
  
  this._initializeCustomApplication = null;  
  this.setInitializeCustomApplicationCallback = function(callback) {
    self._initializeCustomApplication = callback;
  };
  
  this._initializationFinishedCallback = null;
  
  this._authentication = ["",""];
  this.getAuthentication = function() { return self._authentication; };
  
  this._urlToMLABRoot = '';
  this.urlToMLABRoot = function() {
    return self._urlToMLABRoot;
  };
  
  this.setModuleContextsReadyCallback = function(callback) {
    self._moduleContextsReadyCallback = callback;
  }
  
  this.getModuleContext = function(moduleContextId) {
    for (var i=0; i<self._moduleContexts.length; i++) {
      if (self._moduleContexts[i].getDiv().id == moduleContextId) {
        return self._moduleContexts[i];
      }
    }
    return null;
  };
  
  this.showIDE = function(moduleContextId) {
    var moduleContext = null;
    for (var i=0; i<self._moduleContexts.length; i++) {
      if (self._moduleContexts[i].getDiv().id == moduleContextId) {
        moduleContext = self._moduleContexts[i];
        break;
      }
    }
    if (moduleContext) {
      moduleContext.showIDE();
    } else {
      self.logError("No such module context found: " + moduleContextId);
    }
  };
  
  this.getArguments = function() { return self._args; }
  this.debugRemoteMessages = function() { return ("debug_remote_messages" in self._args); }
  this.isFieldSyncronizationProfilingEnabled = function() { return ("enable_field_sync_profiling" in self._args); }
  
  this.initialize = function(initializationFinishedCallback) {
    self._initializationFinishedCallback = initializationFinishedCallback;
    function parsePageArguments() {
      var tmp = window.location.href.split('?');
      tmp = tmp.splice(1, tmp.length-1);
      tmp = tmp.join('?').split('&');
      var args = new Object();
      for (var i=0; i<tmp.length; i++) {
        var items = tmp[i].split('=');
        if (items.length > 1) {
          args[items[0]] = unescape(items.splice(1, items.length-1).join('='));
        } else {
          args[tmp[i]] = '1';
        }
      }
      return args;
    }

    self._args = parsePageArguments();
    
    if ("diagnosis" in self._args) { self._showDiagnosisPanel = true; }    
    if ("mlab_root" in self._args) { self._urlToMLABRoot = self._args["mlab_root"]; }
    else { 
      // assume that MLAB_ROOT is http://server/Packages
      self._urlToMLABRoot = window.location.protocol + "//" + window.location.host + "/Packages";
    }
    
    if ("streaming" in self._args) { self._useStreaming = (self._args["streaming"] != "0"); }    
    if (!("framework" in self._args)) { self._args["framework"] = "jQueryMobile"; }    

    // Setup streaming settings from URL params:
    this._renderQualitySettings = {maxPendingImages:3, jpegQuality:75};
    if ("maxPendingImages" in self._args) {
      this._renderQualitySettings.maxPendingImages = parseInt(self._args["maxPendingImages"]);
    }    
    if ("jpgQuality" in self._args) {
      this._renderQualitySettings.jpgQuality = parseInt(self._args["jpgQuality"]);
    }    
    if ("minUpdateDelayInMs" in self._args) {
      this._renderQualitySettings.minUpdateDelayInMs = parseInt(self._args["minUpdateDelayInMs"]);
    }    
    if ("maxUpdateDelayInMs" in self._args) {
      this._renderQualitySettings.maxUpdateDelayInMs = parseInt(self._args["maxUpdateDelayInMs"]);
    }    
    this.getRenderQualitySettings = function() { return self._renderQualitySettings; }

    var styleModule = "css/default.css";
    if ("style" in self._args) { styleModule = self._args["style"]; }
    
    var scriptModules = ["js/core/Utilities.js", "js/core/Controls.js", 
                         "js/core/RemoteMessages.js", "js/core/RemoteManager.js", "js/core/Event.js",
                         "js/core/ItemModelHandler.js", "js/core/ItemModelViewControl.js",
                         "js/core/ModuleContext.js"];
    var cssModules = [styleModule];
    self._resourceManager = new MLABResourceManager();
    self.loadResources(scriptModules, cssModules, self.coreModulesLoaded);
  };
  
  this.loadResources = function(scriptModules, cssModules, callback) {
    self._resourceManager.loadResources(scriptModules, cssModules, callback);
  };
  
  this.coreModulesLoaded = function() {
    self.log("Core modules loaded.");    
    self.loadResources(["js/"+self._args["framework"] + "/Application.js"], [], self.frameworkModuleLoaded);
  };
  
  this.frameworkModuleLoaded = function() {
    self.log("Framework module '" + self._args["framework"] + "' loaded.");
    self.loadFrameworkModules(self.frameworkLoaded);
  };
    
  this.frameworkLoaded = function() {    
    self.log("Framework loaded.");
    self._systemInfo = new MLABSystemInfo();
    self._eventHandler = new MLABEventHandler();
    self._initializationFinishedCallback();
  };
  
  this.createModuleContext = function(moduleDiv, isLoginRequired) {
    self.log("Creating module context for " + moduleDiv.id);
    try {
      var moduleContext = new MLABModuleContext(moduleDiv, self._nextModuleContextID, isLoginRequired);
      self._nextModuleContextID += 1;
      self._moduleContexts.push(moduleContext);
      self._pendingModuleContexts.push(moduleContext);
      self.registerWidgetControls(moduleContext);
      moduleContext.setModuleContextReadyCallback(self._handleModuleContextReady);
      return moduleContext;
    } catch (e) {
      self.logException(e);
    }
  };
  
  this._handleModuleContextReady = function(moduleContext, moduleCreationStatus) {    
    self._pendingModuleContexts.remove(moduleContext);
    
    // collect all unauthenticated module contexts. if all contexts finished
    // connecting, then re-request authentication and retry those contexts
    if (moduleCreationStatus == 4) {
      if (!self._unauthenticatedModuleContexts) {
        self._unauthenticatedModuleContexts = [];
      }
      self._unauthenticatedModuleContexts.push(moduleContext);
    }
    
    if (self._pendingModuleContexts.length == 0) {
      if (self._unauthenticatedModuleContexts && self._unauthenticatedModuleContexts.length > 0) {
        self._loginRequired = true;
        self.hideLoadDialog();
        
        // authentication failed, re-request authentication data
        self.requestAuthentication(function() {
          self.showLoadDialog();
          // connect again
          for (var i=0; i<self._unauthenticatedModuleContexts.length; i++) {
            var mc = self._unauthenticatedModuleContexts[i];
            self._pendingModuleContexts.push(mc);
            mc.authenticate();
          }
          delete self._unauthenticatedModuleContexts;
        });
        
      } else {
        // all contexts are authenticated or do not need any authentication
        if (self._moduleContextsReadyCallback) {
          try {
            self._moduleContextsReadyCallback();
            // authentication data is no more required
            delete self._authentication;            
          } catch(e) {
            self.logException(e);
          }
        }
        self._flushPendingLogMessages();
        self._flushPendingLogErrors();
        self._flushPendingLogExceptions();
        self.body.style.visibility = "visible";
        for (var i=0; i<self._moduleContexts.length; i++) {
          self._moduleContexts[i].setBodyIsVisible();
        }
      }
    }
  };
  
  this.getRemoteRenderingControlAndModuleContext = function(target) {
    var control = null;
    var moduleContext = null;
    for (var i=0; i<self._moduleContexts.length; i++) {
      control = self._moduleContexts[i].getRemoteRenderingControl(target);
      if (control) {
        moduleContext = self._moduleContexts[i];
        break;
      }
    }
    return {"control": control, "moduleContext": moduleContext};
  };
  
  this.getEventHandler = function() { return self._eventHandler; };
  
  this.bodyReady = function() {
    document.body.onunload = self.shutdown;
    try {
      self.frameworkBodyReady();
    } catch (e) {
      self.logException(e);
    }
    
    var finishBodyReady = (function() {
      self.body = document.createElement("div");
      self.body.id = "body";
      self.body.style.visibility = "hidden";
      document.body.appendChild(self.body);
      
      if (self._initializeCustomApplication) {
        try {
          self._initializeCustomApplication();
        } catch(e) {
          self.logException(e);
        }
      }
      
      if (self.customApplicationFinishedInitialization) {
        try {
          self.customApplicationFinishedInitialization();
        } catch (e) {
          self.logException(e);
        }
      }
      
      function createModuleContextsHelper(moduleDivName, isLoginRequired) {
        var moduleDivs = document.getElementsByName(moduleDivName);
        if (moduleDivs.length > 0) {
          var moduleContexts = [];
          for (var i=0; i<moduleDivs.length; i++) {
            moduleContexts.push(self.createModuleContext(moduleDivs[i], isLoginRequired));
          }
          for (var i=0; i<moduleContexts.length; i++) {
            if (moduleContexts[i]) {
              moduleContexts[i].connect(); 
            }
          }
          return true;
        }
        return false;
      }
      
      var anyModuleDivCreated = createModuleContextsHelper("runmacro_authenticated", true);
      self._loginRequired = anyModuleDivCreated;
      if (createModuleContextsHelper("runmacro", false)) { anyModuleDivCreated = true; }
      if (!anyModuleDivCreated) {
        self.showError("No module divs exist in the html document");
      }
      
      self._isReady = true;
    });
    
    if (self._loginRequired) {
      self.requestAuthentication(finishBodyReady);
    } else {
      finishBodyReady();
    }
  };
  
  this.shutdown = function() {
    for (var i=0; i<self._moduleContexts.length; i++) {
      self._moduleContexts[i].disconnect();
    }
  };
  
  this.createModuleContextDiv = function(moduleName, divId, isLoginRequired) {
    var div = document.createElement("div");
    div.id = divId;
    if (isLoginRequired) {
      div.setAttribute("name", "runmacro_authenticated");
    } else {
      div.setAttribute("name", "runmacro");
    }
    div.setAttribute("class", moduleName);
    return div;
  };
  
  this.appendDiagnosisMessage = function(message) { self.showError("app.appendDiagnosisMessage() not implemented by framework"); };
  
  this.log = function(message) {
    if (self._moduleContexts.length == 0) {
      if (!self._pendingLogMessages) { self._pendingLogMessages = []; }
      self._pendingLogMessages.push(message);
      if (console) { console.log(message); }
    } else {
      for (var i=0; i<self._moduleContexts.length; i++) {
        self._moduleContexts[i].log(message);
      }
    }
  };
  
  this._flushPendingLogMessages = function() {
    if (self._pendingLogMessages && (self._moduleContexts.length > 0)) {
      for (var i=0; i<self._pendingLogMessages; i++) {
        for (var j=0; j<self._moduleContexts.length; j++) {
          self._moduleContexts[j].log(self._pendingLogMessages[i]);
        }
      }
      delete self._pendingLogMessages;
    }
  };
  
  this.logError = function(message) {
    if (self._moduleContexts.length == 0) {
      if (!self._pendingLogErrors) { self._pendingLogErrors = []; }
      self._pendingLogErrors.push(message);
      if (console) { console.log(message); }
    } else {
      for (var i=0; i<self._moduleContexts.length; i++) {
        self._moduleContexts[i].logError(message);
      }
    }
  };
  
  this._flushPendingLogErrors = function() {
    if (self._pendingLogErrors && (self._moduleContexts.length > 0)) {
      for (var i=0; i<self._pendingLogErrors; i++) {
        for (var j=0; j<self._moduleContexts.length; j++) {
          self._moduleContexts[j].log(_pendingLogErrors[i]);
        }
      }
      delete self._pendingLogErrors;
    }
  };
  
  this.logException = function(exception) {
    if (self._moduleContexts.length == 0) {
      if (!self._pendingLogExceptions) { self._pendingLogExceptions = []; }
      self._pendingLogExceptions.push(exception);
      if (console) { console.log(exception); }
    } else {
      for (var i=0; i<self._moduleContexts.length; i++) {
        self._moduleContexts[i].logException(exception);
      }
    }
  };
  
  this._flushPendingLogExceptions = function() {
    if (self._pendingLogExceptions && (self._moduleContexts.length > 0)) {
      for (var i=0; i<self._pendingLogExceptions; i++) {
        for (var j=0; j<self._moduleContexts.length; j++) {
          self._moduleContexts[j].log(self.__pendingLogExceptions[i]);
        }
      }
      delete self._pendingLogExceptions;
    }
  };
  
  this.registerWidgetControls = function(moduleContext) { 
    mlabThrowException("registerWidgetControls() is not implemented"); 
  };
  
  this.requestAuthentication = function(authenticatedCallback) {
    mlabThrowException("requestAuthentication() is not implemented");
  };
  
  this.showLoadDialog = function() {
    mlabThrowException("showLoadDialog() is not implemented");
  };
  
  this.hideLoadDialog = function() {
    mlabThrowException("hideLoadDialog() is not implemented");
  };
}


//=============================================================================
// The global application variable
//=============================================================================
gApp = new MLABApplication();

