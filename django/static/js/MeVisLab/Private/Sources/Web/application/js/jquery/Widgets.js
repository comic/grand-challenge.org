MLAB.JQuery.deriveClass("Window", MLAB.GUI.Widget, {
  Window: function() {
    this._initializedDialog = false
    MLAB.TS.Window.super.constructor.call(this)
  },
  
  appendToDOM: function(domParent) { 
    MLAB.TS.Window.super.appendToDOM.call(this, domParent)
    $(this._getDOMElement()).dialog({dialogClass: "no-close hidden-overflow",
                                     modal: true,
                                     autoOpen: false,
                                     resizable: true,
                                     closeOnEscape: false})
    this._initializedDialog = true
  },
  
  setVisible: function(visible) {
    if (this._initializedDialog){
      MLAB.TS.Window.super.setVisible.call(this, visible)
      if (visible){
        $(this.getDOMElement()).dialog("open")
      }
      else {
        $(this.getDOMElement()).dialog("close")
      }
    }
  },
  
  setWidth: function(width) {
    if (this._initializedDialog){
      $(this._getDOMElement()).dialog("option", "width", width)
    }
  },
  
  setHeight: function(height) {
    if (this._initializedDialog){
      $(this._getDOMElement()).dialog("option", "height", height)
    }
  },
  
})

