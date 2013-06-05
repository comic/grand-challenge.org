MLAB.JQuery.deriveClass("Widget", MLAB.GUI.Widget, {

  Widget: function() {
    this._jqueryObject = null
    MLAB.JQuery.Widget.super.constructor.call(this)
  },

  _setJQueryObject: function(jqueryObject) {
    this._jqueryObject = jqueryObject
    this._setDOMElement(jqueryObject[0])
    this._jqueryObject.on("hide", this.callback("_handleHideEvent"))
    this._jqueryObject.on("show", this.callback("_handleShowEvent"))
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
    this._jqueryObject.render(domParent)
  },
  
  setVisible: function(visible) {
    if (this.isVisible() !== visible) {
      MLAB.JQuery.Widget.super.setVisible.call(this, visible)
      if (visible) {
        this._jqueryObject.show()
      } else {
        this._jqueryObject.hide()
      }
    }
  },
  
  _addWidgetToDOM: function(widget) {
    this._jqueryObject.append(widget._getDOMElement())
  },
  
  _removeWidgetFromDOM: function(widget) {
      // TODO: check correct function
    this._jqueryObject.remove(widget._getDOMElement())
  },
}, {
  // static members

  _jqueryBaseUrl: "",
  
  setJQueryBaseUrl: function(url) {
    MLAB.JQuery.Widget._jqueryBaseUrl = url
  },
    
  getJQueryBaseUrl: function(url) {
    return MLAB.JQuery.Widget._jqueryBaseUrl
  }
})

MLAB.JQuery.deriveClass("Window", MLAB.JQuery.Widget, {
  Window: function() {
    this._panel = null
    MLAB.JQuery.Window.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    var html = '<div title="TODO"></div>';
    this._panel = $(self._domElement).append(html);
    this._panel.dialog();
    this._setJQueryObject(this._panel);
  },
  
  setId: function(id) {
    this._panel.attr("id", id);
  },

})


MLAB.JQuery.deriveClass("Dialog", MLAB.JQuery.Widget, {
  Dialog: function() {
    this._panel = null
    MLAB.JQuery.Dialog.super.constructor.call(this)
  },
  
  _createDOMElement: function() {
    var html = '<div title="TODO"></div>';
    this._panel = $(self._domElement).append(html);
    this._panel.dialog();
    this._setJQueryObject(this._panel);
  },
  
  setId: function(id) {
    this._panel.attr("id", id);
  },
})


/** \class MLAB.JQuery.Slider
 * 
 */
MLAB.JQuery.deriveClass("Slider", MLAB.GUI.Slider, {
  Slider: function(interval) {
    MLAB.JQuery.Slider.super.constructor.call(this)
    this._scaleFactor = 1
    this._isFloatValue = false
    this._signalsWereBlocked = false
    this._isSliding = false
  },

  _createDOMElement: function() {
    var html = '<input type="range" name="slider-1" id="slider-1" min="'+this._minimumValue+'" max="'+this._maxmumValue+'" value="50" data-highlight="true" />';
    this._slider = $(html);
    this._setDOMElement(this._slider[0]);
  },
  
  onShow: function() {
    this._slider.on("change", this.callback("_onSliderChange"))
    this._slider.on("slidestart", this.callback("_onSlideStart"))
    this._slider.on("slidestop", this.callback("_onSlideEnd"))
  },
  
  _setDOMElementEnabled: function(enabled) {
    MLAB.JQuery.Slider.super._setDOMElementEnabled.call(this, enabled)
    if (enabled) {
      this._slider.slider("enable")
    } else {
      this._slider.slider("disable")
    }
  },
  
  setRange: function(min, max) {
    MLAB.JQuery.Slider.super.setRange.call(this, min, max)
    this._slider.attr("min", min);
    this._slider.attr("max", max);
  },
  
  setIsFloatValue: function(value) {
    this._isFloatValue = value
  },
  
  _mapValueToJQuerySlider: function(value) {
    return Math.round((value - this._minimumValue)/this._scaleFactor)
  },
  
  _mapValueFromJQuerySlider: function(value) {
    var v = this._minimumValue + value * this._scaleFactor
    if (!this._isFloatValue) {
      v = Math.round(v)
    }
    return v
  },
  
  _updateSliderFromValue: function() {
    var v = this._mapValueToJQuerySlider(this._value)
    this._slider.attr("value", v)
  },
  
  _updateValueInternal: function(value) {
    if (this._signalsWereBlocked) {
      var signalsBlocked = this.signalsBlocked()
      this.blockSignals(true)
    }
    MLAB.JQuery.Slider.super._updateValue.call(this, value)
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
    return this._mapValueFromJQuerySlider(this._slider.attr("value"))
  },
  
  _onSliderChange: function(offsetFromStart) {
    if (this._emitValueChangedWhileEditing) {
      var v = this._getSliderValue()
      this._updateValueInternal(v)
    }
  },
  
  _onSlideStart: function() {
    console.log("_onSlideStart")
    this._isSliding = true
    if (this.signalsBlocked()) {
      this._signalsWereBlocked = true
    }
  },

  _onSlideEnd: function() {
    var v = this._getSliderValue()
    console.log("_onSlideEnd")
    this._updateValueInternal(v)
    this._signalsWereBlocked = false
    this._isSliding = false
  },
})

MLAB.JQuery.deriveClass("Splitter", MLAB.GUI.Splitter, {
  Splitter: function() {
    MLAB.JQuery.Splitter.super.constructor.call(this)
    this._firstDiv = null
    this._secondDiv = null
  },
  
  setDirection: function(direction) {
    MLAB.JQuery.Splitter.super.setDirection.call(this, direction)
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
      MLAB['Core'].throwException("MLAB.JQuery.Splitter can only handle two widgets")
    }
    
    MLAB.GUI.addStyleSheetClass(div, cssClass)
    
    this._domElement.appendChild(div)
    widget.appendToDOM(div)
  },
  
  _handleWidgetAdded: function(widget) {
    MLAB.JQuery.Splitter.super._handleWidgetAdded.call(this, widget)
    // the first widget is not added before the second is added
    if (this._children.length < 2) {
      return
    } else if (this._children.length > 2) {
      MLAB['Core'].throwException("MLAB.JQuery.Splitter can only handle two widgets")
    }
    if (this._direction === MLAB.GUI.Splitter.VERTICAL) {
      this._createJQueryVerticalResize()
    } else {
      this._createJQueryHorizontalResize()
    }
  },
  
  _createJQueryVerticalResize: function() {
    var height = this._getDOMElement().offsetHeight
    
    $(this._firstDiv).resizable({ 
        handles: "n, s",
        resize: function( event, ui ) {
            console.log("TODO set secondDiv")
            console.log(ui)
            //$(this._secondDiv).css("top")
        }
    })
  },
  
  _createJQueryHorizontalResize: function() {
    var size = parseInt(this._getDOMElement().offsetWidth, 10);

    var max = (size - 150)
    if (max < 150) { max = 150 }
        
    $(this._firstDiv).resizable({ 
        handles: "e, w",
        minWidth: 150,
        maxWidth: max,
        resize: function( event, ui ) {
            console.log("TODO set secondDiv")
            console.log(ui)
            //$(this._secondDiv).css("top")
            //var w = ev.width;
            //YAHOO.util.Dom.setStyle(this._firstDiv, 'height', '');
            //YAHOO.util.Dom.setStyle(this._secondDiv, 'width', (size - w - 6) + 'px');
        }
    })

    //resize.resize(null, 200, 200, 0, 0, true);
  },
})

MLAB.GUI.WidgetFactory.registerWidgetClass("Dialog", MLAB.JQuery.Dialog, /*overwrite=*/true)
MLAB.GUI.WidgetFactory.registerWidgetClass("Slider", MLAB.JQuery.Slider, /*overwrite=*/true)
MLAB.GUI.WidgetFactory.registerWidgetClass("Splitter", MLAB.JQuery.Splitter, /*overwrite=*/true)
MLAB.GUI.WidgetFactory.registerWidgetClass("Window", MLAB.JQuery.Window, /*overwrite=*/true)
