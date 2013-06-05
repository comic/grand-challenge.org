/** \class MLAB.Core.RemoteCallInterfaceHandler(MLAB.Core.BaseFieldHandlerBase)
 * 
 */
MLAB.Core.deriveClass("RemoteCallInterfaceHandler", MLAB.Core.BaseFieldHandlerBase, {
  RemoteCallInterfaceHandler: function (baseField) {
    MLAB.Core.RemoteCallInterfaceHandler.super.constructor.call(this, baseField)
  },
  
  handleMessage: function(message) {
    switch (message.type) {
    case MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE:
      break
    case MLAB.Core.MSG_GENERIC_BASE_REQUEST:
      var module = this._baseField.getFieldOwner()
      if (message.method.indexOf("::") === 0) {
        var tmp = message.method.slice(2).split(".")
        var obj = window
        for (var i=0; i<tmp.length; i++) {
          obj = obj[tmp[i]]
          if (typeof(obj) === "undefined") {
            break
          }
        }
        var method = obj
      } else {
        var method = module[message.method]
      }
      if (typeof(method) === "undefined") {
        module.logError("MLAB.Core.RemoteCallInterfaceHandler: no such method found: " + message.method)
      } else {
        try {
          if (message.requestId > 0) {
            var result = method.apply(module, message.arguments)
            var data = {result: result, requestId: message.requestId}
            this.sendBaseFieldMessage(MLAB.Core.GenericBaseReplyMessage, data)
          } else {
            method.apply(module, message.arguments)
          }
        } catch (e) {
          module.logException(e)
        }
      }
      break
    case MLAB.Core.MSG_GENERIC_BASE_REPLY:
      break
    }
  }
})

MLAB.Core.BaseFieldHandlerFactory.registerHandler("RemoteCallInterface", MLAB.Core.RemoteCallInterfaceHandler)
