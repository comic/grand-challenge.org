/*
* Author : Alex
*
* Jquery wrapper object to show a DIAG viewer using MeVis Web Rendering.
* This object get instantiated and manipulated in html pages showing 
* this viewer 
*/

function COMICWebWorkstationWrapper(domElementId) {
  var self = this;
  
  this._elementId = domElementId;
  this._elementSelector = "#"+domElementId;
  this._mlabModuleName = "COMICWebWorkstation";
  this._module = null;
  this._isInFullscreen = false;
  this._nonFullscreenSize = {"width":null,"height":null};

  // Callback executed when loading is complete
  this.comicLoadingFinishedCB = function () {
    console.log("[comicLoadingFinishedCB]: Loading finished signal received.");
    this.module = MLAB.GUI.Application.module(this._options['moduleName'])
  }
  
  // Callback for log messages from the client
  this.comicLoggingCB = function (logMessage) {
    console.log("[comicLoggingCB] Log message received from viewer: " + logMessage);
  }
    
  // Callback for error log messages from the client
  this.comicErrorLoggingCB = function (logMessage) {
    console.log("[comicErrorLoggingCB] Error log message received from viewer: " + logMessage);
  }
    
  // used for logging within this file only
  this.log = function (msg) {
    msg = "[HTML] " + msg;
    console.log(msg);
    this.comicLoggingCB(msg);
  }
  
  this.init = function(options){
    //var urlToMLABRoot = this._appName
    //urlToMLABRoot = "/Applications/" + this._appName;
    //urlToMLABRoot = "/static/js/mlabRemote/"
    
    this._options = {
      "moduleName": this._elementId,
      "webSocketHostName": "ANKH",
      "webSocketPort": 4114,     
      "debugRemoteMessages" : "", 
      "diagnosis" : "",                                            // Will enable the MeVisLab output in the browser console. Cannot be set to "urlToMLABRoot" : urlToMLABRoot,
      "ComicView2D_loadingFinishedCallback": this.comicLoadingFinishedCB, // Callback executed when the viewer is fully loaded 
      "ComicView2D_loggingCallback": this.comicLoggingCB,                 // Callback for info logging. Will only include processing server logging when 'diagnosis' is enabled.
      "ComicView2D_errorCallback": this.comicErrorLoggingCB,              // Callback for error logging. Will also contain server error info.
      "ComicView2D_viewerContainerId": this._elementId,               // id of the root HTML div element
      'path': 'C:/DemoData',
      'width': 400,
      'height': 300,
      'deferredLoad': false,
      'extensionFilter':"",
      'showBrowser':1,
    };
    jQuery.extend(this._options, options);
  
    this.log("Using appName: " + this._appName);
    this.log("Using urlToMLABRoot: " + this._options['urlToMLABRoot']);
    
	MLABApp.initialize(function() { self._mlabApploaded() } ,self._options);
	
	$(window).resize(function() {
		if(self._isInFullscreen){
			self._resizeWindowTo(window.innerWidth,window.innerHeight);
		};		
	});	
	
	$(window).keyup(function(event) {
		if(event.which == 27){ //27 == escape key
			self.leaveFullscreen();
		}		
	});
  };
  
  this._mlabApploaded = function(){
	var container = $(this._elementSelector)
	container.resizable({ ghost: true, helper: "ui-resizable-helper" })
	         .on( "resizestop", function( event, ui ) {
	         	if (self._module) {
				    var viewerControl = self._module.control("viewer")
				    viewerControl.resizeViewport(ui.size.width, ui.size.height);
	         	}
	         });
	// does not work atm because the MWT does not allow lazy module creation
    if (false){//this._options['deferredLoad']) {
      container.html("<br/><br/>Click to load image viewer");
      container.css("text-align", "center");
      container.css("background", "nil");
      container.css("background-color", "#333");
      container.css("color", "white");
      container.css("padding", "10px");
      container.click(function () {
        container.html("");
	    self._createModule();
        container.css("background", "nil");
        container.css("background-color", "transparent");
        container.css("color", "black");
        container.css("padding", "0px");
        container.off('click');
      })
    } else {
      self._createModule();
    }
  }

  this._createModule = function() {
    MLAB.GUI.Application.connectCallback("modulesAreReady", function(){
  	  var container = $(self._elementSelector)
	  self._module = MLAB.GUI.Application.module(self._mlabModuleName);
	  self._module.showPanel(null, container[0]);
	  self.setDataRoot(self._options["path"])
	  var viewerControl = self._module.control("viewer")
	  viewerControl.resizeViewport(self._options.width, self._options.height);
	})
	MLAB.GUI.Application.createModule(self._mlabModuleName);
  }
  
  this.gotoFullscreen = function(){
  	if(!this._isInFullscreen){
	  	this._isInFullscreen = true;
	  	var container = $(self._elementSelector);
	  	this._nonFullscreenSize.width = container.width();
	  	this._nonFullscreenSize.height = container.height();  	
	  	this._resizeWindowTo(window.innerWidth,window.innerHeight);
	  	container.css("position", "fixed");	  	
	  	container.css("top","0");
  		container.css("left","0");
  		$("html").css("overflow","hidden");
  		
  		$("#messagescontainer").hide()
  							   .css("z-index",1000)
  							   .html("<div class = 'messagelist'>Entering fullscreen mode. Press escape to exit</div>")
  							   .fadeIn(400,function(){
  							   		setTimeout(function(){
  							   			$("#messagescontainer").fadeOut()
  							   		},4000)
  							   	})	  	
	}	
  }
  
  this.leaveFullscreen = function(){
  	if(this._isInFullscreen){  		
  		this._isInFullscreen = false;  		
  	    this._resizeWindowTo(this._nonFullscreenSize.width,this._nonFullscreenSize.height);
  	    var container = $(self._elementSelector);
  	    container.css("position", "");
  	    $("html").css("overflow","");
  	}  	
  }
  
  this._resizeWindowTo = function(width,height){  	
  	var container = $(self._elementSelector)  	  	  	
  	container.css("width",width);
  	container.css("height",height);  	  
  	var viewerControl = self._module.control("viewer")
	viewerControl.resizeViewport(width,height);
  }; 
  
  //== convenience functions for calling methods on the MLab module itself ============
  
  this.setDataRoot = function(rootPath) {
    module = MLAB.GUI.Application.module(self._mlabModuleName);
    module.sendGenericRequest("setDataRoot", [rootPath], function(arguments) {
      // process return value
    });
  }
  
  this.setExtensionFilter = function(extensionFilter) {
	module = MLAB.GUI.Application.module(self._mlabModuleName);
    module.sendGenericRequest("setExtensionFilter", [extensionFilter], function(arguments) {
      // process return value
    });
  }
 
}

