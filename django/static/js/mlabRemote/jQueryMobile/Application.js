//=============================================================================
// JQMDiagnosisPanel
//=============================================================================
/*function YUIDiagnosisPanel() {
  var self = this;
  
  var div = document.getElementById("DiagnosisPanel"); 
  if (!div) {
    div = document.createElement("div");
    div.id = "DiagnosisPanel";
    gApp.body.appendChild(div); 
 
    this._panel = new YAHOO.widget.Panel("DiagnosisPanel", { y: window.innerHeight-50,
                                                             width: (window.innerWidth-20) + "px", height:"200px",
                                                             autofillheight: "body",
                                                             visible:true, draggable:false, 
                                                             close:true, constraintoviewport:false} );
    
    this._panel.setHeader("Diagnosis Console");
    this._panel.setBody("");        
    this._panel.setFooter("End of Panel #2");
    this._panel.render("body");
    this._panel.body.style.overflow = 'auto';
  
    this.appendText = function(text) {
      self._panel.body.innerHTML += "<br>" + text; //.replace(/\n/g, "<br>").replace(/\s/g, "&nbsp;");
    };
  } else {
    this.appendText = function(text) {
      div.innerHTML += "<br>" + text; //.replace(/\n/g, "<br>").replace(/\s/g, "&nbsp;");
    };
  }
}
*/

//=============================================================================
// The YUIResourceLoader loads all yui scripts sequentially, otherwise they can be loaded to early
// and required objects may be missing
//=============================================================================
function JQMResourceLoader(resourceList, loadingFinishedCallback) {
  var self = this;
  
  this.inheritFrom = MLABResourceLoader
  this.inheritFrom(resourceList, loadingFinishedCallback);
  
  this.loadResources = function() {
    self.loadResource(self._pendingResources[0]);
  };
  
  this.superResourceLoaded = this.resourceLoaded; 
  this.resourceLoaded = function(resource) {
    self.superResourceLoaded(resource);
    if (self._pendingResources.length > 0) {
      self.loadResources();
    }
  };
}


//=============================================================================
// jQueryMobile JQM Application
//=============================================================================
function JQMApplication() {
  var self = this;
  
  this._diagnosisPanel = null;
  
  // TODO: this should either be a relative url to this page or be specified 
  // by the server and queried
  //this.jqmBaseUrl = "http://mevislab.mevis.lokal/resources/yui"
  //this.jqmBaseUrl = "http://192.168.0.104:88/Packages/MeVisLab/Private/Sources/Web/yui/2.6.0"
  //this.jqmBaseUrl = "http://127.0.0.1:88/Packages/MeVisLab/Private/Sources/Web/yui/2.6.0"
  //this.jqmBaseUrl = "http://192.168.77.1/static/js/yui"
  this.jqmBaseUrl = "/"
  this.loadFrameworkModules = function(loadingFinishedCallback) {
    var scriptModules = ["js/jquery-1.7.1.min.js",
                         "js/jquery.mobile-1.1.0-rc.1.min.js"];
    var cssModules = ["css/jquery.mobile-1.1.0-rc.1.min.css"];
    self._resourceManager.loadResources(scriptModules, cssModules, function() { self.loadOwnFrameworkModules(loadingFinishedCallback); }, JQMResourceLoader);
  };
  
  this.loadOwnFrameworkModules = function(loadingFinishedCallback) {
    var scriptModules = ["js/jQueryMobile/Controls.js"];
    var cssModules = [];
    self._resourceManager.loadResources(scriptModules, cssModules, function() { self.initializeJQMApplication(loadingFinishedCallback); });
  };
  
  this.initializeJQMApplication = function(loadingFinishedCallback) {
    loadingFinishedCallback();
  };
  
  self._pendingDiagnosisMessages = [];
  
  this.frameworkBodyReady = function() {
    

  };
  
  this.customApplicationFinishedInitialization = function() {
    if (self._showDiagnosisPanel) {
      /*self._diagnosisPanel = new YUIDiagnosisPanel();
      for (var i=0; i<self._pendingDiagnosisMessages.length; i++) {
        self._diagnosisPanel.appendText(self._pendingDiagnosisMessages[i]);
      }
      delete self._pendingDiagnosisMessages;
      */
    }
  };
  
  this.appendDiagnosisMessage = function(message) {
    if (self._showDiagnosisPanel) {
      /*if (self._diagnosisPanel) {
        self._diagnosisPanel.appendText(message);
      } else {
        self._pendingDiagnosisMessages.push(message);
        if (console) {
          console.log("Pending diagnosis message: " + message);
        }
      }*/
    } else if (console) {
      console.log(message);
    }
  };
  
  this.registerWidgetControls = function(moduleContext) {
    moduleContext.registerWidgetControl("Field", YUIFieldControl);
    moduleContext.registerWidgetControl("ItemModelView", MLABMLItemModelViewControl);
    moduleContext.registerWidgetControl("Label", MLABLabelControl);
    moduleContext.registerWidgetControl("Button", JQMButtonControl);
    moduleContext.registerWidgetControl("Horizontal", JQMHorizontalControl);
    moduleContext.registerWidgetControl("Vertical", JQMVerticalControl);
    moduleContext.registerWidgetControl("Slider", JQMSliderControl);
    moduleContext.registerWidgetControl("CheckBox", JQMCheckBoxControl);
    moduleContext.registerWidgetControl("ComboBox", JQMComboBoxControl);
    moduleContext.registerWidgetControl("RemoteRendering", JQMRemoteRenderingControl);
    moduleContext.registerWidgetControl("Window", JQMWindowControl);
  };
  
  this._createLoginDialog = function() {
    
    var hd = document.createElement("div");
    hd.setAttribute("class", "hd");
    hd.innerHTML = "Login";
    
    var p = document.createElement("p");
    p.innerHTML = "Enter your username and passwort:";
    
    var userLabel  = document.createElement("label");
    userLabel.setAttribute("for", "user");
    userLabel.innerHTML = "Username:";
    var passwordLabel = document.createElement("label");
    passwordLabel.setAttribute("for", "password");
    passwordLabel.innerHTML = "Password:";
    var userInput = document.createElement("input");
    userInput.setAttribute("type", "text");
    userInput.setAttribute("name", "user");
    var passwordInput = document.createElement("input");
    passwordInput.setAttribute("type", "password");
    passwordInput.setAttribute("name", "password");
    
    var table = document.createElement("table");
    var r0 = table.insertRow(0);
    r0.insertCell(0).appendChild(userLabel);
    r0.insertCell(1).appendChild(userInput);
    var r1 = table.insertRow(1);
    r1.insertCell(0).appendChild(passwordLabel);
    r1.insertCell(1).appendChild(passwordInput);
    
    var form = document.createElement("form");
    form.setAttribute("name", "loginDialogForm");
    form.appendChild(p);
    form.appendChild(table);
    
    var bd = document.createElement("div");
    bd.setAttribute("class", "bd");
    bd.appendChild(form);
    
    self._loginDialog = document.createElement("div");
    self._loginDialog.id = "loginDialog";
    self._loginDialog.appendChild(hd);
    self._loginDialog.appendChild(bd);
    document.body.appendChild(self._loginDialog);
/*
    var handleSubmit = function() {
      self._yuiLoginDialog.hide();
      self._authentication = [userInput.value, mlabEncodeBase64(passwordInput.value)];
      passwordInput.value = "";
      self._yuiLoginDialog.authenticatedCallback(); 
    };
    
    self._yuiLoginDialog = new YAHOO.widget.Dialog("loginDialog", { 
       width : "25em",
       fixedcenter : true,
       visible : false, 
       constraintoviewport : true,
       buttons : [ { text:"Login", handler:handleSubmit, isDefault:true },
                   { text:"Cancel", handler:function(){self._yuiLoginDialog.hide();} } ]
    });
    
    var enterKeyListener = new YAHOO.util.KeyListener(document, { keys:13 },
        { fn:handleSubmit, scope:self._yuiLoginDialog, correctScope:true }, 
        "keyup");
    self._yuiLoginDialog.cfg.queueProperty("keylisteners", enterKeyListener);
    
    self._yuiLoginDialog.render();
    */
  };
  
  this.requestAuthentication = function(authenticatedCallback) {    
    if (!self._loginDialog) {
      self._createLoginDialog();
    }
    self._yuiLoginDialog.authenticatedCallback = authenticatedCallback;
    self._yuiLoginDialog.show();
  };
  
  this.showLoadDialog = function() {
    if (!self.loadDialog) {
      /*try {
        // create the load dialog
        var loadDialogDiv = document.createElement("div");
        loadDialogDiv.id = "loadDialogDiv";
        document.body.appendChild(loadDialogDiv);
        self.loadDialog = new YAHOO.widget.Panel(loadDialogDiv.id,   
                                                 { width:"240px",  
                                                   fixedcenter:true,  
                                                   close:false,  
                                                   draggable:false,  
                                                   zindex:4, 
                                                   modal:true, 
                                                   visible:false 
                                                 });
        self.loadDialog.setHeader("Loading, please wait..."); 
        self.loadDialog.setBody('<img src="http://mevislab.mevis.lokal/resources/yui/rel_interstitial_loading.gif" />'); 
        self.loadDialog.render(document.body);
      } catch (e) {
        self.logException(e);
      }*/
    }
    //self.loadDialog.show();
  };
  
  this.hideLoadDialog = function() {
    /*if (self.loadDialog) {      
      self.loadDialog.hide();
    }*/
  };
}


//=============================================================================

app.inheritJQMApplication = JQMApplication;
app.inheritJQMApplication();
