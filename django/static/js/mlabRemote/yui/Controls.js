
function yuiCreateLineEdit(control, fieldName) {
  var domElement = control.getDomElement();
  
  var input = document.createElement("input");
  input.id = self.getElementId("line_edit_input");
  input.value = self._ctx.getFieldValue(fieldName);
  input.style.position = "relative";
  domElement.appendChild(input);
  
  var div = document.createElement("div");
  div.id = self.getElementId("line_edit_container");
  domElement.appendChild(div);
  
  var dataSource = new YAHOO.util.LocalDataSource([self._ctx.getFieldValue(fieldName)]);
  var autoComplete = new YAHOO.widget.AutoComplete(input.id, div.id, dataSource);
  return {"input": input, "div": div, "dataSource": dataSource, "autoComplete": autoComplete};
}


//=============================================================================
// YUIHorizontalControl
//=============================================================================
function YUIHorizontalControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABHorizontalControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupYUIHorizontalControl = function(parentDomElement) {
    self.setupHorizontalControl(parentDomElement);
  };
}


//=============================================================================
// YUIFieldControl
//=============================================================================
function YUIFieldControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABFieldControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this._setupNumberField = function() {
    var slider = self.getMDLAttribute("slider", "false");
    if (slider && mlabIsTrue(slider)) {      
      var input = document.createElement("input");
      input.value = self._field.getValue();
      input.onkeydown = self._onNumberEditKeyDown;
      //input.style.display = "inline";
      self._fieldDomElement = document.createElement("div");
      //self._fieldDomElement.style.display = "block";
      self._fieldDomElement.appendChild(input);
      
      
      var thumbImage = document.createElement("img");
      thumbImage.src =  app.yuiBaseUrl + "/examples/slider/assets/thumb-n.gif";
      
      var thumbDiv = document.createElement("div");
      thumbDiv.setAttribute("class", "yui-slider-thumb");
      thumbDiv.id = self.getElementId("slider_thumb");
      thumbDiv.style.left = "0px";
      thumbDiv.appendChild(thumbImage);
      
      var bgDiv = document.createElement("div");
      bgDiv.setAttribute("class", "yui-h-slider");
      bgDiv.style.display = "inline-block";
      bgDiv.style.verticalAlign = "bottom";
      bgDiv.id = self.getElementId("slider_bg");
      bgDiv.style.backgroundImage = "url('" + app.yuiBaseUrl + "/examples/slider/assets/bg-fader.gif')";
      bgDiv.appendChild(thumbDiv);      

      self._fieldDomElement.appendChild(bgDiv);
      
      YAHOO.util.Event.onDOMReady(function() {
        var min = 0;
        var max = 200;
        var interval = 1;
        self._slider = YAHOO.widget.Slider.getHorizSlider(bgDiv.id, thumbDiv.id, min, max, interval);        
        self._slider.animate = true;
                
        var range = self._field.getMaxValue() - self._field.getMinValue();
        self._slider.scaleFactor = (range > 0 ? (range/200) : 1);
        self._slider.getRealValue = function() { return Math.round(this.getValue() * this.scaleFactor); }

        self._slider.subscribe("change", self._onSliderChange);        

        YAHOO.util.Event.on(self._fieldDomElement.children[0], "keydown", function(e) {
          if (YAHOO.util.Event.getCharCode(e) === KeyEvent.DOM_VK_ENTER) {
            var v = parseFloat(this.value, 10);
            v = (YAHOO.lang.isNumber(v)) ? v : 0;
            // convert the real value into a pixel offset
            self._slider.setValue(Math.round(v/self._slider.scaleFactor));
          }
        });

      });
    } else {
      self._setupStringField();
    }
  };
  
  this._onSliderChange = function(offsetFromStart) {    
    var input = self._fieldDomElement.children[0];
    input.value = self._slider.getRealValue();
    self._sliderSettingFieldValue = true;
    self._field.setValue(input.value);
    self._sliderSettingFieldValue = false;
  };
  
  this._onNumberEditKeyDown = function(event) {    
    if (event.keyCode == KeyEvent.DOM_VK_RETURN) {
      var input = self._fieldDomElement.children[0];
      self._field.setValue(input.value);
      // do not set the slider value here, since setting the field
      // value triggers _numberFieldChanged() already
    }
  };
  
  this._fieldControlNumberFieldChanged = this._numberFieldChanged
  this._numberFieldChanged = function() {
    if (!self._sliderSettingFieldValue) {
      if (self._slider) {
        var v = 0;
        if (self._field.isIntegerField()) {
          v = parseInt(self._field.getValue(), 10);
        } else {
          v = parseFloat(self._field.getValue(), 10);
        }
        v = (YAHOO.lang.isNumber(v)) ? v : 0;
        self._slider.setValue(Math.round(v/self._slider.scaleFactor));
      }
    }
    self._fieldControlNumberFieldChanged();
  };
  
  /*
  this._setupStringField = function() {
    var r = yuiCreateLineEdit(self, self._mdlTree.value);
    self._fieldDomElement = r.input;
    self._div = r.div;
    self._dataSource = r.dataSource;
    self._autoComplete = r.autoComplete;
  };*/
}


//=============================================================================
// YUILineEditControl
//=============================================================================
function YUILineEditControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABLineEditControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupYUILineEditControl = function(parentDomElement) {    
    self.setupLineEditControl(parentDomElement);
    /*
    var r = yuiCreateLineEdit(self, self._mdlTree.value);
    self._input = r.input;
    self._div = r.div;
    self._dataSource = r.dataSource;
    self._autoComplete = r.autoComplete;*/
  };
}


//=============================================================================
// YUIRemoteRenderingControl
//=============================================================================
function YUIRemoteRenderingControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABRemoteRenderingControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupYUIRemoteRenderingControl = function(parentDomElement) {
    self.setupRemoteRenderingControl(parentDomElement);
  }; 
}


//=============================================================================
// YUISplitterControl
//=============================================================================
function YUISplitterControl(mdlTree, moduleContext) {
  var self = this;
  
  this.VERTICAL = 0;
  this.HORIZONTAL = 1;
  
  this.inheritFrom = MLABWidgetControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupYUISplitterControl = function(parentControl) {
    self.setupWidgetControl("YUISplitterControl", parentControl);
    
    var d = self.getMDLAttribute("direction", "horizontal");
    if (d == "vertical") {
      self._direction = self.VERTICAL;
      self._domElement.setAttribute("class", self._domElement.getAttribute("class") + " yui-g VerticalSplitter");
    } else {
      self._direction = self.HORIZONTAL;
      self._domElement.setAttribute("class", self._domElement.getAttribute("class") + " yui-g HorizontalSplitter");
    }
  }; 
  
  this._setupChildrenVertical = function() {
    if (self._mdlTree.children) {
      for (var i=0; i<self._mdlTree.children.length; i++) {
        var c = self._moduleContext.createControl(self._mdlTree.children[i]);
        if (c) { self.setupChild(c); }
      }
    }
  };
  
  this._setupChildrenHorizontal = function() {
    if (self._mdlTree.children) {
      for (var i=0; i<self._mdlTree.children.length; i++) {
        var c = self._moduleContext.createControl(self._mdlTree.children[i]);
        if (c) { self.setupHorizontalChild(c); }
      }
    }
  };
  
  this.setupChildren = function() {
    try {
      if (self._direction == self.VERTICAL) {
        self._setupChildrenVertical();
      } else {
        self._setupChildrenHorizontal();
      }
      if (self._domElement.childNodes.length > 2) {
        self._moduleContext.log("Warning: YUISplitterControl does not support more than 2 children")
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
  
  this.setupHorizontalChild = function(childControl) {
    childControl.setup(self);
    childControl.setupTypicalTags();
    self.appendHorizontalChild(childControl);
    childControl.setupChildren();
  }
  
  this.appendHorizontalChild = function(childControl) {
    var children = self._domElement.childNodes;
    
    var class_ = childControl._domElement.getAttribute("class") + " yui-u";
    if (children.length == 0) { class_ += " first"; }
    childControl._domElement.setAttribute("class", class_ + " HorizontalSplitterChild");
    
    var id = self.getElementId(children.length);
    childControl._domElement.setAttribute("id", id);
    
    self._domElement.appendChild(childControl._domElement);
    
    var width = self._domElement.offsetWidth;
    
    if (children.length > 1) {
      var previousChild = children[children.length-2];
      var prevId = previousChild.getAttribute("id");

      var resize = new YAHOO.util.Resize(prevId, {
        handles: ['r'],
        minWidth: 25, 
        maxWidth: width-25
      });
      resize.on('resize', function(ev) {
        var w = ev.width;
        YAHOO.util.Dom.setStyle(previousChild, 'width', (w - 6) + 'px');
        YAHOO.util.Dom.setStyle(childControl._domElement, 'left', (w - 6) + 'px');
        YAHOO.util.Dom.setStyle(childControl._domElement, 'width', (width - w - 6) + 'px');
      });
    }
  };
  
  this.appendChild = function(childControl) {
    if (self._direction == self.VERTICAL) {
      self._domElement.appendChild(childControl._domElement);

      var children = self._domElement.childNodes;

      var id = self.getElementId(children.length-1);
      childControl._domElement.setAttribute("id", id);
      var class_ = childControl._domElement.getAttribute("class");
      childControl._domElement.setAttribute("class", class_ + " VerticalSplitterChild");

      var height = self._domElement.offsetHeight;
      
      if (children.length > 1) {
        var previousChild = children[children.length-2];
        var prevId = previousChild.getAttribute("id");

        var resize = new YAHOO.util.Resize(prevId, {
          handles: ['b'],
          minHeight: 25, 
          maxHeight: height-25
        });
        resize.on('resize', function(ev) {
          var h = ev.height;
          YAHOO.util.Dom.setStyle(previousChild, 'height', (h - 6) + 'px');
          YAHOO.util.Dom.setStyle(childControl._domElement, 'top', (h - 6) + 'px');
          YAHOO.util.Dom.setStyle(childControl._domElement, 'height', (height - h - 6) + 'px');
        });
      }
    } else {
      self._moduleContext.logError("YUISplitterControl.appendChild: horizontal direction is unsupported");
    }
  };
}


//=============================================================================
// YUIVerticalControl
//=============================================================================
function YUIVerticalControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABVerticalControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupYUIVerticalControl = function(parentDomElement) {
    self.setupVerticalControl(parentDomElement);
  };
}


//=============================================================================
// YUIWindowControl
//=============================================================================
function YUIWindowControl(mdlTree, moduleContext) {
  var self = this;

  this.inheritFrom = MLABWindowControl;
  this.inheritFrom(mdlTree, moduleContext);
}
