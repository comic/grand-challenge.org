/** \class MLAB.Core.ItemModelItem
 * 
 */
MLAB.Core.defineClass("ItemModelItem", {
  ItemModelItem: function(theModel, parent) {
    this._model = theModel
    this._parent = parent
    this._hasChildren = true  // the root item always can have children
    this._id = this._model._nextItemID++
  
    // automatically add item to map of ids to items
    this._model._idToItem[this._id] = this
  },
  
  getModel: function() {
    return this._model
  },
  
  getID: function() {
    return this._id
  },
  
  getAttribute: function(attrName) {
    if (attrName in this._values) {
      return this._values[attrName]
    } else {
      // if value wasn't defined in this item fall back to default:
      return this._model._attributes[attrName]
    }
  },
  
  setAttribute: function(attrName, value) {
    if (!(attrName in this._model._attributes)) {
      // value not in model
      return false
    } else if (value === this.getAttribute(attrName)) {
      // unchanged
      return true
    } else {
      this._values[attrName] = value
      return this._model._valueChanged(this, attrName)
    }
  },
  
  hasChildren: function() {
    return this._hasChildren
  },
  
  getChildCount: function() {
    if (!("_children" in this)) {
      // advise master to send children data
      this._model._requestChildren(this._id)
      this._children = []
    }
    return this._children.length
  },
  
  getChild: function(index) {
    return this._children[index]
  },
  
  getParent: function() {
    return this._parent
  },
  
  isRoot: function() {
    return !(this._parent)
  },
  
  // remove all children of this item
  _removeChildren: function() {
    if ("_children" in this) {
      for (var i=0;i<this._children.length;i++) {
        this._children[i]._remove()
      }
      delete this._children
    }
  },

  // remove this item
  _remove: function() {
    this._removeChildren()
    // remove the id from the mapping
    delete this._model._idToItem[this._id]
  }
})

/** MLAB.Core.ItemModelHandler(MLAB.Core.BaseFieldHandlerBase)
 * 
 */
MLAB.Core.deriveClass("ItemModelHandler", MLAB.Core.BaseFieldHandlerBase, {
  ItemModelHandler: function (baseField) {
    MLAB.Core.ItemModelHandler.super.constructor.call(this, baseField)
    // mapping from ids to items
    this._idToItem = new Object()
    
    // item IDs are given consecutively to received items
    this._nextItemID = 0
    
    // this will be set by the attribute message
    this._isFlat = false
    
    // generate new item in item model:
    
    // default attributes
    this._attributes = new Object()
    
    // create root item
    this._rootItem = new MLAB.Core.ItemModelItem(this, null)
    
    // listeners get notified when items get inserted/removed/changed:
    this._listeners = new Array()
  },
  
  // get root item
  getRootItem: function() {
    return this._rootItem
  },
  
  isFlat: function() {
    return this._isFlat
  },
  
  addListener: function(listener) {
    if (listener) {
      this._listeners.push(listener)
    } else {
      MLAB.Core.throwException("MLAB.Core.ItemModelHandler.addListener: no field listener given")
    }
  },

  removeListener: function(listener) {
    if (listener) {
      var i = this._listeners.indexOf(listener)
      this._listeners.splice(i, 1)
    } else {
      MLAB.Core.throwException("MLAB.Core.ItemModelHandler.removeListener: no field listener given")
    }
  },
  
  // I think there is no good way to get the number of defined attributes, but I also think
  // that we don't need this here...
  
  // is attribute defined for this model
  hasAttribute: function(attrName) {
    return (attrName in this._attributes)
  },
  
  getAttributeDefault: function(attrName) {
    return this._attributes[attrName]
  },
  
  getItemForID: function(id) {
    return this._idToItem[id]
  },
  
  // handle local change of attribute
  _valueChanged: function(item, attrName) {
    // this might notify the instance that changed the value itself...
    this._fireDataChanged([item], [attrName])
    // pass information on to server
    this.sendBaseFieldMessage(MLAB.Core.ItemModelDataChanged, {attributeNames: [attrName], 
                                                         itemIDs: [item.getID()],
                                                         values: [item.getAttribute(attrName)]})
  },
  
  // send requestChildren message to master
  _requestChildren: function(parentItemID) {
    this.sendBaseFieldMessage(MLAB.Core.ItemModelGetChildrenMessage, {itemID: parentItemID})
  },
  
  // message multiplexer:
  handleMessage: function(msg) {
    switch (msg.type) {
      case MLAB.Core.MSG_ITEM_MODEL_ATTRIBUTES:
        this._handleAttributesMessage(msg)
        break
      case MLAB.Core.MSG_ITEM_MODEL_ITEM_CHANGED:
        this._handleItemChangedMessage(msg)
        break
      case MLAB.Core.MSG_ITEM_MODEL_ITEMS_INSERTED:
        this._handleItemsInsertedMessage(msg)
        break
      case MLAB.Core.MSG_ITEM_MODEL_ITEMS_REMOVED:
        this._handleItemsRemovedMessage(msg)
        break
      case MLAB.Core.MSG_ITEM_MODEL_DATA_CHANGED:
        this._handleDataChangedMessage(msg)
        break
      case MLAB.Core.MSG_ITEM_MODEL_CHILDREN_DONE:
        // currently not used
        break
      case MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE:
        break
        
      default:
        MLAB.Core.throwException("MLAB.Core.ItemModelHandler.handleMessage: unhandled message type: " + msg.type)
    }
  },
  
  // handle the different message types
  _handleAttributesMessage: function(msg) {
    for (var i=0;i<msg.attributes.length;i++) {
      var entry = msg.attributes[i]
      this._attributes[entry[0]] = entry[1]
    }
    this._isFlat = !msg.hasChildren
    // all basic information is there, set this handler as the new value of the Base field
    // TODO: what does this? isn't a touch() on the field enough? the handler is not the base object ...
    this._baseField.updateValue(this)
  },

  _handleItemChangedMessage: function(msg) {
    var item = this._idToItem[msg.itemID]
    if (item) {
      this._fireItemChanged(item, true)
      item._removeChildren()
      item._hasChildren = msg.hasChildren
      this._fireItemChanged(item, false)
    }
  },

  _handleItemsInsertedMessage: function(msg) {
    var parentItem = this._idToItem[msg.parentItemID]
    var itemCount = msg.items.length
    if (parentItem) {
      this._fireItemsInserted(parentItem, msg.position, itemCount, true)
      // if _children property doesn't exist yet, create it:
      if (!("_children" in parentItem)) {
        parentItem._children = new Array()
      }
      // insert children:
      for (var i=0;i<itemCount;i++) {
        var itemData = msg.items[i]
        var item = new MLAB.Core.ItemModelItem(this, parentItem)
        item._values = itemData.data
        item._hasChildren = itemData.hasChildren
        parentItem._children.splice(msg.position+i, 0, item)
      }
      this._fireItemsInserted(parentItem, msg.position, itemCount, false)
    }
  },

  _handleItemsRemovedMessage: function(msg) {
    var parentItem = this._idToItem[msg.parentItemID]
    if (parentItem && ("_children" in parentItem)) {
      this._fireItemsRemoved(parentItem, msg.position, msg.itemCount, true)
      for (var i=0;i<msg.itemCount;i++) {
        parentItem._children[msg.position+i]._remove()
      }
      parentItem._children.splice(msg.position, msg.itemCount)
      this._fireItemsRemoved(parentItem, msg.position, msg.itemCount, false)
    }
  },

  _handleDataChangedMessage: function(msg) {
    var items = []
    var attributes = msg.attributeNames
    for (var i=0;i<msg.itemIDs.length;i++) {
      var item = this._idToItem[msg.itemIDs[i]]
      for (var j=0;j<attributes.length;j++) {
        item._values[attributes[j]] = msg.values[i*attributes.length + j]
      }
      items.push(item)
    }
    this._fireDataChanged(items, attributes)
  },

  // notify listeners:
  _fireItemChanged: function(item, before) {
    for (var i=0;i<this._listeners.length;i++) {
      this._listeners[i].itemChanged(item, before)
    }
  },
  
  _fireItemsInserted: function(parentItem, at, amount, before) {
    for (var i=0;i<this._listeners.length;i++) {
      this._listeners[i].itemsInserted(parentItem, at, amount, before)
    }
  },
  
  _fireItemsRemoved: function(parentItem, at, amount, before) {
    for (var i=0;i<this._listeners.length;i++) {
      this._listeners[i].itemsRemoved(parentItem, at, amount, before)
    }
  },
  
  _fireDataChanged: function(items, attributes) {
    for (var i=0;i<this._listeners.length;i++) {
      this._listeners[i].dataChanged(items, attributes)
    }
  }
  
})

MLAB.Core.BaseFieldHandlerFactory.registerHandler("AbstractItemModel", MLAB.Core.ItemModelHandler)
