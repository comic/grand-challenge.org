/** \class MLAB.Core.WindowController
 * 
 * \param module The MLAB.Core.Module instance.
 */
MLAB.GUI.deriveClass("WindowController", MLAB.Core.Object, {
  WindowController: function() {
    MLAB.GUI.WindowController.super.constructor.call(this)
    this.registerSignal("windowCreated")
    this._module = null
    this._namedControls = {}
    this._windowControls = []
  },
  
  setModule: function(module) {
    this._module = module
  },
  
  getModule: function() {
    return this._module
  },
  
  createControl: function(mdlTree) {
    var control = MLAB.GUI.WidgetControlFactory.createControl(mdlTree, this._module)
    if (control) {
      var name = control.getName()
      if (name !== null) {
        this._addNamedControl(control, name)
      }
    }
    return control
  },
  
  _addNamedControl: function(control, name) {
    if (name in this._namedControls) {
      MLAB.Core.throwException("A control with the same name is already registered: " + name)
    }
    this._namedControls[name] = control
  },
  
  getRemoteRenderingControl: function(module, domElement) {
    var inputFields = module.getInputFields()
    for (var fieldName in inputFields) {
      var field = inputFields[fieldName]
      if (field.isBaseField() && field.getBaseType() === "RemoteRendering") {
        var control = field.getHandler().getControl()
        if (control.getViewport() === domElement) { return control }
      }
    }
    return null
  },
  
  getWindow: function(windowName) {
    var name = this._getWindowName(windowName)
    for (var i=0; i<this._windowControls.length; i++) {
      var w = this._windowControls[i]
      if (w.getWindowName() === name) {
        return w
      }
    }
    if (name === "_default") {
      if (this._windowControls.length > 0) {
        return this._windowControls[0]
      }
    }
    return null
  },
  
  /** \fn MLAB.Core.WindowController.control
   * 
   * Returns the first widget control with the given name. null is returned if none is found. 
   * 
   * \param controlName The control name.
   * \return An MLAB.Core.WidgetControl instance or null if none was found.
   */
  control: function(controlName) { 
    if (controlName in this._namedControls) {
      return this._namedControls[controlName]
    }
    return null
  },
  
  _getWindowName: function(windowName) {
    if (typeof(windowName) === "undefined" || windowName === null || windowName.length === 0) {
      return "_default"
    }
    return windowName
  },
  
  hideWindow: function(windowName) {
    var windowControl = this.getWindow(windowName)
    if (windowControl) {
      windowControl.hide()
    }
  },
  
  hidePanel: function(windowName) {
    this.hideWindow(windowName)
  },
  
  showWindow: function(windowName, windowContainer) {
    var name = this._getWindowName(windowName)
    var windowControl = this.getWindow(name)
    if (!windowControl) {
      windowControl = this.createWindow(name, windowContainer)
    }
    if (windowControl) {
      windowControl.show()
    }
    return windowControl
  },
  
  showDialog: function(windowName, windowContainer) {
    var windowControl = this.createDialog(windowName, windowContainer)
    windowControl.show()
    return windowControl
  },
  
  createDialog: function(windowName, windowContainer) {
    var windowControl = this._createWindowInternal(windowName, windowContainer)
    if (windowControl) {
      var domElement = windowControl.getWidget()._getDOMElement()
      var cssClass = domElement.getAttribute("class")
      cssClass += " MLABDialog"
      domElement.setAttribute("class", cssClass)
      domElement.style.left = window.innerWidth / 2 - domElement.offsetWidth / 2
      if (domElement.style.left < 0) { domElement.style.left = 0 }
      domElement.style.top = window.innerHeight / 2 - domElement.offsetHeight / 2
      if (domElement.style.top < 0) { domElement.style.top = 0 }
      //console.log(domElement.offsetHeight)
      windowControl.hide()
      domElement.style.visibility = "visible"
      //console.log(domElement.offsetHeight)
      this.emit("windowCreated", windowControl)
    } else {
      this._module.logError("Failed to create dialog " + windowName)
    }
    return windowControl
  },
  
  showPanel: function(windowName, windowContainer) {
    var name = this._getWindowName(windowName)
    var panelControl = this.getWindow(name)
    if (!panelControl) {
      panelControl = this.createPanel(name, windowContainer)
    }
    if (panelControl) {
      panelControl.show()
    }
    return panelControl
  },
  
  /** \fn MLAB.Core.WindowController.createPanel
   * 
   * Creates a panel from an MDL window. A panel is handled like a window by the window controller,
   * except that its widget is a panel instead of a window. This means cannot create a window
   * and a panel with same name as you cannot create two windows with the same name. You can access
   * the panel using getWindow() also.
   */
  createPanel: function(windowName, windowContainer) {
    var panelControl = null
    var windowTree = this._getWindowTree(windowName)
    if (windowTree !== null) {
      // convert the window control into a panel control in the MDL description
      var json = {name: "Panel", value: ""}
      var panelTree = new MLAB.Core.Tree(json)
      for (var i=0; i<windowTree.count(); i++) {
        var child = windowTree.child(i)
        panelTree.append(child)
      }
      panelControl = this._createPanelInternal(panelTree, windowContainer)
      if (panelControl) {
        if (windowName) {
          panelControl.setWindowName(windowName)
        }
        this.emit("windowCreated", panelControl)
      } else {
        this._module.logError("Failed to create panel from window: " + windowName)
      }
    } else {
      this._module.logError("Failed to create panel: no such window found in the MDL definition: " + windowName)
    }
    return panelControl
  },
  
  _createPanelInternal: function(panelTree, windowContainer) {
    var panelControl = null
    if (panelTree) {
      var c = MLAB.GUI.WidgetControlFactory.createPanel(panelTree, this._module)
      if (c) {
        if (windowContainer) {
          this._windowOrPanelControlCreated(c, windowContainer)
        } else {
          this._module.logError("Failed to append panel to DOM, because no window container is given: " + windowName)
        }
      }
      panelControl = c
    }
    return panelControl
  },
  
  _getWindowTree: function(windowName) {
    var searchName = this._getWindowName(windowName)
    var firstWindowTree = null
    var windowTree = null
    var mdlTree = this._module.getMDLTree()
    for (var i=0; i<mdlTree.count(); i++) {
      var child = mdlTree.child(i)
      if (child.getName() === "Window") {
        if (!firstWindowTree) { firstWindowTree = child }
        var tmpName = this._getWindowName(child.getValue())
        if (tmpName === windowName) {
          windowTree = child
          break
        }
      }
    }
    if (!windowTree && searchName === "_default") {
      windowTree = firstWindowTree
    }
    return windowTree
  },
    
  createWindow: function(windowName, windowContainer) {
    var windowControl = this._createWindowInternal(windowName, windowContainer)
    if (windowControl) {
      this.emit("windowCreated", windowControl)
    } else {
      this._module.logError("Failed to create window " + windowName)
    }
    return windowControl
  },
    
  _createWindowInternal: function(windowName, windowContainer) {
    var windowTree = this._getWindowTree(windowName)
    var windowControl = null
    if (windowTree) {
      var c = MLAB.GUI.WidgetControlFactory.createWindow(windowTree, this._module)
      if (c) {
        // if no window container is given, then add the window to the body.
        // this is valid, because windows are floating and thus their parent may be any element
        this._windowOrPanelControlCreated(c, windowContainer ? windowContainer : document.body)
      }
      windowControl = c
    } else {
      this._module.logError("No such MDL window found: " + windowName)
    }
    return windowControl
  },
  
  _windowOrPanelControlCreated: function(control, windowContainer) {
    this._windowControls.push(control)
    var name = control.getName()
    if (name !== null) {
      this._addNamedControl(control, name)
    }
    control.appendToDOM(windowContainer)
  },
  
  destroy: function() {
    for (var i=0; i<this._windowControls.length; i++) {
      var w = this._windowControls[i]
      var domElement = w.getWidget()._getDOMElement()
      domElement.parentElement.removeChild(domElement)
      w.destroy()
    }
    this._windowControls = null
  },
})
