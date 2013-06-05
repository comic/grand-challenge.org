MLAB.createNamespace("GUI")

;(function() {
    
  /** \fn MLAB.GUI.getNextID
   * Increments the last id by 1 and returns it. The first id will be 1.
   */
  this.getNextID = (function() {
    var lastDOMElementID = 0
    function getNextID() { return ++lastDOMElementID }
    return getNextID
  })()
  
  /* Helper function for MLAB.GUI.setDOMElementEnabled(). It
   * recursively enables/disables DOM elements. Elements that belong
   * to another MLAB.GUI.Widget are ignored.
   */
  function propagateSetDOMElementEnabled(domElement, enabled) {
    for (var i=0; i<domElement.children.length; i++) {
      var w = domElement.children[i]
      // stop at DOM elements that belong to a widget, because the widgets
      // handle those theirselves
      if (typeof(w.widget) === "undefined") {
        MLAB.GUI.setDOMElementEnabled(w, enabled)
      }
    }
  }
  
  /** \fn MLAB.GUI.setDOMElementEnabled
   * 
   * Enables/disables the given DOM element. Enables/disables also its children,
   * which do not belong to any widget, recursively.
   * 
   * \param domElement The DOM element.
   * \param enabled A boolean that indicates if the element is enabled or disabled.
   */
  this.setDOMElementEnabled = function(domElement, enabled) {
    if (domElement.tagName === "BUTTON" || domElement.tagName === "INPUT" || domElement.tagName === "SELECT") {
      if (enabled) {
        domElement.removeAttribute("disabled")
      } else {
        domElement.setAttribute("disabled", "disabled")
      }
    }
    if (enabled) {
      MLAB.GUI.removeStyleSheetClass(domElement, "MLAB-GUI-DisabledDOMElement")
    } else {
      MLAB.GUI.addStyleSheetClass(domElement, "MLAB-GUI-DisabledDOMElement")
    }
    propagateSetDOMElementEnabled(domElement, enabled)
  }
  
  /* Helper function for MLAB.GUI.setDOMElementVisible(). It
   * recursively shows/hidesDOM elements. Elements that belong
   * to another MLAB.GUI.Widget are ignored.
   */
  function propagateSetDOMElementVisible(domElement, visible) {
    for (var i=0; i<domElement.children.length; i++) {
      var w = domElement.children[i]
      if (typeof(w.widget) === "undefined") {
        MLAB.GUI.setDOMElementVisible(w, visible)
      }
    }
  }
  
  /** \fn MLAB.GUI.setDOMElementVisible
   * 
   * Shows/hides the given DOM element. Shows/hides also its children,
   * which do not belong to any widget, recursively.
   * The CSS class MLAB-GUI-ConcealedDOMElement is added to hidden elements,
   * which by default sets the style display to 'none'. This corresponds to hiding
   * widgets in MeVisLab, because the DOM elements do not occupy any space then.
   * Using style visibility with the value 'hidden', would cause DOM element to be 
   * invisible, but it still occupies space.
   * 
   * \param domElement The DOM element.
   * \param visible A boolean that indicates if the element is shown or hidden.
   */
  this.setDOMElementVisible = function(domElement, visible) {
    // first show/hide the children to avoid flickering
    propagateSetDOMElementVisible(domElement, visible)
    if (visible) {
      MLAB.GUI.removeStyleSheetClass(domElement, "MLAB-GUI-ConcealedDOMElement")
    } else {
      MLAB.GUI.addStyleSheetClass(domElement, "MLAB-GUI-ConcealedDOMElement")
    }
  }
  
  
  /** \fn MLAB.GUI.isDOMElementEnabled
   * 
   * Returns if the DOM element is enabled. See also MLAB.GUI.setDOMElementEnabled()
   * 
   * \return Returns a boolean indicating whether the DOM element is enabled.
   */
  this.isDOMElementEnabled = function(domElement) {
    var isEnabled = true
    if (domElement.tagName === "BUTTON" || domElement.tagName === "INPUT" || domElement.tagName === "SELECT") {
      if (domElement.getAttribute("disabled")) {
        isEnabled = false
      }
    }
    if (isEnabled) {
      var clss = domElement.getAttribute("class")
      if (clss && clss.split(" ").indexOf("MLAB-GUI-DisabledDOMElement") >= 0) {
        isEnabled = false
      }
    }
    return isEnabled
  },
  
  
  /** \fn MLAB.GUI.addStyleSheetClass
   * 
   * Appends the given style sheet class to the DOM element. It does not
   * check if the class was already added.
   * 
   * \param domElement The DOM element.
   * \param styleSheetClass The CSS class name.
   */
  this.addStyleSheetClass = function(domElement, styleSheetClass) {
    var clss = domElement.getAttribute("class")
    if (!clss) {
      clss = styleSheetClass
    } else {
      clss = clss.split(" ")
      if (clss.indexOf(styleSheetClass) >= 0) {
        clss.remove(styleSheetClass)
      }
      clss.push(styleSheetClass)
      clss = clss.join(" ") 
    }
    domElement.setAttribute("class", clss)
  }


  /** \fn MLAB.GUI.removeStyleSheetClass
   * 
   * Removes the given style sheet class from the DOM element. No error
   * is produces when the given style sheet class is not set on the DOM element.
   * 
   * \param domElement The DOM element.
   * \param styleSheetClass The CSS class name.
   */
  this.removeStyleSheetClass = function(domElement, styleSheetClass) {
    var clss = domElement.getAttribute("class")
    if (clss) {
      var classes = clss.split(" ")
      clss = ""
      for (var i=0; i<classes.length; i++) {
        if (classes[i] !== styleSheetClass) {
          if (clss.length > 0) {
            clss += " "
          }
          clss += classes[i]
        }
      }
      if (clss.length > 0) {
        domElement.setAttribute("class", clss)
      } else {
        domElement.removeAttribute("class")
      }
    }
  }
  
  /** \fn MLAB.GUI.getGlobalPosition
   * 
   * Returns the global position of the given domElement
   * 
   * \param domElement The DOM element.
   */
   this.getGlobalPosition = function(domElement) {
    var totalOffsetX = 0
    var totalOffsetY = 0
    var currentElement = domElement
    do {
      totalOffsetX += currentElement.offsetLeft
      totalOffsetY += currentElement.offsetTop
    } 
    while (currentElement = currentElement.offsetParent)

    return { x:totalOffsetX, y:totalOffsetY }
  }

  /** Namespace constants */
  //@{
  this.HORIZONTAL = 0
  this.VERTICAL = 1
  //@}

}).apply(MLAB.GUI)

