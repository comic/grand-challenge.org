/** \class MLAB.Core.KeyEvent
 */
MLAB.Core.defineClass("KeyEvent", {
  KeyEvent: function(type, text, qtKeyCode, qtModifiersCode) {
    this.type = type
    this.qtKeyCode = qtKeyCode
    this.text = text
    this.qtModifiersCode = qtModifiersCode
  },
}, {
  // static members
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
})

/** \class MLAB.Core.MouseEvent
 */
MLAB.Core.defineClass("MouseEvent", {
  MouseEvent: function(type, relativePosition, qtButtons, qtButtonCode, qtModifiersCode) {
    this.type = type
    this.isWheelEvent = false
    
    this.qtModifiersCode = qtModifiersCode
    this.qtButtons = qtButtons
    this.qtButtonCode = qtButtonCode  
    this.relativePosition = relativePosition
  },
})

/** \class MLAB.Core.WheelEvent
 */
MLAB.Core.deriveClass("WheelEvent", MLAB.Core.MouseEvent, {
  WheelEvent: function(type, relativePosition, qtButtons, qtModifiersCode, qtOrientation, wheelEventDelta) {
    // pass 1 as qtButtonCode, it is ignored later on, because it is only evaluated for mouse events
    MLAB.Core.WheelEvent.super.constructor.call(this, type, relativePosition, qtButtons, /*qtButtonCode=*/1, qtModifiersCode)
  
    this.isWheelEvent = true

    this.qtOrientation = qtOrientation // 1 === x, 2 === y
    this.wheelEventDelta = wheelEventDelta
  },
})


;(function() {
  var keyTranslationMap = null
  var textlessTranslationMap = null
  
  function initKeyTranslationMap() {
    keyTranslationMap = {}
    textlessTranslationMap = {}
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_CANCEL] =      0x01020001
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_HELP] =        0x01000058
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_BACK_SPACE] =       0x01000003
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_TAB] =              0x01000001
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_CLEAR] =            0x0100000b
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_RETURN] =           0x01000004
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_ENTER] =            0x01000005
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SHIFT] =       0x01000020
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_CONTROL] =     0x01000021
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_ALT] =         0x01000023
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_PAUSE] =       0x01000008
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_CAPS_LOCK] =   0x01000024
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_ESCAPE] =           0x01000000
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SPACE] =            0x20
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_PAGE_UP] =     0x01000016
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_PAGE_DOWN] =   0x01000017
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_END] =         0x01000011
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_HOME] =        0x01000010
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_LEFT] =        0x01000012
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_UP] =          0x01000013
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_RIGHT] =       0x01000014
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_DOWN] =        0x01000015
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_PRINTSCREEN] = 0x01000009
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_INSERT] =      0x01000006
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_DELETE] =      0x01000007
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SEMICOLON] =        0x3b
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_EQUALS] =           0x3d
    /*
        KeyEvent.DOM_VK_NUMPAD0:
        KeyEvent.DOM_VK_NUMPAD1:
        KeyEvent.DOM_VK_NUMPAD2:
        KeyEvent.DOM_VK_NUMPAD3:
        KeyEvent.DOM_VK_NUMPAD4:
        KeyEvent.DOM_VK_NUMPAD5:
        KeyEvent.DOM_VK_NUMPAD6:
        KeyEvent.DOM_VK_NUMPAD7:
        KeyEvent.DOM_VK_NUMPAD8:
        KeyEvent.DOM_VK_NUMPAD9:
        keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SEPARATOR] =      0x??
    */
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_MULTIPLY]  =          0x2a
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_ADD]       =          0x2b
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SUBTRACT]  =          0x2d
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_DECIMAL]   =          0x2e
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_DIVIDE]    =          0x2f
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F1] =            0x01000030
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F2] =            0x01000031
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F3] =            0x01000032
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F4] =            0x01000033
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F5] =            0x01000034
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F6] =            0x01000035
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F7] =            0x01000036
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F8] =            0x01000037
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F9] =            0x01000038
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F10] =           0x01000039
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F11] =           0x0100003a
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F12] =           0x0100003b
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F13] =           0x0100003c
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F14] =           0x0100003d
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F15] =           0x0100003e
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F16] =           0x0100003f
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F17] =           0x01000040
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F18] =           0x01000041
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F19] =           0x01000042
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F20] =           0x01000043
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F21] =           0x01000044
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F22] =           0x01000045
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F23] =           0x01000046
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_F24] =           0x01000047
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_NUM_LOCK] =      0x01000025
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SCROLL_LOCK] =   0x01000026
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_COMMA] =              0x2c
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_PERIOD] =             0x2e
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_SLASH] =              0x2f
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_BACK_QUOTE] =         0x27 // ??
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_OPEN_BRACKET] =       0x5b
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_BACK_SLASH] =         0x5c
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_CLOSE_BRACKET] =      0x5d
    keyTranslationMap[MLAB.Core.KeyEvent.DOM_VK_QUOTE] =              0x60 // ??
    textlessTranslationMap[MLAB.Core.KeyEvent.DOM_VK_META] =          0x01000022  
  }
  
  function getQtSpecialKeyCode(code) {
    if (keyTranslationMap === null) {
      initKeyTranslationMap()
    }
    var result = keyTranslationMap[code]
    if (result === undefined) {
      result = textlessTranslationMap[code]
    }
    return result
  }
  
  MLAB.Core.getQtButtonCode = function(button) {
    switch(button) {
      case 0:
      return 1
      case 1:
      return 4
      case 2:
      return 2
    } 
    return 0
  }
  

  MLAB.Core.getQtKeyCode = function(code) {
    if ((code >= 48 && code <= 57) || (code >= 65 && code <= 90)) {
      // digits and letters are identical
      return code
    } else {
      return getQtSpecialKeyCode(code)
    }
  }

  // returns if the key code is a textless code
  MLAB.Core.isTextlessKeyCode = function(code) {
    if (keyTranslationMap === null) {
      initKeyTranslationMap()
    }
    return (code in textlessTranslationMap)
  }
   
  MLAB.Core.getQtModifiersCode = function(event) {
    var modifiers = 0
    if (event.shiftKey) {
      modifiers |= 0x02000000
    }
    if (event.ctrlKey) {
      modifiers |= 0x04000000
    }
    if (event.altKey) {
      modifiers |= 0x08000000
    }
    if (event.metaKey) {
      modifiers |= 0x10000000
    }
    return modifiers
  }

})()


/** \class MLAB.Core.EventHandler
 * 
 */
MLAB.Core.defineClass("EventHandlerSingleton", {
  EventHandlerSingleton: function() {
    
    this._logger = null
    
    this._buttons = 0
    
    // remember which viewer should get key events (also used for mouse grabbing)
    this._currentRemoteRenderingControlTarget = null
    
    // the target the mouse is currently over
    this._mouseTarget = null
    
    // previous text of last keypress
    this._prevText = ""
    // previous text of last keydown
    this._prevKeyCode = 0
    // flag to ignore next key press
    this._ignoreNextKeyPress = false
    
    this._mouseEvent = null
    
    window.addEventListener("keydown", this.callback("handleKeyEvent"), true)
    window.addEventListener("keypress", this.callback("handleKeyEvent"), true)
    window.addEventListener("keyup", this.callback("handleKeyEvent"), true)
    window.addEventListener("mousedown", this.callback("handleGlobalMouseEvent"), true)
    window.addEventListener("mousemove", this.callback("handleGlobalMouseEvent"), false)
    window.addEventListener("mouseup", this.callback("handleGlobalMouseEvent"), false)
    

    if (window.addEventListener) {
      // Firefox case
      window.addEventListener('DOMMouseScroll', this.callback("handleGlobalMouseEvent"), false)
    }
    // other browser, do not register the function as window.onmousewheel, because
    // chrome would handle the event twice then
    document.onmousewheel = this.callback("handleGlobalMouseEvent")
  },
  
  setLogger: function(logger) {
    this._logger = logger
  },
    
  _relMouseCoords: function(event, target) {
    var totalOffsetX = 0
    var totalOffsetY = 0
    var currentElement = target
  
    do {
      totalOffsetX += currentElement.offsetLeft
      totalOffsetY += currentElement.offsetTop
    } 
    while (currentElement = currentElement.offsetParent)
  
    var canvasX = event.pageX - totalOffsetX
    var canvasY = event.pageY - totalOffsetY

    return {x:canvasX, y:canvasY}
  },
  
  showStatus: function(msg, event, target) {
    var pos = this._relMouseCoords(event, target)
    var tmpMsg = msg
    if (MLAB.Core.SystemInfo.isIOS()) { tmpMsg += " IOS " }
    if (MLAB.Core.SystemInfo.isIE9()) { tmpMsg += " IE9 " }
    if ("button" in event) {
      tmpMsg += ", button: " + event.button + ", x: " + pos.x + ", y: " + pos.y + " "
    } else {
      tmpMsg += ", keyCode: " + event.keyCode + " "
    }
    if (event.shiftKey) { tmpMsg += "[SHIFT]" }
    if (event.ctrlKey) { tmpMsg += "[CTRL]" }
    if (event.altKey) { tmpMsg += "[ALT]" }
    
    console.log(tmpMsg)
    /*try {
      var status = document.getElementById("status")
      if (!status) {
        status = document.createElement("div")
        status.id = "status"
        document.body.appendChild(status)
      }
      
      status.innerHTML = tmpMsg
    } catch (e) {
      console.log(e)
    }*/
  },
  
  _getRemoteRenderingControl: function(target) {
    var remoteRenderingControl = target.widget.getControl()
    if (typeof(remoteRenderingControl) !== "undefined" && remoteRenderingControl instanceof MLAB.GUI.RemoteRenderingControl) { 
      return remoteRenderingControl
    }
    return null
  },
  
  _sendKeyEvent: function(evt, target, type, remoteRenderingControl) {
    var text = ""
    var qtCode
    if (type === "keydown") {
      qtCode = MLAB.Core.getQtKeyCode(evt.keyCode)
      this._prevKeyCode = qtCode
      this._prevText = ""
      if (MLAB.Core.isTextlessKeyCode(evt.keyCode)) {
        // we ignore the next keydown and use the current event to send the
        // textless event
        this._ignoreNextKeyPress = true
      } else {
        // we send the code with the keypress event later on, since that gives us the 'text'
        this._ignoreNextKeyPress = false
        return
      }
    } else if (type === "keypress") {
      if (this._ignoreNextKeyPress) {
        this._ignoreNextKeyPress = false
        return
      }
      qtCode = this._prevKeyCode
      text = String.fromCharCode(evt.charCode)
      this._prevText = text
    } else if (type === "keyup") {
      qtCode = MLAB.Core.getQtKeyCode(evt.keyCode)
      text = this._prevText
    }
    //console.log(type + " " + qtCode + " " + text)

    if (typeof qtCode === "undefined") {
      // unsupported key code
      return
    }
    if (text=="\\") {
      text = "\\\\"
    }
    
    var keyEvent = new MLAB.Core.KeyEvent(type, text, qtCode, MLAB.Core.getQtModifiersCode(evt))
    remoteRenderingControl.getSlave().handleKeyEvent(keyEvent)
  },
  
  _sendWheelEvent: function(evt, target, type, remoteRenderingControl) {
    if (!evt.isTouch) {
      evt.preventDefault()
    }
    var position = this._relMouseCoords(evt, target)
    var qtOrientation = 2 // 1 === x, 2 === y
    var delta = 0
    if (evt.wheelDeltaX) {
      // Chrome
      qtOrientation = 1
      delta = evt.wheelDeltaX
    } else if (evt.wheelDeltaY) {
      // Chrome
      delta = evt.wheelDeltaY
    } else if (evt.wheelDelta) {
      // IE/Opera
      delta = evt.wheelDelta
      // TODO: determine the orientation here
    } else if (evt.detail) {
      // Firefox
      delta = -evt.detail * (MLAB.Core.SystemInfo.isMacOS() ? 120 : 40)
      if (evt.axis === evt.HORIZONTAL_AXIS) {
        qtOrientation = 1
      }
    }
    var qtModifiersCode = MLAB.Core.getQtModifiersCode(evt)
    var wheelEvent = new MLAB.Core.WheelEvent(type, position, this._buttons, qtModifiersCode, qtOrientation, delta)
    remoteRenderingControl.getSlave().handleWheelEvent(wheelEvent)
  },
  
  _sendMouseEvent: function(evt, target, type, remoteRenderingControl) {
    var mouseEvent = null
    if (type === "mouseover") {
      this._currentRemoteRenderingControlTarget = target
      mouseEvent = new MLAB.Core.MouseEvent(type, {x:0,y:0}, 0, 0, 0)
    } else if (type === "mouseout") {
      this._currentRemoteRenderingControlTarget = null
      mouseEvent = new MLAB.Core.MouseEvent(type, {x:0,y:0}, 0, 0, 0)
    } else {
      var buttonCode = 0
      if (type === "mousedown") {
        buttonCode = MLAB.Core.getQtButtonCode(evt.button)
        this._buttons |= buttonCode
      } else if (type === "mouseup") {
        buttonCode = MLAB.Core.getQtButtonCode(evt.button)
        this._buttons &= ~buttonCode
      }
      if (!evt.isTouch) {
        evt.preventDefault()
      }
      var position = this._relMouseCoords(evt, target)
      var qtModifiersCode = MLAB.Core.getQtModifiersCode(evt)
      mouseEvent = new MLAB.Core.MouseEvent(type, position, this._buttons, buttonCode, qtModifiersCode)
    }
    remoteRenderingControl.getSlave().handleMouseEvent(mouseEvent)
  },
  
  handleEvent: function(evt, target, isKeyEvent, type) {
    if (!target) {
      // the target may be valid if the document is still loading and the  user already causes events,
      // ignore them
      return
    }
    if (typeof type === "undefined") {
      type = evt.type
    }

    /*if (type !== "mousemove") {
      this.showStatus(type, evt, target)
    }*/
    
    var remoteRenderingControl = this._getRemoteRenderingControl(target)
    if (remoteRenderingControl !== null) {
      if (type === "keydown" || type === "keypress" || type === "keyup") {
        this._sendKeyEvent(evt, target, type, remoteRenderingControl)
      } else {
        if (this.isWheelEvent(evt)) {
          this._sendWheelEvent(evt, target, type, remoteRenderingControl)          
        } else {
          this._sendMouseEvent(evt, target, type, remoteRenderingControl)
          //if (is_verbose || is_verbose_events) { console.log("SEND " + msg.join(" , ")) }      
          if (type === "mouseup" && this._buttons === 0 && 
              this._mouseTarget !== this._currentRemoteRenderingControlTarget) {
            // mouse was released outside of canvas, we must send the Leave event now:
            this.handleEvent(evt, this._currentRemoteRenderingControlTarget, /*isKeyEvent=*/false, "mouseout")
            if (this._mouseTarget) {
              // we are over another viewer now, we must send an Enter and a MouseMove event, but to the new viewer
              this.handleEvent(evt, this._mouseTarget, /*isKeyEvent=*/false, "mouseover")
              this.handleEvent(evt, this._mouseTarget, /*isKeyEvent=*/false, "mousemove")
            }
          }

        }
      }
    }
    return false
  },

  handleLocalMouseEvent: function(evt) {
    try {
      var target = evt.target
      if ((this._buttons === 0)) {
        this.handleEvent(evt, target, /*isKeyEvent=*/false)
      }
      if (evt.type === "mouseover") {
        this._mouseTarget = target
      } else if (evt.type === "mouseout") {
        this._mouseTarget = null
      }
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  },
  
  isWheelEvent: function(evt) {
    return ((evt.type === "mousewheel") || (evt.type === "DOMMouseScroll"))
  },
  
  handleGlobalMouseEvent: function(evt) {
    try {
      if ((this._buttons !== 0) || (this.isWheelEvent(evt) && this._currentRemoteRenderingControlTarget)) {
        this.handleEvent(evt, this._currentRemoteRenderingControlTarget, /*isKeyEvent=*/false)
      }
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  },

  handleKeyEvent: function(evt) {
    try {
      if (this._currentRemoteRenderingControlTarget) {
        return this.handleEvent(evt, this._currentRemoteRenderingControlTarget, /*isKeyEvent=*/true)
      } else {
        return true
      }
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  },
  
  dummyHandler: function(event) {
    return false
  },

  touchStart: function(event) {
    try {
      event.preventDefault()
  
      //pos = this._relMouseCoords(event.touches[0])
      //document.getElementById("status").innerHTML = "touch start " + pos.x + " " + pos.y
  
      var target = event.touches[0].target
      var touch = event.touches[0]
      //this.handleEvent({type:"mouseover",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}, target)
      this._mouseEvent = {}
      this._mouseEvent.isTouch = true
      this._mouseEvent.button = event.touches.length-1
      this._mouseEvent.pageX = touch.pageX
      this._mouseEvent.pageY = touch.pageY
      this._mouseEvent.target = event.target
      this._mouseEvent.type = "mouseover"
      this.handleEvent(this._mouseEvent, target, /*isKeyEvent=*/false)
      this._mouseEvent.type = "mousedown"
      this.handleEvent(this._mouseEvent, event.target, /*isKeyEvent=*/false)

      //this._mouseEvent = {type:"mousedown",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}
      //this.handleEvent(this._mouseEvent, target)
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  },

  touchMove: function(event) {
    try {
      event.preventDefault()
  
  //    pos = this._relMouseCoords(event.touches[0])
  //    document.getElementById("status").innerHTML = "touch move " + pos.x + " " + pos.y
  
      var target = event.touches[0].target
       if (!target) return
      //console.log(target + " - "+ event.target)
      var touch = event.touches[0]
      this._mouseEvent = {}
      this._mouseEvent.isTouch = true
      this._mouseEvent.button = event.touches.length-1
      this._mouseEvent.type = "mousemove"
      this._mouseEvent.pageX = touch.pageX
      this._mouseEvent.pageY = touch.pageY
      this._mouseEvent.target = event.target
      this.handleEvent(this._mouseEvent, event.target, /*isKeyEvent=*/false)
      

      //var touch = event.touches[0]
      //mouseEvent = {type:"mousemove",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}
      //this.handleEvent(mouseEvent, target, /*isKeyEvent=*/false)
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  },

  touchEnd: function(event) {
    try {
      event.preventDefault()
  
      var touch = event.changedTouches[0]
      //this._mouseEvent = {}
      this._mouseEvent.isTouch = true
      this._mouseEvent.type = "mouseup"
      this._mouseEvent.pageX = touch.pageX
      this._mouseEvent.pageY = touch.pageY
      //this._mouseEvent.target = event.target
      this.handleEvent(this._mouseEvent, this._mouseEvent.target, /*isKeyEvent=*/false)
      this._mouseEvent.type = "mouseout"
      this.handleEvent(this._mouseEvent, this._mouseEvent.target, /*isKeyEvent=*/false)
      
      //this._mouseEvent.type = "mouseup"
      //this._mouseEvent.button = 1
      //this.handleEvent(this._mouseEvent, this._mouseEvent.target, /*isKeyEvent=*/false)

      //this._mouseEvent.type = "mouseup"
      //this.handleEvent(this._mouseEvent, this._mouseEvent.target, /*isKeyEvent=*/false)
  
      //this.handleEvent({type:"mouseout", target:this._mouseEvent.target}, this._mouseEvent.target, /*isKeyEvent=*/false)
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  },

  touchCancel: function(event) {
    try {
      event.preventDefault()
  //    document.getElementById("status").innerHTML = "touch cancel"
    } catch (e) {
      if (this._logger) {
        this._logger.logException(e)
      } else {
        throw e
      }
    }
  }
})


MLAB.Core.EventHandler = new MLAB.Core.EventHandlerSingleton()
