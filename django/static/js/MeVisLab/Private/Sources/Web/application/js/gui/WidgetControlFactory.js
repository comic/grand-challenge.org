//=============================================================================
// MLABWidgetControlFactory
//=============================================================================
MLAB.GUI.defineClass("WidgetControlFactorySingleton", {
  WidgetControlFactorySingleton: function() {
    this._controlClasses = new Object()
  },

  _getControlClass: function(controlName) {
    var c = this._controlClasses[controlName]
    if (c !== undefined) {
      return c
    }
    return null
  },

  createWindow: function(mdlTree, module) {
    if (mdlTree.getName() === "Window") {
      var c = this.createControl(mdlTree, module)
      if (c) {
        c.setup(/*parentControl=*/null)
        c.setupTypicalTags()
        return c
      } else {
        MLAB.Core.throwException("No MDL Window control implementation found")
      }
    } else {
      MLAB.Core.throwException('MDL tree is no window: "' + mdlTree.getName() + '"')
    }
  },
  
  createPanel: function(mdlTree, module) {
    if (mdlTree.getName() === "Panel") {
      var c = this.createControl(mdlTree, module)
      if (c) {
        c.setup(/*parentControl=*/null)
        c.setupTypicalTags()
        return c
      } else {
        MLAB.Core.throwException("No MDL Panel control registered")
      }
    } else {
      MLAB.Core.throwException('MDL tree is no panel: "' + mdlTree.getName() + '"')
    }
  },

  createControl: function(mdlTree, module) {
    var c = this._getControlClass(mdlTree.getName())
    if (c) {
      return new c(mdlTree, module)
    } else {
      if (module.isWidgetControl(mdlTree.getName())) {
        module.logError("No JavaScript implementation found for this widget control: " + mdlTree.getName())
      }
    }
    return null
  },

  registerWidgetControl: function(controlName, control, overwrite) {
    if ((this._getControlClass(controlName) === null) || (overwrite === true)) {
      if (typeof(control) !== "undefined") {
        this._controlClasses[controlName] = control
      } else {
        MLAB.Core.throwException("Attempt to register an undefined object as a widget control: " + controlName)
      }
    } else {
      MLAB.Core.throwException('Failed to register widget control "' + controlName + '": ' +
                               'another control with the same name was already registered')
    }
  },
})

MLAB.GUI.WidgetControlFactory = new MLAB.GUI.WidgetControlFactorySingleton()
