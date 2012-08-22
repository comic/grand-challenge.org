if (typeof KeyEvent == "undefined") {
    var KeyEvent = {
        DOM_VK_CANCEL: 3,
        DOM_VK_HELP: 6,
        DOM_VK_BACK_SPACE: 8,
        DOM_VK_TAB: 9,
        DOM_VK_CLEAR: 12,
        DOM_VK_RETURN: 13,
        DOM_VK_ENTER: 14,
        DOM_VK_SHIFT: 16,
        DOM_VK_CONTROL: 17,
        DOM_VK_ALT: 18,
        DOM_VK_PAUSE: 19,
        DOM_VK_CAPS_LOCK: 20,
        DOM_VK_ESCAPE: 27,
        DOM_VK_SPACE: 32,
        DOM_VK_PAGE_UP: 33,
        DOM_VK_PAGE_DOWN: 34,
        DOM_VK_END: 35,
        DOM_VK_HOME: 36,
        DOM_VK_LEFT: 37,
        DOM_VK_UP: 38,
        DOM_VK_RIGHT: 39,
        DOM_VK_DOWN: 40,
        DOM_VK_PRINTSCREEN: 44,
        DOM_VK_INSERT: 45,
        DOM_VK_DELETE: 46,
        DOM_VK_0: 48,
        DOM_VK_1: 49,
        DOM_VK_2: 50,
        DOM_VK_3: 51,
        DOM_VK_4: 52,
        DOM_VK_5: 53,
        DOM_VK_6: 54,
        DOM_VK_7: 55,
        DOM_VK_8: 56,
        DOM_VK_9: 57,
        DOM_VK_SEMICOLON: 59,
        DOM_VK_EQUALS: 61,
        DOM_VK_A: 65,
        DOM_VK_B: 66,
        DOM_VK_C: 67,
        DOM_VK_D: 68,
        DOM_VK_E: 69,
        DOM_VK_F: 70,
        DOM_VK_G: 71,
        DOM_VK_H: 72,
        DOM_VK_I: 73,
        DOM_VK_J: 74,
        DOM_VK_K: 75,
        DOM_VK_L: 76,
        DOM_VK_M: 77,
        DOM_VK_N: 78,
        DOM_VK_O: 79,
        DOM_VK_P: 80,
        DOM_VK_Q: 81,
        DOM_VK_R: 82,
        DOM_VK_S: 83,
        DOM_VK_T: 84,
        DOM_VK_U: 85,
        DOM_VK_V: 86,
        DOM_VK_W: 87,
        DOM_VK_X: 88,
        DOM_VK_Y: 89,
        DOM_VK_Z: 90,
        DOM_VK_CONTEXT_MENU: 93,
        DOM_VK_NUMPAD0: 96,
        DOM_VK_NUMPAD1: 97,
        DOM_VK_NUMPAD2: 98,
        DOM_VK_NUMPAD3: 99,
        DOM_VK_NUMPAD4: 100,
        DOM_VK_NUMPAD5: 101,
        DOM_VK_NUMPAD6: 102,
        DOM_VK_NUMPAD7: 103,
        DOM_VK_NUMPAD8: 104,
        DOM_VK_NUMPAD9: 105,
        DOM_VK_MULTIPLY: 106,
        DOM_VK_ADD: 107,
        DOM_VK_SEPARATOR: 108,
        DOM_VK_SUBTRACT: 109,
        DOM_VK_DECIMAL: 110,
        DOM_VK_DIVIDE: 111,
        DOM_VK_F1: 112,
        DOM_VK_F2: 113,
        DOM_VK_F3: 114,
        DOM_VK_F4: 115,
        DOM_VK_F5: 116,
        DOM_VK_F6: 117,
        DOM_VK_F7: 118,
        DOM_VK_F8: 119,
        DOM_VK_F9: 120,
        DOM_VK_F10: 121,
        DOM_VK_F11: 122,
        DOM_VK_F12: 123,
        DOM_VK_F13: 124,
        DOM_VK_F14: 125,
        DOM_VK_F15: 126,
        DOM_VK_F16: 127,
        DOM_VK_F17: 128,
        DOM_VK_F18: 129,
        DOM_VK_F19: 130,
        DOM_VK_F20: 131,
        DOM_VK_F21: 132,
        DOM_VK_F22: 133,
        DOM_VK_F23: 134,
        DOM_VK_F24: 135,
        DOM_VK_NUM_LOCK: 144,
        DOM_VK_SCROLL_LOCK: 145,
        DOM_VK_COMMA: 188,
        DOM_VK_PERIOD: 190,
        DOM_VK_SLASH: 191,
        DOM_VK_BACK_QUOTE: 192,
        DOM_VK_OPEN_BRACKET: 219,
        DOM_VK_BACK_SLASH: 220,
        DOM_VK_CLOSE_BRACKET: 221,
        DOM_VK_QUOTE: 222,
        DOM_VK_META: 224
    };
}



function MLABEventHandler() {
  var self = this;
  
  this._keyTranslationMap = null;
  this._textlessTranslationMap = null;
  
  this._getQtButtonCode = function(button) {
    switch(button) {
      case 0:
      return 1;
      case 1:
      return 4;
      case 2:
      return 2;
    } 
    return 0;
  };

  this._initKeyTranslationMap = function() {
    self._keyTranslationMap = {}; 
    self._textlessTranslationMap = {}; 
    self._textlessTranslationMap[KeyEvent.DOM_VK_CANCEL] =      0x01020001;
    self._textlessTranslationMap[KeyEvent.DOM_VK_HELP] =        0x01000058;
    self._keyTranslationMap[KeyEvent.DOM_VK_BACK_SPACE] =       0x01000003;
    self._keyTranslationMap[KeyEvent.DOM_VK_TAB] =              0x01000001;
    self._keyTranslationMap[KeyEvent.DOM_VK_CLEAR] =            0x0100000b;
    self._keyTranslationMap[KeyEvent.DOM_VK_RETURN] =           0x01000004;
    self._keyTranslationMap[KeyEvent.DOM_VK_ENTER] =            0x01000005;
    self._textlessTranslationMap[KeyEvent.DOM_VK_SHIFT] =       0x01000020;
    self._textlessTranslationMap[KeyEvent.DOM_VK_CONTROL] =     0x01000021;
    self._textlessTranslationMap[KeyEvent.DOM_VK_ALT] =         0x01000023;
    self._textlessTranslationMap[KeyEvent.DOM_VK_PAUSE] =       0x01000008;
    self._textlessTranslationMap[KeyEvent.DOM_VK_CAPS_LOCK] =   0x01000024;
    self._keyTranslationMap[KeyEvent.DOM_VK_ESCAPE] =           0x01000000;
    self._keyTranslationMap[KeyEvent.DOM_VK_SPACE] =            0x20;
    self._textlessTranslationMap[KeyEvent.DOM_VK_PAGE_UP] =     0x01000016;
    self._textlessTranslationMap[KeyEvent.DOM_VK_PAGE_DOWN] =   0x01000017;
    self._textlessTranslationMap[KeyEvent.DOM_VK_END] =         0x01000011;
    self._textlessTranslationMap[KeyEvent.DOM_VK_HOME] =        0x01000010;
    self._textlessTranslationMap[KeyEvent.DOM_VK_LEFT] =        0x01000012;
    self._textlessTranslationMap[KeyEvent.DOM_VK_UP] =          0x01000013;
    self._textlessTranslationMap[KeyEvent.DOM_VK_RIGHT] =       0x01000014;
    self._textlessTranslationMap[KeyEvent.DOM_VK_DOWN] =        0x01000015;
    self._textlessTranslationMap[KeyEvent.DOM_VK_PRINTSCREEN] = 0x01000009;
    self._textlessTranslationMap[KeyEvent.DOM_VK_INSERT] =      0x01000006;
    self._textlessTranslationMap[KeyEvent.DOM_VK_DELETE] =      0x01000007;
    self._keyTranslationMap[KeyEvent.DOM_VK_SEMICOLON] =        0x3b;
    self._keyTranslationMap[KeyEvent.DOM_VK_EQUALS] =           0x3d;
    /*
        self._KeyEvent.DOM_VK_NUMPAD0:
        self._KeyEvent.DOM_VK_NUMPAD1:
        self._KeyEvent.DOM_VK_NUMPAD2:
        self._KeyEvent.DOM_VK_NUMPAD3:
        self._KeyEvent.DOM_VK_NUMPAD4:
        self._KeyEvent.DOM_VK_NUMPAD5:
        self._KeyEvent.DOM_VK_NUMPAD6:
        self._KeyEvent.DOM_VK_NUMPAD7:
        self._KeyEvent.DOM_VK_NUMPAD8:
        self._KeyEvent.DOM_VK_NUMPAD9:
        self._keyTranslationMap[KeyEvent.DOM_VK_SEPARATOR] =      0x??;
    */
    self._keyTranslationMap[KeyEvent.DOM_VK_MULTIPLY]  =          0x2a;
    self._keyTranslationMap[KeyEvent.DOM_VK_ADD]       =          0x2b;
    self._keyTranslationMap[KeyEvent.DOM_VK_SUBTRACT]  =          0x2d;
    self._keyTranslationMap[KeyEvent.DOM_VK_DECIMAL]   =          0x2e;
    self._keyTranslationMap[KeyEvent.DOM_VK_DIVIDE]    =          0x2f;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F1] =            0x01000030;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F2] =            0x01000031;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F3] =            0x01000032;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F4] =            0x01000033;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F5] =            0x01000034;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F6] =            0x01000035;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F7] =            0x01000036;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F8] =            0x01000037;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F9] =            0x01000038;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F10] =           0x01000039;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F11] =           0x0100003a;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F12] =           0x0100003b;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F13] =           0x0100003c;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F14] =           0x0100003d;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F15] =           0x0100003e;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F16] =           0x0100003f;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F17] =           0x01000040;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F18] =           0x01000041;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F19] =           0x01000042;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F20] =           0x01000043;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F21] =           0x01000044;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F22] =           0x01000045;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F23] =           0x01000046;
    self._textlessTranslationMap[KeyEvent.DOM_VK_F24] =           0x01000047;
    self._textlessTranslationMap[KeyEvent.DOM_VK_NUM_LOCK] =      0x01000025;
    self._textlessTranslationMap[KeyEvent.DOM_VK_SCROLL_LOCK] =   0x01000026;
    self._keyTranslationMap[KeyEvent.DOM_VK_COMMA] =              0x2c;
    self._keyTranslationMap[KeyEvent.DOM_VK_PERIOD] =             0x2e;
    self._keyTranslationMap[KeyEvent.DOM_VK_SLASH] =              0x2f;
    self._keyTranslationMap[KeyEvent.DOM_VK_BACK_QUOTE] =         0x27; // ??
    self._keyTranslationMap[KeyEvent.DOM_VK_OPEN_BRACKET] =       0x5b;
    self._keyTranslationMap[KeyEvent.DOM_VK_BACK_SLASH] =         0x5c;
    self._keyTranslationMap[KeyEvent.DOM_VK_CLOSE_BRACKET] =      0x5d;
    self._keyTranslationMap[KeyEvent.DOM_VK_QUOTE] =              0x60; // ??
    self._textlessTranslationMap[KeyEvent.DOM_VK_META] =          0x01000022;
  };
  

  this._getQtKeyCode = function(code) {
    if ((code >= 48 && code <= 57) || (code >= 65 && code <= 90)) {
      // digits and letters are identical
      return code;
    } else {
      return self._getQtSpecialKeyCode(code)
    }
  }
  
  this._getQtSpecialKeyCode = function(code) {
    if (self._keyTranslationMap == null) {
      self._initKeyTranslationMap();
    }
    var result = self._keyTranslationMap[code];
    if (result == undefined) {
      result = self._textlessTranslationMap[code];
    }
    return result
  };

  // returns if the key code is a textless code
  this._isTextlessKeyCode = function(code) {
    if (self._keyTranslationMap == null) {
      self._initKeyTranslationMap();
    }
    return (code in self._textlessTranslationMap);
  }
   
  this._getQtModifiersCode = function(evt) {
    var modifiers = 0;
    if (evt.shiftKey) {
      modifiers |= 0x02000000;
    }
    if (evt.ctrlKey) {
      modifiers |= 0x04000000;
    }
    if (evt.altKey) {
      modifiers |= 0x08000000;
    }
    if (evt.metaKey) {
      modifiers |= 0x10000000;
    }
    return modifiers;
  };

  this._buttons = 0;
  
  // remember which viewer should get key events (also used for mouse grabbing)
  this._currentRemoteRenderingControlTarget = null;
  
  // the target the mouse is currently over
  this._mouseTarget = null;
  
  // previous text of last keypress
  this._prevText = "";
  // previous text of last keydown
  this._prevKeyCode = 0;
  // flag to ignore next key press
  this._ignoreNextKeyPress = false;
  
  this._relMouseCoords = function(event, target) {
    var totalOffsetX = 0;
    var totalOffsetY = 0;
    var currentElement = target;
  
    do {
      totalOffsetX += currentElement.offsetLeft;
      totalOffsetY += currentElement.offsetTop;
    } 
    while (currentElement = currentElement.offsetParent);
  
    var canvasX = event.pageX - totalOffsetX;
    var canvasY = event.pageY - totalOffsetY;

    return {x:canvasX, y:canvasY};
  }
  
  this.showStatus = function(msg, event, target) {
    var pos = self._relMouseCoords(event, target);
    var tmpMsg = msg;
    if (gApp.getSystemInfo().isIOS()) { tmpMsg += " IOS "; }
    if (gApp.getSystemInfo().isIE9()) { tmpMsg += " IE9 "; }
    if ("button" in event) {
      tmpMsg += ", button: " + event.button + ", x: " + pos.x + ", y: " + pos.y + " ";
    } else {
      tmpMsg += ", keyCode: " + event.keyCode + " ";
    }
    if (event.shiftKey) { tmpMsg += "[SHIFT]"; }
    if (event.ctrlKey) { tmpMsg += "[CTRL]"; }
    if (event.altKey) { tmpMsg += "[ALT]"; }
    
    console.log(tmpMsg);
    /*try {
      var status = document.getElementById("status");
      if (!status) {
        status = document.createElement("div");
        status.id = "status";
        document.body.appendChild(status);
      }
      
      status.innerHTML = tmpMsg;
    } catch (e) {
      console.log(e);
    }*/
  }
  
  this.handleEvent = function(evt, target, type) {
    if (!target) {
      if (gApp.isReady()) {
        gApp.logError("Target is not valid although application is ready: " + target + ", " + evt.type + ", " + type + ", " + evt.target + 
            ", " + self._currentRemoteRenderingControlTarget + ", " + self._mouseTarget);
      }
      // else it is ok that the target is not valid, because the user caused events
      // while the document is still loading
      return;
    }
    if (typeof type == "undefined") {
      type = evt.type;
    }

    /*if (type != "mousemove") {
      self.showStatus(type, evt, target);
    }*/
    
    var r = gApp.getRemoteRenderingControlAndModuleContext(target);
    var control = r.control;
    var moduleContext = r.moduleContext;
    var slaveID = control.getRemoteRenderingSlaveID();
    if (slaveID) {
      var baseField = control.getBaseField(); //target.id;
      var msg = [baseField, "1", slaveID];
      if (type == "keydown" || type == "keypress" || type == "keyup") {
        text = ""
        if (type == "keydown") {
          qtCode = self._getQtKeyCode(evt.keyCode);
          self._prevKeyCode = qtCode
          self._prevText = ""
          if (self._isTextlessKeyCode(evt.keyCode)) {
            // we ignore the next keydown and use the current event to send the
            // textless event
            self._ignoreNextKeyPress = true
          } else {
            // we send the code with the keypress event later on, since that gives us the 'text'
            self._ignoreNextKeyPress = false
            return;
          }
        } else if (type == "keypress") {
          if (self._ignoreNextKeyPress) {
            self._ignoreNextKeyPress = false
            return
          }
          qtCode = self._prevKeyCode;
          text = String.fromCharCode(evt.charCode);
          self._prevText = text;
        } else if (type == "keyup") {
          qtCode = self._getQtKeyCode(evt.keyCode);
          text = self._prevText;
        }
        //console.log(type + " " + qtCode + " " + text)

        if (typeof qtCode == "undefined") {
          // unsupported key code
          return;
        }
        if (text=="\\") {
          text = "\\\\"
        }
        msg.push(type == "keyup" ? 7 : 6);
        msg.push(qtCode);
        msg.push(self._getQtModifiersCode(evt));
        msg.push(text);  // text generated by pressed key
        msg.push("false");  // auto-repeat?
        msg.push(1);  // number of keys involved in this event
      } else if (type == "mouseover") {
        self._currentRemoteRenderingControlTarget = target;
        msg.push(10);
      } else if (type == "mouseout") {
        self._currentRemoteRenderingControlTarget = null;
        msg.push(11);
      } else {
        var buttonCode = 0;
        if (type == "mousedown") {
          msg.push(2);
          buttonCode = self._getQtButtonCode(evt.button);
          self._buttons |= buttonCode;
        } else if (type == "mouseup") {
          msg.push(3);
          buttonCode = self._getQtButtonCode(evt.button);
          self._buttons &= ~buttonCode;
        } else if (type == "dblclick") {
          msg.push(4);
          buttonCode = self._getQtButtonCode(evt.button);
        } else if (type == "mousemove") {
          msg.push(5);
        }
        if (!evt.isTouch) {
          evt.preventDefault();
        }
        var position = self._relMouseCoords(evt, target)
        if (self.isWheelEvent(evt)) {
          var qtOrientation = 2; // 1 == x, 2 == y
          var delta = 0;
          if (evt.wheelDeltaX) {
            // Chrome
            qtOrientation = 1;
            delta = evt.wheelDeltaX; 
          } else if (evt.wheelDeltaY) {
            // Chrome
            delta = evt.wheelDeltaY;
          } else if (evt.wheelDelta) {
            // IE/Opera
            delta = evt.wheelDelta;
            // TODO: determine the orientation here
          } else if (evt.detail) {
            // Firefox
            delta = -evt.detail * (gApp.getSystemInfo().isMacOS() ? 120 : 40);
            if (evt.axis == evt.HORIZONTAL_AXIS) {
              qtOrientation = 1;
            }
          }
          msg.push(31);
          msg.push(position.x);
          msg.push(position.y);
          msg.push(delta);
          msg.push(self._buttons);
          msg.push(self._getQtModifiersCode(evt));
          msg.push(qtOrientation);
        } else {        
          msg.push(position.x);
          msg.push(position.y);
          msg.push(buttonCode);
          msg.push(self._buttons);
          msg.push(self._getQtModifiersCode(evt));
        }
      }
      
      var message = new MLABRenderingQEventMessage();
      message.setData(msg);
      moduleContext.sendMessage(message);
      
      //if (is_verbose || is_verbose_events) { console.log("SEND " + msg.join(" , ")) }      
      if (type == "mouseup" && self._buttons == 0 && 
          self._mouseTarget != self._currentRemoteRenderingControlTarget) {
        // mouse was released outside of canvas, we must send the Leave event now:
        self.handleEvent(evt, self._currentRemoteRenderingControlTarget, "mouseout");
        if (self._mouseTarget) {
          // we are over another viewer now, we must send an Enter and a MouseMove event, but to the new viewer
          self.handleEvent(evt, self._mouseTarget, "mouseover");
          self.handleEvent(evt, self._mouseTarget, "mousemove");
        }
      }
    }
    return false;
  };

  this.handleLocalMouseEvent = function(evt) {
    try {
      var target = evt.target;
      if ((self._buttons == 0)) {
        self.handleEvent(evt, target);
      }
      if (evt.type == "mouseover") {
        self._mouseTarget = target;
      } else if (evt.type == "mouseout") {
        self._mouseTarget = null;
      }
    } catch (e) {
      gApp.logException(e);
    }
  };
  
  this.isWheelEvent = function(evt) {
    return ((evt.type == "mousewheel") || (evt.type == "DOMMouseScroll"));
  }
  
  this.handleGlobalMouseEvent = function(evt) {
    try {
      if ((self._buttons != 0) || (self.isWheelEvent(evt) && self._currentRemoteRenderingControlTarget)) {
        self.handleEvent(evt, self._currentRemoteRenderingControlTarget);
      }
    } catch (e) {
      gApp.logException(e);
    }
  };
  
  this.handleKeyEvent = function(evt) {
    try {
      if (self._currentRemoteRenderingControlTarget) {
        return self.handleEvent(evt, self._currentRemoteRenderingControlTarget)
      } else {
        return true;
      }
    } catch (e) {
      gApp.logException(e);
    }
  };
  
  /*this.handleChangeEvent = function(evt) {
    try {
      var fieldName = evt.target.id;
      var fieldValue = evt.target.value;
      var options = "0";
      var message = new MLABModuleSetFieldValuesMessage();
      message.setFieldData([[fieldName, fieldValue, options]]);
      gApp.sendMessage(message);
    } catch (e) {
      gApp.logException(e);
    }
    return false;
  };*/
  
  this.dummyHandler = function(event) {
    return false;
  };
  
  this._mouseEvent = null;

  this.touchStart = function(event) {
    try {
      event.preventDefault();
  
      //pos = self._relMouseCoords(event.touches[0])
      //document.getElementById("status").innerHTML = "touch start " + pos.x + " " + pos.y; 
  
      var target = event.touches[0].target;
      var touch = event.touches[0];
      //self.handleEvent({type:"mouseover",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}, target);
      self._mouseEvent = {};
      self._mouseEvent.isTouch = true;
      self._mouseEvent.button = event.touches.length-1;
      self._mouseEvent.pageX = touch.pageX;
      self._mouseEvent.pageY = touch.pageY;
      self._mouseEvent.target = event.target;
      self._mouseEvent.type = "mouseover";
      self.handleEvent(self._mouseEvent, target);
      self._mouseEvent.type = "mousedown"
      self.handleEvent(self._mouseEvent, event.target);

      //self._mouseEvent = {type:"mousedown",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}; 
      //self.handleEvent(self._mouseEvent, target);
    } catch (e) {
      gApp.logException(e);
    }
  };

  this.touchMove = function(event) {
    try {
      event.preventDefault();
  
  //    pos = self._relMouseCoords(event.touches[0])
  //    document.getElementById("status").innerHTML = "touch move " + pos.x + " " + pos.y; 
  
      var target = event.touches[0].target;
       if (!target) return;
      //console.log(target + " - "+ event.target);
      var touch = event.touches[0];
      self._mouseEvent = {}
      self._mouseEvent.isTouch = true;
      self._mouseEvent.button = event.touches.length-1
      self._mouseEvent.type = "mousemove"
      self._mouseEvent.pageX = touch.pageX;
      self._mouseEvent.pageY = touch.pageY;
      self._mouseEvent.target = event.target;
      self.handleEvent(self._mouseEvent, event.target);
      

      //var touch = event.touches[0];
      //mouseEvent = {type:"mousemove",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}; 
      //self.handleEvent(mouseEvent, target);
    } catch (e) {
      gApp.logException(e);
    }
  };

  this.touchEnd = function(event) {
    try {
      event.preventDefault();
  
      var touch = event.changedTouches[0];
      //self._mouseEvent = {}
      self._mouseEvent.isTouch = true;
      self._mouseEvent.type = "mouseup";
      self._mouseEvent.pageX = touch.pageX;
      self._mouseEvent.pageY = touch.pageY;
      //self._mouseEvent.target = event.target;
      self.handleEvent(self._mouseEvent, self._mouseEvent.target);
      self._mouseEvent.type = "mouseout"
      self.handleEvent(self._mouseEvent, self._mouseEvent.target);
      
      //self._mouseEvent.type = "mouseup";
      //self._mouseEvent.button = 1;
      //self.handleEvent(self._mouseEvent, self._mouseEvent.target);

      //self._mouseEvent.type = "mouseup";
      //self.handleEvent(self._mouseEvent, self._mouseEvent.target);
  
      //self.handleEvent({type:"mouseout", target:self._mouseEvent.target}, self._mouseEvent.target);
    } catch (e) {
      gApp.logException(e);
    }
  };

  this.touchCancel = function(event) {
    try {
      event.preventDefault();
  //    document.getElementById("status").innerHTML = "touch cancel"; 
    } catch (e) {
      gApp.logException(e);
    }
  };
  
  window.onkeydown = this.handleKeyEvent;
  window.onkeypress = this.handleKeyEvent;
  window.onkeyup = this.handleKeyEvent;
  window.addEventListener("mousedown", this.handleGlobalMouseEvent, true);
  window.addEventListener("mousemove", this.handleGlobalMouseEvent, false);
  window.addEventListener("mouseup", this.handleGlobalMouseEvent, false);
  

  if (window.addEventListener) {
    // Firefox case
    window.addEventListener('DOMMouseScroll', this.handleGlobalMouseEvent, false);
  }
  // other browser, do not register the function as window.onmousewheel, because
  // chrome would handle the event twice then
  document.onmousewheel = this.handleGlobalMouseEvent;
}
