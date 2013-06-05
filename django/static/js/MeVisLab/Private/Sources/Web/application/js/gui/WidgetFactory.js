/** \class MLAB.GUI.WidgetFactory
 * 
 */
MLAB.GUI.defineClass("WidgetFactorySingleton", {
  
  _widgetClasses: {},
  
  WidgetFactorySingleton: function() {
  },
  
  _getWidgetClass: function(widgetName) {
    var c = MLAB.GUI.WidgetFactory._widgetClasses[widgetName]
    if (c !== undefined) {
      return c
    }
    return null
  },
  
  registerWidgetClass: function(widgetName, widgetClass, overwrite) {
    if ((this._getWidgetClass(widgetName) === null) || (overwrite === true)) {
      if (typeof(widgetClass) !== "undefined") {
        MLAB.GUI.WidgetFactory._widgetClasses[widgetName] = widgetClass
      } else {
        MLAB.Core.throwException("Attempt to register an undefined object as a widget: " + widgetName)
      }
    } else {
      MLAB.Core.throwException('Failed to register widget class "' + widgetName + '": ' +
                         'another class with the same name was already registered')
    }
  },

  create: function(widgetName, id, arg1, arg2, arg3, arg4, arg5, arg6) {
    var widgetClass = this._getWidgetClass(widgetName)
    if (widgetClass === null) {
      MLAB.Core.throwException("No such widget class registered: " + widgetName)
    }
    var w = new widgetClass(arg1, arg2, arg3, arg4, arg5, arg6)
    if (id) {
      w.setId(id)
    }
    return w
  }
})
  
MLAB.GUI.WidgetFactory = new MLAB.GUI.WidgetFactorySingleton()
