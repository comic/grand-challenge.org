var mevislabWS;
var _remoteModule;
var is_IE9;
var is_IOS;
var is_verbose = false;
var is_verbose_events = false;
var useStreaming = true

function getInternetExplorerVersion()
// Returns the version of Internet Explorer or a -1
// (indicating the use of another browser).
{
  var rv = -1; // Return value assumes failure.
  if (navigator.appName == 'Microsoft Internet Explorer')
  {
    var ua = navigator.userAgent;
    var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
    if (re.exec(ua) != null)
      rv = parseFloat( RegExp.$1 );
  }
  return rv;
}

//===========================================================================

function showStatus(msg, event)
{
  var pos = relMouseCoords(event)
  var tmpMsg = msg;
  if (is_IOS) {
    tmpMsg += " IOS " 
  }
  if (is_IE9) {
    tmpMsg += " IE9 " 
  }
  if ("button" in event) {
    tmpMsg += ", button: " + event.button + ", x: " + pos.x + ", y: " + pos.y + " ";
  } else {
    tmpMsg += ", keyCode: " + event.keyCode + " ";
  }
  if (event.shiftKey) {
    tmpMsg += "[SHIFT]";
  }
  if (event.ctrlKey) {
    tmpMsg += "[CTRL]";
  }
  if (event.altKey) {
    tmpMsg += "[ALT]";
  }
  document.getElementById("status").innerHTML = tmpMsg;
}

function isTrue(value)
{
  return value == "true";
}

function getQtButtonCode(button)
{
  switch(button) {
      case 0:
      return 1;
      case 1:
      return 4;
      case 2:
      return 2;
  } 
  return 0;
}

var keyTranslationMap = {};

function initKeyTranslationMap()
{
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

    keyTranslationMap[KeyEvent.DOM_VK_CANCEL] =      0x01020001;
    keyTranslationMap[KeyEvent.DOM_VK_HELP] =        0x01000058;
    keyTranslationMap[KeyEvent.DOM_VK_BACK_SPACE] =  0x01000003;
    keyTranslationMap[KeyEvent.DOM_VK_TAB] =         0x01000001;
    keyTranslationMap[KeyEvent.DOM_VK_CLEAR] =       0x0100000b;
    keyTranslationMap[KeyEvent.DOM_VK_RETURN] =      0x01000004;
    keyTranslationMap[KeyEvent.DOM_VK_ENTER] =       0x01000005;
    keyTranslationMap[KeyEvent.DOM_VK_SHIFT] =       0x01000020;
    keyTranslationMap[KeyEvent.DOM_VK_CONTROL] =     0x01000021;
    keyTranslationMap[KeyEvent.DOM_VK_ALT] =         0x01000023;
    keyTranslationMap[KeyEvent.DOM_VK_PAUSE] =       0x01000008;
    keyTranslationMap[KeyEvent.DOM_VK_CAPS_LOCK] =   0x01000024;
    keyTranslationMap[KeyEvent.DOM_VK_ESCAPE] =      0x01000000;
    keyTranslationMap[KeyEvent.DOM_VK_SPACE] =       0x20;
    keyTranslationMap[KeyEvent.DOM_VK_PAGE_UP] =     0x01000016;
    keyTranslationMap[KeyEvent.DOM_VK_PAGE_DOWN] =   0x01000017;
    keyTranslationMap[KeyEvent.DOM_VK_END] =         0x01000011;
    keyTranslationMap[KeyEvent.DOM_VK_HOME] =        0x01000010;
    keyTranslationMap[KeyEvent.DOM_VK_LEFT] =        0x01000012;
    keyTranslationMap[KeyEvent.DOM_VK_UP] =          0x01000013;
    keyTranslationMap[KeyEvent.DOM_VK_RIGHT] =       0x01000014;
    keyTranslationMap[KeyEvent.DOM_VK_DOWN] =        0x01000015;
    keyTranslationMap[KeyEvent.DOM_VK_PRINTSCREEN] = 0x01000009;
    keyTranslationMap[KeyEvent.DOM_VK_INSERT] =      0x01000006;
    keyTranslationMap[KeyEvent.DOM_VK_DELETE] =      0x01000007;
    keyTranslationMap[KeyEvent.DOM_VK_SEMICOLON] =   0x3b;
    keyTranslationMap[KeyEvent.DOM_VK_EQUALS] =      0x3d;
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
        KeyEvent.DOM_VK_MULTIPLY:
        KeyEvent.DOM_VK_ADD:
        KeyEvent.DOM_VK_SEPARATOR:
        KeyEvent.DOM_VK_SUBTRACT:
        KeyEvent.DOM_VK_DECIMAL:
        KeyEvent.DOM_VK_DIVIDE:
     */
    keyTranslationMap[KeyEvent.DOM_VK_F1] =            0x01000030;
    keyTranslationMap[KeyEvent.DOM_VK_F2] =            0x01000031;
    keyTranslationMap[KeyEvent.DOM_VK_F3] =            0x01000032;
    keyTranslationMap[KeyEvent.DOM_VK_F4] =            0x01000033;
    keyTranslationMap[KeyEvent.DOM_VK_F5] =            0x01000034;
    keyTranslationMap[KeyEvent.DOM_VK_F6] =            0x01000035;
    keyTranslationMap[KeyEvent.DOM_VK_F7] =            0x01000036;
    keyTranslationMap[KeyEvent.DOM_VK_F8] =            0x01000037;
    keyTranslationMap[KeyEvent.DOM_VK_F9] =            0x01000038;
    keyTranslationMap[KeyEvent.DOM_VK_F10] =           0x01000039;
    keyTranslationMap[KeyEvent.DOM_VK_F11] =           0x0100003a;
    keyTranslationMap[KeyEvent.DOM_VK_F12] =           0x0100003b;
    keyTranslationMap[KeyEvent.DOM_VK_F13] =           0x0100003c;
    keyTranslationMap[KeyEvent.DOM_VK_F14] =           0x0100003d;
    keyTranslationMap[KeyEvent.DOM_VK_F15] =           0x0100003e;
    keyTranslationMap[KeyEvent.DOM_VK_F16] =           0x0100003f;
    keyTranslationMap[KeyEvent.DOM_VK_F17] =           0x01000040;
    keyTranslationMap[KeyEvent.DOM_VK_F18] =           0x01000041;
    keyTranslationMap[KeyEvent.DOM_VK_F19] =           0x01000042;
    keyTranslationMap[KeyEvent.DOM_VK_F20] =           0x01000043;
    keyTranslationMap[KeyEvent.DOM_VK_F21] =           0x01000044;
    keyTranslationMap[KeyEvent.DOM_VK_F22] =           0x01000045;
    keyTranslationMap[KeyEvent.DOM_VK_F23] =           0x01000046;
    keyTranslationMap[KeyEvent.DOM_VK_F24] =           0x01000047;
    keyTranslationMap[KeyEvent.DOM_VK_NUM_LOCK] =      0x01000025;
    keyTranslationMap[KeyEvent.DOM_VK_SCROLL_LOCK] =   0x01000026;
    keyTranslationMap[KeyEvent.DOM_VK_COMMA] =         0x2c;
    keyTranslationMap[KeyEvent.DOM_VK_PERIOD] =        0x2e;
    keyTranslationMap[KeyEvent.DOM_VK_SLASH] =         0x2f;
    keyTranslationMap[KeyEvent.DOM_VK_BACK_QUOTE] =    0x27; // ??
    keyTranslationMap[KeyEvent.DOM_VK_OPEN_BRACKET] =  0x5b;
    keyTranslationMap[KeyEvent.DOM_VK_BACK_SLASH] =    0x5c;
    keyTranslationMap[KeyEvent.DOM_VK_CLOSE_BRACKET] = 0x5d;
    keyTranslationMap[KeyEvent.DOM_VK_QUOTE] =         0x60; // ??
    keyTranslationMap[KeyEvent.DOM_VK_META] =          0x01000022;
}

function getQtKeyCode(code)
{
  if ((code >= 48 && code <= 57) || (code >= 65 && code <= 90)) {
    // digits and letters are identical
    return code;
  } else {
    if (keyTranslationMap.length == 0) {
      initKeyTranslationMap();
    }
    return keyTranslationMap[code];
  }
}

function getQtModifiersCode(evt)
{
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
}

var buttons = 0;

// remember which viewer should get key events (also used for mouse grabbing)
var currentTarget = null;

// the target the mouse is currently over
var mouseTarget = null;

function relMouseCoords(event, target)
{
  var totalOffsetX = 0;
  var totalOffsetY = 0;
  var currentElement = target

  do{
      totalOffsetX += currentElement.offsetLeft;
      totalOffsetY += currentElement.offsetTop;
  }
  while(currentElement = currentElement.offsetParent)

  var canvasX = event.pageX - totalOffsetX;
  var canvasY = event.pageY - totalOffsetY;

  return {x:canvasX, y:canvasY}
}

function handleEvent(evt, target, type)
{
  if (typeof type == "undefined") {
    type = evt.type;
  }

  //showStatus(type, evt);
  
  var slaveID = target.getAttribute("mevis:slaveID");
  if (slaveID) {
    var baseField = target.id;
    var msg = ["1022", baseField, "1", slaveID]
    if (type == "keydown" || type == "keyup") {
      qtCode = getQtKeyCode(evt.keyCode);
      if (typeof qtCode == "undefined") {
        // unsupported key code
        return;
      }
      msg.push(type == "keydown" ? 6 : 7)
      msg.push(qtCode);
      msg.push(getQtModifiersCode(evt));
      msg.push("");  // text generated by pressed key
      msg.push("false");  // auto-repeat?
      msg.push(1);  // number of keys involved in this event
    } else if (type == "mouseover") {
      currentTarget = target
      msg.push(10);
    } else if (type == "mouseout") {
      currentTarget = null
      msg.push(11)
    } else {
      var buttonCode = 0;
      if (type == "mousedown") {
        msg.push(2)
        buttonCode = getQtButtonCode(evt.button);
        buttons |= buttonCode;
      } else if (type == "mouseup") {
        msg.push(3)
        buttonCode = getQtButtonCode(evt.button);
        buttons &= ~buttonCode;
      } else if (type == "mousemove") {
        msg.push(5)
      }
      evt.preventDefault()
     
      var result = relMouseCoords(evt, target)
      msg.push(result.x);
      msg.push(result.y);
      msg.push(buttonCode);
      msg.push(buttons);
      msg.push(getQtModifiersCode(evt));
    }
    mevislabWS.send(msg.join("\n") + "\n");
    if (is_verbose || is_verbose_events) { console.log("SEND " + msg.join(" , ")) }
    
    if (type == "mouseup" && buttons == 0 && mouseTarget != currentTarget) {
      // mouse was released outside of canvas, we must send the Leave event now:
      handleEvent(evt, currentTarget, "mouseout");
      if (mouseTarget) {
        // we are over another viewer now, we must send an Enter and a MouseMove event, but to the new viewer
        handleEvent(evt, mouseTarget, "mouseover");
        handleEvent(evt, mouseTarget, "mousemove");
      }
    }
  }
  return false;
}

function handleMouseEvent(evt)
{
  return handleEvent(evt, evt.target)
}

function handleLocalMouseEvent(evt)
{
  var target = evt.target
  if (buttons == 0) {
    handleEvent(evt, target);
  }
  if (evt.type == "mouseover") {
    mouseTarget = target;
  } else if (evt.type == "mouseout") {
    mouseTarget = null;
  }
}

function handleGlobalMouseEvent(evt)
{
  if (buttons != 0) {
    handleEvent(evt, currentTarget);
  }
}

function handleKeyEvent(evt)
{
  if (currentTarget) {
    return handleEvent(evt, currentTarget)
  } else {
    return true;
  }
}

function handleChangeEvent(evt)
{
  var fieldName = evt.target.id
  var fieldValue = evt.target.value
  var options = "0"
  var msg = ["103", "0", "1", fieldName, fieldValue, options]
  mevislabWS.send(msg.join("\n") + "\n");
  return false;
}

function dummyHandler(event)
{
  return false;
}

window.onkeydown = handleKeyEvent;
window.onkeyup = handleKeyEvent;

//===========================================================================

function fieldUpdate(data)
{
  // remove message type
  data.shift()
  // remove message status
  data.shift()
  // get number of field updates
  var n = Number(data.shift())
  for (var i=0;i<n;i++) {
    var fieldName = data.shift()
    var fieldValue = data.shift()
    var options = data.shift()
    var formField = document.getElementById(fieldName)
    if (formField && formField.tagName == "INPUT") {
      formField.value = fieldValue
    }
  }
}

function sendTestMessages()
{
  var target = document.getElementById("mainScene")
  handleEvent({type:"mouseover",button:0, pageX:100, pageY:200, target:target}, target)
  mouseEvent = {type:"mousedown",button:0, pageX:100, pageY:200, target:target} 
  handleEvent(mouseEvent , target)
  mouseEvent = {type:"mousemove",button:0, pageX:180, pageY:280, target:target} 
  handleEvent(mouseEvent , target)
  mouseEvent.type = "mouseup"
  handleEvent(mouseEvent, target)
  handleEvent({type:"mouseout", target:target}, target)
}

var mouseEvent

function touchStart(event) {
  event.preventDefault();

  //pos = relMouseCoords(event.touches[0])
  //document.getElementById("status").innerHTML = "touch start " + pos.x + " " + pos.y; 

  var target = event.touches[0].target
  var touch = event.touches[0]
  handleEvent({type:"mouseover",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target}, target)
  
  mouseEvent = {type:"mousedown",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target} 
  handleEvent(mouseEvent , target)
}

function touchMove(event) {
  event.preventDefault();

//  pos = relMouseCoords(event.touches[0])
//  document.getElementById("status").innerHTML = "touch move " + pos.x + " " + pos.y; 

  var target = event.touches[0].target
  var touch = event.touches[0]
  mouseEvent = {type:"mousemove",button:0, pageX:touch.pageX, pageY:touch.pageY, target:target} 
  handleEvent(mouseEvent , target)
}

function touchEnd(event) {
  event.preventDefault();

  mouseEvent.type = "mouseup"
  handleEvent(mouseEvent, mouseEvent.target)

  handleEvent({type:"mouseout", target:mouseEvent.target}, mouseEvent.target)
}

function touchCancel(event) {
  event.preventDefault();
//  document.getElementById("status").innerHTML = "touch cancel"; 
}

function baseUpdate(baseField, baseType, baseGeneration)
{
  if(baseType == "RemoteRendering") {
    // see if we have an image element with this field name
    var img = document.getElementById(baseField)
    if (img && img.tagName == "IMG") {
      // add this as a client (MsgSlaveAdded)
      var slaveID = 1; // it is ok to have a 1:1 relation here
      if (is_IOS) {
        img.addEventListener("touchstart",  touchStart,  false);
        img.addEventListener("touchmove",   touchMove,   false);
        img.addEventListener("touchend",    touchEnd,    false);
        img.addEventListener("touchcancel", touchCancel, false);
      } else {
        // install event handlers:
        img.addEventListener("mousedown", handleLocalMouseEvent, true);
        // img.addEventListener("mouseup",   handleLocalMouseEvent, false);
        img.addEventListener("mousemove", handleLocalMouseEvent, false);
        img.addEventListener("mouseover", handleLocalMouseEvent, false);
        img.addEventListener("mouseout",  handleLocalMouseEvent, false);
        // img.onkeydown=handleKeyEvent;
        // img.onkeyup=handleKeyEvent;
        img.ondragstart=dummyHandler;
        img.oncontextmenu=dummyHandler;
      }
      // mark image as viewer:
      img.setAttribute("mevis:slaveID", slaveID);
      mevislabWS.send("1020\n" + baseField + "\n" + baseGeneration + "\n" + slaveID + "\n");
      // send the render size we require:
      mevislabWS.send("1023\n" + baseField + "\n" + baseGeneration + "\n" + slaveID + "\n" +
                      img.width + "\n" + img.height + "\n");

      if (!useStreaming) {
        // request the initial image
        requestImageUpdate(img, baseGeneration, false)
      } else {
        // start streaming:
        mevislabWS.send("1030\n" + baseField + "\n" + baseGeneration + "\n" + slaveID + "\n");
      }
    }
  }
}

function requestImageUpdate(img, baseGeneration, highQuality)
{
  var slaveID = 1; // it is ok to have a 1:1 relation here
  
  img.setAttribute("mevis:updatePending", "1");
  var msg = "1024\n" + img.id + "\n" + baseGeneration + "\n" + slaveID + "\n" +
                  highQuality + "\n"
  mevislabWS.send(msg);
  if (is_verbose) { console.log("SEND " + msg); }
} 

function remoteSceneChanged(baseField, baseGeneration)
{
  if (!useStreaming) {
    // see if we have an image element with this field name
    var img = document.getElementById(baseField)
    if (img && img.tagName == "IMG") {
      // request a new image (currently in low quality only)
      if (img.getAttribute("mevis:updatePending")) {
        // request updated image delayed
        img.setAttribute("mevis:sceneChangedAgain", "1");
      } else {
        requestImageUpdate(img, baseGeneration, false);
      }
    }
  }
}

function remoteImageReceived(baseField, baseGeneration, slaveID, fullQuality, imageData)
{
  // see if we have an image element with this field name
  var img = document.getElementById(baseField)
  if (img && img.tagName == "IMG") {
    // clear old timer if it exists
    if (!useStreaming) {
      if (img.getAttribute("mevis:highQualityTimer")) {
        var oldTimerId = Number(img.getAttribute("mevis:highQualityTimer"));
        window.clearTimeout(oldTimerId);
        img.removeAttribute("mevis:highQualityTimer");
      }

      if (img.getAttribute("mevis:sceneChangedAgain")) {
        // scene has changed again in the meantime, request updated image
        img.removeAttribute("mevis:sceneChangedAgain");
        var msg = "1024\n" + baseField + "\n" + baseGeneration + "\n" + slaveID + "\n" +
                        "false\n"
        mevislabWS.send(msg);
        if (is_verbose) { console.log("SEND " + msg) }
      } else {
        // we may request an updated image directly now
        img.removeAttribute("mevis:updatePending");
                 
        if (!isTrue(fullQuality)) {
          // create new timer to request high quality image:
          var timerId = window.setTimeout(function (){ requestImageUpdate(img, baseGeneration, true)},500);
          img.setAttribute("mevis:highQualityTimer", timerId);
        }
      }
    }

    if (useStreaming) {
      // send acknowledgment
      mevislabWS.send("1029\n" + baseField + "\n" + baseGeneration + "\n" + slaveID + "\n");
    }
    
    // It is faster to set the image after the new request has been sent above.
    var mimeType = (fullQuality ? "image/png" : "image/jpeg");
    // set image data
    img.src = "data:" + mimeType + ";base64," + imageData;
  }
}

var cursorShapes = {};

function remoteCursorReceived(data)
{
  // see if we have an image element with this field name
  var baseField = data[1]
  var baseGeneration = data[2]
  var slaveID = data[3]
  
  var img = document.getElementById(baseField)
  if (img && img.tagName == "IMG") {
    shapeID = data[4]
    var cursorStyle = ""
    hasQCursor = isTrue(data[5]);
    if (hasQCursor) {
      // use cursor shape provided in message
      shape = Number(data[6])
      switch (shape) {
      case  0: cursorStyle = "default";     break;
      case  1: cursorStyle = "n-resize";    break;
      case  2: cursorStyle = "crosshair";   break;
      case  3: cursorStyle = "wait";        break;
      case  4: cursorStyle = "text";        break;
      case  5: cursorStyle = "ns-resize";   break;
      case  6: cursorStyle = "ew-resize";   break;
      case  7: cursorStyle = "nesw-resize"; break;
      case  8: cursorStyle = "nwse-resize"; break;
      case  9: cursorStyle = "move";        break;
      case 10: cursorStyle = "none";        break;
      case 11: cursorStyle = "row-resize";  break;
      case 12: cursorStyle = "col-resize";  break;
      case 13: cursorStyle = "pointer";     break;
      case 14: cursorStyle = "not-allowed"; break;
      case 15: cursorStyle = "help";        break;
      case 16: cursorStyle = "wait";        break;
      case 17: cursorStyle = "cell";        break; // no direct match  // better: -moz-grab
      case 18: cursorStyle = "all-scroll";  break; // no direct match  // better: -moz-grabbing
      case 24:
        // bitmap cursor, construct cursor style with data url:
        cursorStyle = "url(data:image/png;base64," + data[9] + ") " + data[7] + " " + data[8] + ", default";
      }
      if (cursorStyle.length > 0) {
        // remember cursor shape
        cursorShapes[shapeID] = cursorStyle
      }
    } else {
      // use remembered cursor style
      cursorStyle = cursorShapes[shapeID]
    }
    
    if (cursorStyle) {
      // set cursor style on tag
      img.style.cursor = cursorStyle
    }
  }
}

//===========================================================================

function connectedToServer()
{
  console.log("<Connected>");
  mevislabWS.send("101\n" + _remoteModule + "\n");
}

function connectionError(evt)
{
  console.log("<Error in WebSocket communcation: " + evt + ">");
}

function messageReceived(evt)
{
  var received_msg = evt.data;
  var msgFragments = received_msg.split("\n");
  var msgType = msgFragments[0]
  switch(msgType) {
  case "103":
    fieldUpdate(msgFragments.slice());
    break;
  case "108":
    // Base field got a new object
    baseUpdate(msgFragments[1], msgFragments[2], msgFragments[3]);
    break;
  case "1025":
    // remote rendering needs update
    remoteSceneChanged(msgFragments[1], msgFragments[2]);
    break;
  case "1026":
    if (is_verbose) { console.log("RECEIVE image") }
    remoteImageReceived(msgFragments[1], msgFragments[2], msgFragments[3], msgFragments[4], msgFragments[5]);
    // don't show message
    return;
    break;
  case "1027":
    if (is_verbose) { console.log("RECEIVE cursor") }
    // remote rendering needs update
    remoteCursorReceived(msgFragments);
    // don't show message
    return;
    break;
  }
  if (is_verbose) { console.log("RECEIVE " + msgFragments.join(" ")); }
}

function connectionClosed()
{
  console.log("<Connection closed>");
}

//===========================================================================

function parsePageArguments() {
      var tmp = window.location.href.split('?');
      tmp = tmp.splice(1, tmp.length-1);
      tmp = tmp.join('?').split('&');
      var args = new Object();
      for (var i=0; i<tmp.length; i++) {
        var items = tmp[i].split('=');
        if (items.length > 1) {
          args[items[0]] = unescape(items.splice(1, items.length-1).join('='));
        } else {
          args[tmp[i]] = '1';
        }
      }
      return args;
}
    
function ConnectToMeVisLab(module)
{
  _remoteModule = module
  
  var args = parsePageArguments();
  if ("streaming" in args) {
    useStreaming = args["streaming"]!=1
  }
  console.log("streaming: " + useStreaming);
  
  window.addEventListener("mousedown", handleGlobalMouseEvent, true);
  window.addEventListener("mousemove", handleGlobalMouseEvent, false);
  window.addEventListener("mouseup",   handleGlobalMouseEvent, false);
  
  is_IE9 = getInternetExplorerVersion()>=9
  // check of IOS devices
  is_IOS = (/iphone|ipad|ipod/i.test(navigator.userAgent.toLowerCase()));  
    
  if ("WebSocket" in window || "MozWebSocket" in window)
  {
    var hostname = window.location.hostname;
    var socketUri = "ws://127.0.0.1:4114/mevislab";
    if (hostname) {
        socketUri = "ws://" + hostname + ":4114/mevislab";
    }
    console.log("<Connecting to " + socketUri + ">");
    if ("MozWebSocket" in window) {
        // Firefox 6.0 uses a prefixed name:
        mevislabWS = new MozWebSocket(socketUri);
    } else {
        mevislabWS = new WebSocket(socketUri);
    }
    mevislabWS.onopen = connectedToServer;
    mevislabWS.onmessage = messageReceived;
    mevislabWS.onclose = connectionClosed;
    mevislabWS.onerror = connectionError;
  }
  else
  {
    alert("WebSockets nor Flash emulation supported here!\n\nBrowser: " + navigator.appName + " " +
          navigator.appVersion);
  }
}

function DisconnectFromMeVisLab()
{
  mevislabWS.close();
}

//===========================================================================

