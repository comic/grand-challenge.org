
function ComicViewer2D(domElementId, options) {
  var self = this;
  
  // May contain:
  // host: MeVisLab WorkerService IP
  // port: websocket port
  this._options = options || {'host': "134.102.230.19", 'port': 4115};
  this._elementId = domElementId;
  this._elementSelector = "#"+domElementId;
  this._mlabModuleName = "DIAGRemoteViewport"
  this._isInit = false;
    
  this._readyCallback = null;
  this._measurementsChangedCallback = null;
  this._errorCallback = null;
  this._logCallback = null;

  this.init = function(readyCallback){
    var element = document.createElement("script");
    element.src = "/static/js/mlabRemote/Application.js";
    element.onload = function() {
      self._mlabRemoteLoaded();
    };
    element.onerror = function() {
      self._mlabRemoteLoadError();
    };
    document.getElementsByTagName("head")[0].appendChild(element);
    self._readyCallback = readyCallback;
  }
  
  this._mlabRemoteLoaded = function() {
    if (self._isInit) return;
    self._isInit = true;
    self._gApp = gApp;
    $(self._elementSelector).append($("<div name='runmacro' id='"+this._mlabModuleName+"' class='"+this._mlabModuleName+"'></div>"));
    if (self._options.host) {
      self._gApp.setWebSocketHostName(self._options.host)
    }
    if (self._options.port) {
      self._gApp.setWebSocketPort(self._options.port)
    }
    options = {"framework": "jQueryMobile",
               "streaming": "1",
               "jsResourcesRoot": "/static/js/mlabRemote/",
               "cssResourcesRoot": "/static/css/",
               "style": "fme.viewer2d.css"};
    self._gApp.initialize(self._internalResourcesLoaded, options);
  }
  
  this._mlabRemoteLoadError = function () {
    
  }
  
  this._internalResourcesLoaded = function() {
    // Load custom javascript and css files
    var scriptModules = [];
    var cssModules = [];
    console.log("calling loadresources")
    //self._gApp.loadResources(scriptModules, cssModules, self._resourcesLoaded);
    self._gApp.bodyReady(self._moduleWindowCreatedCallback);
  }
  
  this._resourcesLoaded = function () {
    //self._gApp.bodyReady(self._moduleWindowCreatedCallback);
  }
  
  this._moduleWindowCreatedCallback = function (moduleCtx) {
    if (self._readyCallback) {
      self._readyCallback();
    }
  }
  
  this.setDataRoot = function(rootPath) {
    ctx = self._gApp.getModuleContext(this._mlabModuleName);
    ctx.sendGenericRequest("setDataRoot", rootPath, function(arguments) {
      // process return value
    });
  }
  
  this.loadImage = function(imageFilename){
    ctx = self._gApp.getModuleContext(this._mlabModuleName);
    ctx.sendGenericRequest("loadImage", [imageFilename], function(arguments) {
      // process return value
    });
  }
  
  this.getMeasurements = function(callback){
    ctx = self._gApp.getModuleContext(this._mlabModuleName);
    ctx.sendGenericRequest("getMeasurements", [imageUID], function(measurementsJSON) {
      callback(JSON.parse(measurementsJSON)); 
    });
  }
  
  this.setMeasurementChangedCallback = function(callback) {
    self._measurementsChangedCallback = callback;
  }

  this.setErrorCallback = function(callback) {
    self._errorCallback = callback;
  }

  this.setLogCallback = function(callback) {
    self._logCallback = callback;
  }
}

