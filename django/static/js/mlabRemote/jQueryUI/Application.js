//=============================================================================
// JQUIDiagnosisPanel
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
function JQUIResourceLoader(resourceList, loadingFinishedCallback) {
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
// jQueryMobile JQUI Application
//=============================================================================
function JQUIApplication() {
  var self = this;
  
  this._diagnosisPanel = null;
  this._hasLoginDialog = false;
  this.loadFrameworkModules = function(loadingFinishedCallback) {
    var scriptModules = ["jquery-ui-1.8.21.custom.min.js"];
    var cssModules = ["jqueryUI/smoothness/jquery-ui-1.8.21.custom.css"];
    self._resourceManager.loadResources(scriptModules, cssModules, function() { self.loadOwnFrameworkModules(loadingFinishedCallback); }, JQUIResourceLoader);
  };
  
  this.loadOwnFrameworkModules = function(loadingFinishedCallback) {
    var scriptModules = ["jQueryUI/Controls.js"];
    var cssModules = [];
    self._resourceManager.loadResources(scriptModules, cssModules, function() { self.initializeJQUIApplication(loadingFinishedCallback); });
  };
  
  this.initializeJQUIApplication = function(loadingFinishedCallback) {
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
    moduleContext.registerWidgetControl("Button", JQUIButtonControl);
    moduleContext.registerWidgetControl("Horizontal", JQUIHorizontalControl);
    moduleContext.registerWidgetControl("Vertical", JQUIVerticalControl);
    moduleContext.registerWidgetControl("Slider", JQUISliderControl);
    moduleContext.registerWidgetControl("CheckBox", JQUICheckBoxControl);
    moduleContext.registerWidgetControl("ComboBox", JQUIComboBoxControl);
    moduleContext.registerWidgetControl("RemoteRendering", JQUIRemoteRenderingControl);
    moduleContext.registerWidgetControl("Window", JQUIWindowControl);
  };
  
  this._createLoginDialog = function() {
    if (self._hasLoginDialog) {
      return;
    }
    html = '<a href="#_mevislab_login_dialog" id="_mevislab_login_dialog_button" style="display:none;" data-rel="dialog">Open dialog</a><div data-role="page" id="_mevislab_login_dialog" data-theme="a"><div id="_mevislab_login_dialog" title="Enter your username and passwort:"> \
            <p class="validateTips">All form fields are required.</p> \
            <form name="loginDialogForm">  \
            <fieldset>  \
              <label for="name">Username:</label>  \
              <input type="text" name="user" id="_mevislab_login_dialog_user" class="text ui-widget-content ui-corner-all" />  \
              <label for="password">Password:</label>  \
              <input type="password" name="password" id="_mevislab_login_dialog_password" value="" class="text ui-widget-content ui-corner-all" />  \
            </fieldset>  \
            <button type="submit" id="_mevislab_login_dialog_submit"> Login</button> \
            <button id="_mevislab_login_dialog_cancel"> Cancel</button> \
            </form>  \
          </div></div>';
    $("body").append($(html))
    self._hasLoginDialog = true;
    $("#_mevislab_login_dialog_submit").click(function () {
      self._authentication = [$("#_mevislab_login_dialog_user").val(), mlabEncodeBase64($("#_mevislab_login_dialog_password").val())];
      $("#_mevislab_login_dialog_password").val("");
      self.authenticatedCallback();
      $('.ui-dialog').dialog('close')
      return false;
    });
    $("#_mevislab_login_dialog_cancel").click(function () {
      $('.ui-dialog').dialog('close')
      return false;
    });
    /*
    $( "#_mevislab_login_dialog" ).dialog({
      autoOpen: false,
      height: 300,
      width: 350,
      modal: true,
      buttons: {
        Login: function() {
          
          self._authentication = [user.val(), mlabEncodeBase64(password.val())];
          password.val("");
          self.authenticatedCallback(); 
          $( this ).dialog( "close" );
        },
        Cancel: function() {
          $( this ).dialog( "close" );
        }
      },
      close: function() {
        //allFields.val( "" ).removeClass( "ui-state-error" );
      }
    });
    */
  };
  
  this.requestAuthentication = function(authenticatedCallback) {
    if (!self._hasLoginDialog) {
      self._createLoginDialog();
    }
    self.authenticatedCallback = authenticatedCallback;
    $( "#_mevislab_login_dialog_button" ).click();
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

app.inheritJQUIApplication = JQUIApplication;
app.inheritJQUIApplication();
