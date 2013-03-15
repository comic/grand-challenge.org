
function ComicViewer2D(domElementId, options) {
  var self = this;
  
  // May contain:
  // host: MeVisLab WorkerService IP
  // port: websocket port

  this._options = {'host': "134.102.230.19", 'port': 4115, 'width': 400, 'height': 300, 'deferredLoad':false, 'extensionFilter':"", 'showBrowser':1};
  jQuery.extend(this._options, options);
  this._elementId = domElementId;
  this._elementSelector = "#"+domElementId;
  this._mlabModuleName = "DIAGRemoteViewport"
  this._isInit = false;
    
  this._readyCallback = null;
  this._measurementsChangedCallback = null;
  this._errorCallback = null;
  this._logCallback = null;
  this.ctx = null;

  this.init = function(readyCallback){
    var element = document.createElement("script");
    element.src = "/static/js/mlabRemote/Application.js";
    element.onload = function() {
      
      if (!self._options['showBrowser']) {
        $(self._elementSelector + " .MLABMLItemModelViewControl").hide();
      }
      if (self._options['deferredLoad']) {
        $(self._elementSelector).html("<br/><br/>Click to load image viewer");
        $(self._elementSelector).css("text-align", "center");
        $(self._elementSelector).css("background", "nil");
        $(self._elementSelector).css("background-color", "#333");
        $(self._elementSelector).css("color", "white");
        $(self._elementSelector).css("padding", "10px");
        $(self._elementSelector).click(function () {
            $(self._elementSelector).html("");
            self._mlabRemoteLoaded();
            $(self._elementSelector).css("background", "nil");
            $(self._elementSelector).css("background-color", "transparent");
            $(self._elementSelector).css("color", "black");
            $(self._elementSelector).css("padding", "0px");
            $(self._elementSelector).off('click');
            })
      } else {
        self._mlabRemoteLoaded();
      }
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
    $(self._elementSelector).append($("<div style='width:"+this._options['width']+"px; height:"+this._options['height']+"px' name='runmacro' id='"+this._mlabModuleName+"' class='"+this._mlabModuleName+"'></div>"));
    if (self._options.host) {
      self._gApp.setWebSocketHostName(self._options.host)
    }
    if (self._options.port) {
      self._gApp.setWebSocketPort(self._options.port)
    }
    options = {"framework": "jQueryUI",
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
    self.ctx = moduleCtx;
    if (self._readyCallback) {
      self._readyCallback();
    }
    ctrl = $(self._elementSelector + " .MLABRemoteRenderingControl")[0]
    //ctrl.mlabControl.resizeViewport(self._options['width'], self._options['height']);
    if (self._options['extensionFilter']) {
        self.setExtensionFilter(self._options['extensionFilter']);
    }
  }
  
  this.setDataRoot = function(rootPath) {
    self.ctx.sendGenericRequest("setDataRoot", [rootPath], function(arguments) {
      // process return value
    });
  }
  
  this.setExtensionFilter = function(extensionFilter) {
    self.ctx.sendGenericRequest("setExtensionFilter", [extensionFilter], function(arguments) {
      // process return value
    });
  }
  
  this.loadImage = function(imageFilename){
    self.ctx.sendGenericRequest("loadImage", [imageFilename], function(arguments) {
      // process return value
    });
  }
  
  this.setErrorCallback = function(callback) {
    self._errorCallback = callback;
  }

  this.setLogCallback = function(callback) {
    self._logCallback = callback;
  }
}

