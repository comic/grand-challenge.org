MLAB.createNamespace("JQuery")

MLAB.JQuery.defineClass("Settings", {
  Settings: function() {
    this._jqueryBaseUrl = null
    this._jqueryUIBaseUrl = null
    this._jqueryScriptMode = ".min"
    this._jqueryVersion = "1.9.1"
    this._jqueryMobileVersion = "1.3.1"
    this._jqueryMobileUseStyleSheets = true
  },
  
  setupFromArguments: function(arguments, applicationSettings) {
    if ("jqueryBaseUrl" in arguments) {
      this._jqueryBaseUrl = arguments["jqueryBaseUrl"]
    } else {
      this._jqueryBaseUrl = applicationSettings.getURLToMLABRoot() + "MeVis/ThirdParty/Sources/web/jquery"
    }
    if ("jqueryMobileBaseUrl" in arguments) {
      this._jqueryMobileBaseUrl = arguments["jqueryMobileBaseUrl"]
    } else {
      this._jqueryMobileBaseUrl = applicationSettings.getURLToMLABRoot() + "MeVis/ThirdParty/Sources/web/jquerymobile"
    }
    if ("jqueryScriptDebugMode" in arguments) {
      this._jqueryScriptMode = ""
    }
    if ("jqueryVersion" in arguments) {
      this._jqueryVersion = "-" + arguments["_jqueryVersion"]
    }
    if ("jqueryMobileVersion" in arguments) {
      this._jqueryMobileVersion = "-" + arguments["jqueryMobileVersion"]
    }
    if ("jqueryMobileNoStyleSheets" in arguments) {
      this._jqueryMobileUseStyleSheets = false
    }
  },
  
  getJQueryBaseUrl: function() { return this._jqueryBaseUrl },
  getJQueryScriptMode: function() { return this._jqueryScriptMode },
  getJQueryVersion: function() { return this._jqueryVersion },
  getJQueryMobileBaseUrl: function() { return this._jqueryMobileBaseUrl },
  getJQueryMobileVersion: function() { return this._jqueryMobileVersion },
  useJQueryMobileStyleSheets: function() { return this._jqueryMobileUseStyleSheets }
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
    var jqueryMobileBaseUrl = this._settings.getJQueryMobileBaseUrl()
    var jqueryMobileVersion = this._settings.getJQueryMobileVersion()
    var mode = this._settings.getJQueryScriptMode()
    
    var scripts = [jqueryBaseUrl + "/jquery-" + jqueryVersion + mode + ".js",
                   jqueryMobileBaseUrl + "/js/jquery.mobile-" + jqueryMobileVersion + mode + ".js"]
    scripts = scripts.concat(["Widgets.js"])
    this.setJSUrls(scripts)
    
    var styles = []
    if (this._settings.useJQueryMobileStyleSheets()) {
      styles.push(jqueryMobileBaseUrl + "/css/jquery.mobile-" + jqueryMobileVersion + mode + ".css")
    }
    this.setCSSUrls(styles)
  },
  
  setup: function() {
    $(document).bind('pagecreate', function() {
        console.log("jQuery Mobile Plugin Ready")
        $(".MLAB-GUI-WidgetControl").trigger("create");
    })
    console.log("jquery mobiel Plugin reday")
    $(".MLAB-GUI-WidgetControl").trigger("create");
  },
})


//=============================================================================

;(function() {
  var plugin = new MLAB.JQuery.Plugin()
  MLAB.GUI.Application.loadPlugin(plugin)
})()

