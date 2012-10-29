
//=============================================================================
// YUIFieldControl
//=============================================================================
function YUIFieldControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABFieldControl;
  this.inheritFrom(mdlTree, moduleContext);
  /*
  this._setupBoolField = function() {
    self._fieldDomElement = $('<label><input type="checkbox" name="checkbox-1" /></label>');
    self._checkbox = self._fieldDomElement.find("input[type='checkbox']")
    //if (self.getField().getBoolValue()) { self._checkbox.checkboxradio('enable'); }
    self._checkbox.bind( "change", function(event, ui) {
      self._onCheckboxChange();
    });
    self._fieldDomElement = self._fieldDomElement[0];
    self._setEditableFunction = function(editable) {
      if (editable){
        self._checkbox.checkboxradio('enable');
      } else {
        self._checkbox.checkboxradio('disable');
      }
    };
  };*/
 
  this._setupEnumField = function() { 
    fldName = self.getField().getName();
    html = '<select name="select-choice-'+fldName+'" data-native-menu="false"></select>'
    self._select = $(html);
    //var select = document.createElement("select");
    var enumItems = self._field.items();
    for (var i=0; i<enumItems.length; i++) {
      //var option = document.createElement("option");
      //option.innerHTML = enumItems[i];
      //if (self._field.getValue() == enumItems[i]) { option.selected = true; }
      //select.appendChild(option);
      $(self._select).append('<option value="'+enumItems[i]+'">'+enumItems[i]+'</option>')
    }
    //self._select.onchange = self._onComboBoxChange;
    self._select.bind( "change", function(event, ui) {
      if (self._field) {
        //self._field.setValue(event.target.value);
        self._field.setCurrentItem(event.target.value);
      }
      /*if (self._activatedCommand) {
        var arguments = [self._activatedCommand, event.target.value];
        self._moduleContext.sendGenericRequest("handleRemoteComboBoxItemActivated", arguments);
      }*/
    });
    self._fieldDomElement = self._select[0];
  };
  
  this._onComboBoxChange = function() {
    var select = self._fieldDomElement;
    var item = null;
    for (var i=0; i<select.length; i++) {
      if (select.options[i].selected) {
        item = select.options[i].innerHTML;
        break;
      }
    }
    if (item != null) {
      self._field.setCurrentItem(item);
    } else {
      self._moduleContext.logError("MLABFieldControl._onComboBoxChange: no selected option found, field: " + self._field.getName());
    }
  };
  
  this._setupStringField = function() {
    var input = document.createElement("input");
    input.value = self._field.getValue();
    input.onkeydown = self._onLineEditKeyDown;
    self._fieldDomElement = input;
    
    $(input).focusout(function (event) {
      var input = self._fieldDomElement;
      self._field.setValue(input.value);
    });
  }
  this.fieldChanged = function(field) {
    if (field == self._field) {
      if (self._disabledLabelDomElement) {
        self._disabledLabelDomElement.innerHTML = self._field.getValue();
      }
      if (field.isBoolField()) {
        var input = self._fieldDomElement;
        input.checked = field.getBoolValue();
      
      } else if (field.isEnumField()) {
        var select = self._fieldDomElement;
        for (var i=0; i<select.length; i++) {
          if (select.options[i].innerHTML == field.getValue()) {
            select.options[i].selected = true;
          } else {
            select.options[i].selected = false;
          }
        }
        $("select[name|=select-choice]").selectmenu("refresh");
      } else if (field.isNumberField()) {
        self._numberFieldChanged();
      } else if (field.isStringField()) {
        self._fieldDomElement.value = field.getValue();
      }
    } else if (field == self._titleField) {
      self._titleFieldChanged();
    } else if (field == self._editField) {
      self._editFieldChanged();
    } else {
      self._moduleContext.logError("MLABFieldControl.fieldChanged: unexpected field: " + field.getName() + ":" + field.getType());
    }
  };
  
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
  
}


//=============================================================================
// JQUIWindowControl
//=============================================================================
function JQUIWindowControl(mdlTree, moduleContext) {
  var self = this;

  this.inheritFrom = MLABWindowControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setupFinished = function() {
  }
}

//=============================================================================
// JQUIButtonControl
//=============================================================================
function JQUIButtonControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABButtonControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupButtonControl = function(parentControl) {
    self.setupWidgetControl("JQUIButtonControl", parentControl);
   
    var imageUrl = null;
    var imageTree = mlabGetMDLChild(self._mdlTree, "image");
    if (imageTree) {
      imageUrl = mlabTranslatePath(imageTree.value);
    }
    
    var title = null;
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      title = titleTree.value;
    }
    fld = self.getField();
    fldName = fld.getName();
    if (fldName.search("toggle") == 0){
      html = '<input type="checkbox" id="check" /><label for="check">'+title+'</label>';
      self._button = $(self._domElement).append(html);
    } else {
      self._button = $(self._domElement).append("<button>"+title+"</button>");
    }
    
    if (imageUrl) {
      console.log("Todo image button")
      //var img = document.createElement("image");
      //img.setAttribute("src", imageUrl);
      //self._button.appendChild(img);
    }
    
    var commandTree = mlabGetMDLChild(self._mdlTree, "command");
    if (commandTree) {
      self._command = commandTree.value;
    } else {
      self._command = null;
    }
    self._button.button()
                .click(function( event ) {
                      self._onButtonClick;
                 });
            
    //self._button.bind( "click", self._onButtonClick);
  };
  
  this._onButtonClick = function() {
    if (self._command) {
      self._moduleContext.sendGenericRequest(self._command, []);
    }
  };
}


//=============================================================================
// JQUISliderControl
//=============================================================================
function JQUISliderControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABSliderControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupSliderControl = function(parentControl) {
    self.setupWidgetControl("MLABSliderControl", parentControl);
   
    var title = null;
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      title = titleTree.value;
    }
    fld = self.getField();
    html = "<input type='range' name='slider' id='slider_"+fld.getName()+"' value='"+
            fld.getValue()+
            "' min='"+
            fld.getMinValue()+
            "' max='"+
            (fld.getMaxValue())+
            "'/>"
    self._sliderId = "slider_"+fld.getName();
    self._slider = $(self._domElement).append(html);
    self._slider.bind( "change", function(event, ui) {
      f = self.getField();
      f.setValue(event.target.value);
    });
  };
  
  this.fieldChanged = function(field) {
    console.log(field.value);
    self._slider = $("#"+self._sliderId);
    if (self._slider.attr("value") != field.getValue()) {
      self._slider.attr("value", field.getValue());
      self._slider.slider('refresh');
    }
  };
}


//=============================================================================
// JQUISliderControl
//=============================================================================
function JQUICheckBoxControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABCheckBoxControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupCheckBoxControl = function(parentControl) {
    self.setupWidgetControl("JQUICheckBoxControl", parentControl);
   
    var title = null;
    var titleTree = mlabGetMDLChild(self._mdlTree, "title");
    if (titleTree) {
      title = titleTree.value;
    }
    fld = self.getField();
    checked = ""
    if (fld.getBoolValue()) {
      checked = "checked='checked'";
    }
    html = '<input type="checkbox" name="checkbox-'+fld.getName()+'" id="checkbox-'+fld.getName()+'" class="custom" '+checked+'/><label for="checkbox-'+fld.getName()+'">'+title+'</label>'
    $(self._domElement).append(html);
    self._checkBox = $(self._domElement).find("input[type='checkbox']")
    
    self._checkBox.bind( "change", function(event, ui) {
      f = self.getField();
      f.setBoolValue(event.target.checked);
    });
    
  };
}


//=============================================================================
// JQUIHorizontalControl
//=============================================================================
function JQUIHorizontalControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABHorizontalControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupJQUIHorizontalControl = function(parentDomElement) {
    self.setupHorizontalControl(parentDomElement);
  };
}


//=============================================================================
// JQUIVerticalControl
//=============================================================================
function JQUIVerticalControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABVerticalControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupJQUIVerticalControl = function(parentDomElement) {
    self.setupVerticalControl(parentDomElement);
  };
}


//=============================================================================
// JQUIComboBoxControl
//=============================================================================
function JQUIComboBoxControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABComboBoxControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupComboBoxControl = function(parentControl) {
    self.setupWidgetControl("JQUIComboBoxControl", parentControl);
    
    html = '<select name="select-choice-0" data-native-menu="false"></select>'
    self._select = $(self._domElement).append(html).children("select");
    
    var activatedCommandTree = mlabGetMDLChild(self._mdlTree, "activatedCommand");
    if (activatedCommandTree) {
      self._activatedCommand = activatedCommandTree.value;
    } else {
      self._activatedCommand = null;
    }
    
    var comboFieldTree = mlabGetMDLChild(self._mdlTree, "comboField");
    if (comboFieldTree) {
      var separatorTree = mlabGetMDLChild(self._mdlTree, "comboSeparator");
      if (separatorTree) {
        self._comboSeparator = separatorTree.value;
      } else {
        self._comboSeparator = ",";
      }
      self._comboField = self._ctx.lookupField(comboFieldTree.value);
      if (self._comboField != null) {
        self._comboField.addListener(self);
        self.fieldChanged(self._comboField);
      } else {
        self._moduleContext.logError("comboField not found: " + comboFieldTree.value);
      }
      self._useItems = false;
    } else {
      self._useItems = true;
    }
    
    if (self._useItems) {
      var items = mlabGetMDLChild(self._mdlTree, "items");
      if (items) {
        
      } else {
        self._moduleContext.logError("MLABComboBoxControl: no comboField nor combobox items given");
      }
    }

    // TODO: enum field support is not implemented!
    if (self._field) {
      self.fieldChanged(self._field);
    }

    self._select.bind( "change", function(event, ui) {
      if (self._field) {
        self._field.setValue(event.target.value);
      }
      if (self._activatedCommand) {
        var arguments = [self._activatedCommand, event.target.value];
        self._moduleContext.sendGenericRequest("handleRemoteComboBoxItemActivated", arguments);
      }
    });
  };
  
  this._setupItems = function(items) {
    for (var i=0; i<items.length; i++) {
      $(self._select).append('<option value="'+items[i]+'">'+items[i]+'</option>')
    }
  }
  this.fieldChanged = function(field) {
    try {
      var value = field.getValue();
      if (typeof(value) != 'undefined') {
        if (field == self._comboField) {
          var items = value.split(self._comboSeparator);
          self._setupItems(items);
        } else if (field == self._field) {
          var optionToSelect = null;
          for (i=0; i<self._select.options.length; i++) {
            var o = self._select.options[i];
            if (o.text != value) {
              o.selected = false;
            } else {
              optionToSelect = o;
            }
          }
          if (optionToSelect) {
            optionToSelect.selected = true;
          }
        }
      }
    } catch(e) {
      self._moduleContext.logException(e);
    }
  };
  
}

//=============================================================================
// JQUIRemoteRenderingControl
//=============================================================================
function JQUIRemoteRenderingControl(mdlTree, moduleContext) {
  var self = this;
  
  this.inheritFrom = MLABRemoteRenderingControl;
  this.inheritFrom(mdlTree, moduleContext);
  
  this.setup = this.setupJQUIRemoteRenderingControl = function(parentDomElement) {
    self.setupRemoteRenderingControl(parentDomElement);
  }; 
}


/*
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
  
  this._numberFieldChanged = function() {
    if (self._sliderSettingFieldValue) { return; }
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
  };
  
  /*
  this._setupStringField = function() {
    var r = yuiCreateLineEdit(self, self._mdlTree.value);
    self._fieldDomElement = r.input;
    self._div = r.div;
    self._dataSource = r.dataSource;
    self._autoComplete = r.autoComplete;
  };
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
    self._autoComplete = r.autoComplete;
  };
}



//=============================================================================
// YUISplitterControl
//=============================================================================
function YUISplitterControl(mdlTree, moduleContext) {
  var self = this;
  
  this.VERTICAL = 0;
  this.HORIZONTAL = 1;
  
  //this._resizers = [];
  
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


*/