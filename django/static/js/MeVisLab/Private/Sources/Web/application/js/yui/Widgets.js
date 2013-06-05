MLAB.YUI.deriveClass("Widget", MLAB.GUI.Widget, {

  Widget: function() {
    this._yuiModule = null
    MLAB.YUI.Widget.super.constructor.call(this)    
  },

  _setYUIModule: function(yuiModule) {
    this._yuiModule = yuiModule
    this._setDOMElement(yuiModule.element)
    this._yuiModule.subscribe("hide", this.callback("_handleHideEvent"))
    this._yuiModule.subscribe("show", this.callback("_handleShowEvent"))
  },

  _handleShowEvent: function(event) {
    if (!this.isVisible()) { 
      this._control.show()
    }
  },
  
  _handleHideEvent: function(event) {
    // TODO: a remote rendering control inside a window does not send rendering stop
    if (this.isVisible()) { 
      this._control.hide()
    }
  },
  
  appendToDOM: function(domParent) {
    this._yuiModule.render(domParent)
  },
  
  //appendChild: function(child) {
  //  this._yuiModule.body.appendChild(child) 
  //},

  setVisible: function(visible) {
    if (this.isVisible() !== visible) {
      MLAB.YUI.Widget.super.setVisible.call(this, visible)
      if (visible) {
        this._yuiModule.show()
      } else {
        this._yuiModule.hide()
      }
    }
  },
  
  _addWidgetToDOM: function(widget) {
    this._yuiModule.body.appendChild(widget._getDOMElement())
  },
  
  _removeWidgetFromDOM: function(widget) {
    this._yuiModule.body.removeChild(widget._getDOMElement())
  },
}, {
  // static members

  _yuiBaseUrl: "",
  
  setYUIBaseUrl: function(url) {
    MLAB.YUI.Widget._yuiBaseUrl = url
  },
    
  getYUIBaseUrl: function(url) {
    return MLAB.YUI.Widget._yuiBaseUrl
  }
})

MLAB.YUI.deriveClass("Window", MLAB.YUI.Widget, {
  Window: function() {
    this._panel = null
    MLAB.YUI.Window.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    this._panel = new YAHOO.widget.Panel(div, { visible:true, draggable:true, close:true, resizeable:true, zIndex: 10} )
    this._panel.setBody(document.createElement("div"))
    this._setYUIModule(this._panel)
    
    this._resize = new YAHOO.util.Resize(div, {
      handles: ["br"],
      autoRatio: false,
      minWidth: 100,
      minHeight: 100,
      status: false,
      proxy: true,
    })
    
    var resizeElement = this._resize._handles["br"]
    resizeElement.style.right = "0px"
    resizeElement.style.bottom = "0px"
    resizeElement.style.height = "8px"
    resizeElement.style.width = "8px"
    resizeElement.style.position = "absolute"
    
    this._resize.on("startResize", function(args) {
      if (this.cfg.getProperty("constraintoviewport")) {
        var D = YAHOO.util.Dom
        var clientRegion = D.getClientRegion()
        var elRegion = D.getRegion(this.element); 
        resize.set("maxWidth", clientRegion.right - elRegion.left - YAHOO.widget.Overlay.VIEWPORT_OFFSET)
        resize.set("maxHeight", clientRegion.bottom - elRegion.top - YAHOO.widget.Overlay.VIEWPORT_OFFSET)
      } else {
        resize.set("maxWidth", null)
        resize.set("maxHeight", null)
      }
    }, this._panel, true)
  
    this._resize.on("resize", function(args) {
      var panelHeight = args.height
      this.cfg.setProperty("height", panelHeight + "px")
    }, this._panel, true)
  },
  
  setId: function(id) {
    this._panel.id = id
  },
  
  appendToDOM: function(domParent) {
    // set the height of the parent element to 0, because windows are floating. The
    // the parent is only used to add them to the DOM and should not occupy any space.
    //domParent.style.width = "1px"
    //domParent.style.height = "0px"
    MLAB.YUI.Window.super.appendToDOM.call(this, domParent)
  }
})


MLAB.YUI.deriveClass("Dialog", MLAB.YUI.Widget, {
  Dialog: function() {
    this._panel = null
    MLAB.YUI.Dialog.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    var div = document.createElement("div")
    this._panel = new YAHOO.widget.Panel(div, { visible:true, draggable:true, close:true, resizeable:true, zIndex:10} )
    this._setYUIModule(this._panel)
  },
  
  setId: function(id) {
    this._panel.id = id
  },
  
  appendToDOM: function(domParent) {
    // set the height of the parent element to 0, because windows are floating. The
    // the parent is only used to add them to the DOM and should not occupy any space.
    //domParent.style.width = "1px"
    //domParent.style.height = "0px"
    MLAB.YUI.Dialog.super.appendToDOM.call(this, domParent)
  }
})


/** \class MLAB.YUI.Slider
 * 
 */
MLAB.YUI.deriveClass("Slider", MLAB.GUI.Slider, {
  Slider: function(interval) {
    MLAB.YUI.Slider.super.constructor.call(this)
    this._scaleFactor = 1
    this._isFloatValue = false
    this._signalsWereBlocked = false
    this._isSliding = false
  },

  _createDOMElement: function() {
    var thumbImage = document.createElement("img")
    thumbImage.src = MLAB.YUI.Widget.getYUIBaseUrl() + "/build/slider/assets/thumb-n.gif"
    
    var thumbDiv = document.createElement("div")
    thumbDiv.setAttribute("class", "yui-slider-thumb")
    thumbDiv.style.left = "0px"
    thumbDiv.appendChild(thumbImage)
    
    var bgDiv = document.createElement("div")
    bgDiv.setAttribute("class", "yui-h-slider")
    bgDiv.style.display = "inline-block"
    bgDiv.style.verticalAlign = "bottom"
    bgDiv.style.backgroundImage = "url('" + MLAB.YUI.Widget.getYUIBaseUrl() + "/build/slider/assets/bg-fader.gif')"
    bgDiv.appendChild(thumbDiv)
    
    var min = 0
    var max = 200
    var interval = 1
    this._slider = YAHOO.widget.Slider.getHorizSlider(bgDiv, thumbDiv, min, max, interval)
    this._slider.animate = true
            
    this._updateRange()

    this._slider.subscribe("change", this.callback("_onSliderChange"))
    this._slider.subscribe("slideEnd", this.callback("_onSlideEnd"))
    this._slider.subscribe("slideStart", this.callback("_onSlideStart"))

    this._setDOMElement(bgDiv)
  },
  
  _setDOMElementEnabled: function(enabled) {
    MLAB.YUI.Slider.super._setDOMElementEnabled.call(this, enabled)
    if (enabled) {
      this._slider.unlock()
    } else {
      this._slider.lock()
    }
  },
  
  _updateRange: function() {
    var range = this._maximumValue - this._minimumValue
    this._scaleFactor = (range > 0 ? (range/200) : 1)
  },
  
  setRange: function(min, max) {
    MLAB.YUI.Slider.super.setRange.call(this, min, max)
    this._updateRange()
  },
  
  setIsFloatValue: function(value) {
    this._isFloatValue = value
  },
  
  _mapValueToYUISlider: function(value) {
    return Math.round((value - this._minimumValue)/this._scaleFactor)
  },
  
  _mapValueFromYUISlider: function(value) {
    var v = this._minimumValue + value * this._scaleFactor
    if (!this._isFloatValue) {
      v = Math.round(v)
    }
    return v
  },
  
  _updateSliderFromValue: function() {
    var v = this._mapValueToYUISlider(this._value)
    this._slider.setValue(v)
  },
  
  _updateValueInternal: function(value) {
    if (this._signalsWereBlocked) {
      var signalsBlocked = this.signalsBlocked()
      this.blockSignals(true)
    }
    MLAB.YUI.Slider.super._updateValue.call(this, value)
    if (this._signalsWereBlocked) {
      this.blockSignals(signalsBlocked)
    }
  },
  
  _updateValue: function(value) {
    if (!this._isSliding) {
      // we ignore setValue/updateValue when we not sliding, because
      // this is triggered externally and would cause the thumb to jump around.
      this._updateValueInternal(value)
      this._updateSliderFromValue()
    }
  },

  _getSliderValue: function() {
    return this._mapValueFromYUISlider(this._slider.getValue())
  },
  
  _onSliderChange: function(offsetFromStart) {
    if (this._emitValueChangedWhileEditing) {
      var v = this._getSliderValue()
      this._updateValueInternal(v)
    }
  },
  
  _onSlideStart: function() {
    this._isSliding = true
    if (this.signalsBlocked()) {
      this._signalsWereBlocked = true
    }
  },

  _onSlideEnd: function() {
    var v = this._getSliderValue()
    this._updateValueInternal(v)
    this._signalsWereBlocked = false
    this._isSliding = false
  },
})

MLAB.YUI.deriveClass("Splitter", MLAB.GUI.Splitter, {
  Splitter: function() {
    MLAB.YUI.Splitter.super.constructor.call(this)
    this.addStyleSheetClass("yui-g")
    this._firstDiv = null
    this._secondDiv = null
  },
  
  setDirection: function(direction) {
    MLAB.YUI.Splitter.super.setDirection.call(this, direction)
    if (this._direction == MLAB.GUI.Splitter.VERTICAL) {
      this.removeStyleSheetClass("HorizontalSplitter")
      this.addStyleSheetClass("VerticalSplitter")
    } else {
      this.removeStyleSheetClass("VerticalSplitter")
      this.addStyleSheetClass("HorizontalSplitter")
    }
  },
  
  _addWidgetToDOM: function(widget) {
    var cssClass = "HorizontalSplitterChild"
    if (this._direction === MLAB.GUI.Splitter.VERTICAL) {
      cssClass = "VerticalSplitterChild"
    }
    var div = null
    if (this._firstDiv === null) {
      div = this._firstDiv = document.createElement("div")
      MLAB.GUI.addStyleSheetClass(this._firstDiv, "first")
    } else if (this._secondDiv === null) {
      div = this._secondDiv = document.createElement("div")
    } else {
      MLAB['Core'].throwException("MLAB.YUI.Splitter can only handle two widgets")
    }
    
    MLAB.GUI.addStyleSheetClass(div, "yui-u")
    MLAB.GUI.addStyleSheetClass(div, cssClass)
    
    this._domElement.appendChild(div)
    widget.appendToDOM(div)
  },
  
  _handleWidgetAdded: function(widget) {
    MLAB.YUI.Splitter.super._handleWidgetAdded.call(this, widget)
    // the first widget is not added before the second is added
    if (this._children.length < 2) {
      return
    } else if (this._children.length > 2) {
      MLAB['Core'].throwException("MLAB.YUI.Splitter can only handle two widgets")
    }
    if (this._direction === MLAB.GUI.Splitter.VERTICAL) {
      this._createYUIVerticalResize()
    } else {
      this._createYUIHorizontalResize()
    }
  },
  
  _createYUIVerticalResize: function() {
    var height = this._getDOMElement().offsetHeight

    var resize = new YAHOO.util.Resize(this._firstDiv, {
      handles: ['b'],
      minHeight: 25, 
      maxHeight: height-25
    })
    resize.on('resize', function(ev) {
      var h = ev.height
      YAHOO.util.Dom.setStyle(this._firstDiv, 'height', (h - 6) + 'px')
      YAHOO.util.Dom.setStyle(this._secondDiv, 'top', (h - 6) + 'px')
      YAHOO.util.Dom.setStyle(this._secondDiv, 'height', (height - h - 6) + 'px')
    })
  },
  
  _createYUIHorizontalResize: function() {
    var size = parseInt(this._getDOMElement().offsetWidth, 10);

    var max = (size - 150)
    if (max < 150) { max = 150 }
    var resize = new YAHOO.util.Resize(this._firstDiv, {
        handles: ['r'],
        minWidth: 150,
        maxWidth: max
    });
    resize.on('resize', function(ev) {
        var w = ev.width;
        YAHOO.util.Dom.setStyle(this._firstDiv, 'height', '');
        YAHOO.util.Dom.setStyle(this._secondDiv, 'width', (size - w - 6) + 'px');
    });

    resize.resize(null, 200, 200, 0, 0, true);
  },
})

MLAB.GUI.WidgetFactory.registerWidgetClass("Dialog", MLAB.YUI.Dialog, /*overwrite=*/true)
MLAB.GUI.WidgetFactory.registerWidgetClass("Slider", MLAB.YUI.Slider, /*overwrite=*/true)
MLAB.GUI.WidgetFactory.registerWidgetClass("Splitter", MLAB.YUI.Splitter, /*overwrite=*/true)
MLAB.GUI.WidgetFactory.registerWidgetClass("Window", MLAB.YUI.Window, /*overwrite=*/true)
