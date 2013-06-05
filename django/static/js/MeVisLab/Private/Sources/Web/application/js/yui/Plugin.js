MLAB.createNamespace("YUI")

MLAB.YUI.defineClass("ApplicationSettings", {
  ApplicationSettings: function() {
    this._yuiBaseUrl = null
    this._yuiScriptMode = "-min"
    this._showLoadDialog = false
  },
  
  setupFromArguments: function(arguments, applicationSettings) {
    if ("yuiBaseUrl" in arguments) {
      this._yuiBaseUrl = arguments["yuiBaseUrl"]
    } else {
      this._yuiBaseUrl = applicationSettings.getURLToMLABRoot() + "MeVis/ThirdParty/Sources/web/yui"
    }
    if ("yuiScriptMode" in arguments) {
      this._yuiScriptMode = "-" + arguments["yuiScriptMode"]
    }
    if ("yuiShowLoadDialog" in arguments) {
      this._showLoadDialog = true
    }
  },
  
  getYUIBaseUrl: function() { return this._yuiBaseUrl },
  getYUIScriptMode: function() { return this._yuiScriptMode },
  showLoadDialog: function() { return this._showLoadDialog },
})

//=============================================================================
// YUIApplication
//=============================================================================
MLAB.YUI.deriveClass("Plugin", MLAB.GUI.PluginBase, {
  Plugin: function() {
    MLAB.YUI.Plugin.super.constructor.call(this)
  },

  initialize: function(applicationArguments) {
    this._yuiSettings = new MLAB.YUI.ApplicationSettings()
    this._yuiSettings.setupFromArguments(applicationArguments, MLAB.GUI.Application.getSettings())
    this._authenticationManager = null
    
    var yuiBaseUrl = this._yuiSettings.getYUIBaseUrl()
    var mode = this._yuiSettings.getYUIScriptMode()
    
    var scripts = []
    if (mode === "-debug") {
      scripts = [yuiBaseUrl + "/build/yahoo/yahoo-debug.js",
                 yuiBaseUrl + "/build/event/event" + mode + ".js",
                 yuiBaseUrl + "/build/logger/logger" + mode + ".js"]
    }
    scripts = scripts.concat([yuiBaseUrl + "/build/yahoo-dom-event/yahoo-dom-event.js",
                               yuiBaseUrl + "/build/datasource/datasource-min.js",
                               yuiBaseUrl + "/build/dragdrop/dragdrop" + mode + ".js",
                               yuiBaseUrl + "/build/slider/slider" + mode + ".js",
                               yuiBaseUrl + "/build/container/container" + mode + ".js",
                               yuiBaseUrl + "/build/connection/connection" + mode + ".js",
                               yuiBaseUrl + "/build/animation/animation" + mode + ".js",
                               yuiBaseUrl + "/build/autocomplete/autocomplete" + mode + ".js",
                               yuiBaseUrl + "/build/element/element" + mode + ".js",
                               yuiBaseUrl + "/build/datatable/datatable" + mode + ".js",
                               yuiBaseUrl + "/build/treeview/treeview" + mode + ".js",
                               yuiBaseUrl + "/build/resize/resize" + mode + ".js"])
    scripts = scripts.concat(["Widgets.js", "AuthenticationManager.js"])
    this.setJSUrls(scripts)
    
    var styles = [yuiBaseUrl + "/build/fonts/fonts-min.css",
                  yuiBaseUrl + "/build/grids/grids-min.css",
                  yuiBaseUrl + "/build/resize/assets/skins/sam/resize.css",
                  yuiBaseUrl + "/build/datatable/assets/skins/sam/datatable.css",
                  yuiBaseUrl + "/build/button/assets/skins/sam/button.css",
                  yuiBaseUrl + "/build/slider/assets/skins/sam/slider.css",
                  yuiBaseUrl + "/build/container/assets/skins/sam/container.css",
                  yuiBaseUrl + "/build/treeview/assets/skins/sam/treeview.css",
                  yuiBaseUrl + "/build/autocomplete/assets/skins/sam/autocomplete.css"]
    this.setCSSUrls(styles)
  },
  
  setup: function() {
    MLAB.GUI.addStyleSheetClass(document.body, "yui-skin-sam")
    // reset 'text-align: center' from grids.css
    document.body.style.textAlign = "left"
    MLAB.GUI.Application.setAuthenticationManager(new MLAB.YUI.AuthenticationManager(this))
    MLAB.YUI.Widget.setYUIBaseUrl(this._yuiSettings.getYUIBaseUrl())
    if (this._yuiSettings.showLoadDialog()) {
      this.showLoadDialog()
    }
  },
  
  showLoadDialog: function() {
    if (!this.loadDialog) {
      try {
        // create the load dialog
        var loadDialogDiv = document.createElement("div")
        loadDialogDiv.id = "loadDialogDiv"
        document.body.appendChild(loadDialogDiv)
        this.loadDialog = new YAHOO.widget.Panel(loadDialogDiv.id,   
                                                 { width:"240px",  
                                                   fixedcenter:true,  
                                                   close:false,  
                                                   draggable:false,  
                                                   zindex:4, 
                                                   modal:true, 
                                                   visible:false 
                                                 })
        this.loadDialog.setHeader("Loading, please wait...")
        this.loadDialog.setBody('<img src="'+ MLAB.GUI.Application.getSettings().getURLToMLABRoot()+'MeVisLab/Private/Sources/Web/application/css/loading.gif" />')
        this.loadDialog.render(document.body)
      } catch (e) {
        this.logException(e)
      }
    }
    this.loadDialog.show()
  },
  
  hideLoadDialog: function() {
    if (this.loadDialog) {      
      this.loadDialog.hide()
    }
  },
})


//=============================================================================

;(function() {
  var plugin = new MLAB.YUI.Plugin()
  MLAB.GUI.Application.loadPlugin(plugin)
  MLAB.GUI.Application.connect("showLoadDialog", plugin, "showLoadDialog")
  MLAB.GUI.Application.connect("hideLoadDialog", plugin, "hideLoadDialog")
})()

