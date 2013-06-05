MLAB.createNamespace("JQuery")

MLAB.JQuery.defineClass("Settings", {
  Settings: function() {
    this._jqueryBaseUrl = null
    this._jqueryUIBaseUrl = null
    this._jqueryScriptMode = ".min"
    this._jqueryVersion = "1.9.1"
    this._jqueryUIVersion = "1.10.1"
    this._jqueryUIUseStyleSheets = true
  },
  
  setupFromArguments: function(arguments, applicationSettings) {
    if ("jqueryBaseUrl" in arguments) {
      this._jqueryBaseUrl = arguments["jqueryBaseUrl"]
    } else {
      this._jqueryBaseUrl = applicationSettings.getURLToMLABRoot() + "MeVis/ThirdParty/Sources/web/jquery"
    }
    if ("jqueryUIBaseUrl" in arguments) {
      this._jqueryUIBaseUrl = arguments["jqueryUIBaseUrl"]
    } else {
      this._jqueryUIBaseUrl = applicationSettings.getURLToMLABRoot() + "MeVis/ThirdParty/Sources/web/jqueryui"
    }
    if ("jqueryScriptDebugMode" in arguments) {
      this._jqueryScriptMode = ""
    }
    if ("jqueryVersion" in arguments) {
      this._jqueryVersion = "-" + arguments["_jqueryVersion"]
    }
    if ("jqueryUIVersion" in arguments) {
      this._jqueryUIVersion = "-" + arguments["jqueryUIVersion"]
    }
    if ("jqueryUINoStyleSheets" in arguments) {
      this._jqueryUIUseStyleSheets = false
    }
  },
  
  getJQueryBaseUrl: function() { return this._jqueryBaseUrl },
  getJQueryScriptMode: function() { return this._jqueryScriptMode },
  getJQueryVersion: function() { return this._jqueryVersion },
  getJQueryUIBaseUrl: function() { return this._jqueryUIBaseUrl },
  getJQueryUIVersion: function() { return this._jqueryUIVersion },
  useJQueryUIStyleSheets: function() { return this._jqueryUIUseStyleSheets }
})

/** \class MLAB.JQuery.Plugin
 * 
 */
MLAB.JQuery.deriveClass("Plugin", MLAB.GUI.PluginBase, {
  Plugin: function() {
    MLAB.JQuery.Plugin.super.constructor.call(this)
  },

  initialize: function(applicationArguments) {
    this._settings = new MLAB.JQuery.Settings()
    this._settings.setupFromArguments(applicationArguments, MLAB.GUI.Application.getSettings())
    
    var jqueryBaseUrl = this._settings.getJQueryBaseUrl()
    var jqueryVersion = this._settings.getJQueryVersion()
    var jqueryUIBaseUrl = this._settings.getJQueryUIBaseUrl()
    var jqueryUIVersion = this._settings.getJQueryUIVersion()
    var mode = this._settings.getJQueryScriptMode()
    
    var scripts = [jqueryBaseUrl + "/jquery-" + jqueryVersion + mode + ".js",
                   jqueryUIBaseUrl + "/js/jquery-ui-" + jqueryUIVersion + ".custom" + mode + ".js"]
    scripts = scripts.concat(["Widgets.js"])
    this.setJSUrls(scripts)
    
    var styles = []
    if (this._settings.useJQueryUIStyleSheets()) {
      styles.push(jqueryUIBaseUrl + "/css/smoothness/jquery-ui-" + jqueryUIVersion + ".custom" + mode + ".css")
    }
    this.setCSSUrls(styles)
  },
  
  setup: function() {
  },
})


//=============================================================================

;(function() {
  var plugin = new MLAB.JQuery.Plugin()
  MLAB.GUI.Application.loadPlugin(plugin)
})()

