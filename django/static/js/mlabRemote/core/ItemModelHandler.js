//=============================================================================
// MLABItemModelItem
//=============================================================================

function MLABItemModelItem(theModel, parent) {
  var model = theModel;
  var self = this;

  this._parent = parent;
  this._hasChildren = true;  // the root item always can have children
  this._id = model._nextItemID++;
  
  // automatically add item to map of ids to items
  model._idToItem[this._id] = this;
  
  this.getModel = function() {
    return model;
  }
  
  this.getID = function() {
    return self._id;
  }
  
  this.getAttribute = function(attrName) {
    if (attrName in self._values) {
      return self._values[attrName];
    } else {
      // if value wasn't defined in this item fall back to default:
      return model._attributes[attrName];
    }
  }
  
  this.setAttribute = function(attrName, value) {
    if (!(attrName in model._attributes)) {
      // value not in model
      return false;
    } else if (value === self.getAttribute(attrName)) {
      // unchanged
      return true;
    } else {
      self._values[attrName] = value;
      return model._valueChanged(self, attrName);
    }
  }
  
  this.hasChildren = function() {
    return self._hasChildren;
  }
  
  this.getChildCount = function() {
    if (!("_children" in self)) {
      // advise master to send children data
      model._requestChildren(self._id);
      self._children = [];
    }
    return self._children.length;
  }
  
  this.getChild = function(index) {
    return self._children[index];
  }
  
  this.getParent = function() {
    return self._parent;
  }
  
  this.isRoot = function() {
    return !(self._parent);
  }
  
  // remove all children of this item
  this._removeChildren = function() {
    if ("_children" in self) {
      for (var i=0;i<self._children.length;i++) {
        self._children[i]._remove();
      }
      delete self._children;
    }
  }

  // remove this item
  this._remove = function() {
    self._removeChildren()
    // remove the id from the mapping
    delete model._idToItem[self.__id];
  }
}

//=============================================================================
// MLABItemModelHandler
//=============================================================================
function MLABItemModelHandler(field, generationID) {
  var self = this;
  
  // we need a reference to our field (and module context) so we can send messages back
  this._field = field;
  
  // the generation ID is needed for messages to the master
  this._generationID = generationID;
  
  // mapping from ids to items
  this._idToItem = new Object();
  
  // item IDs are given consecutively to received items
  this._nextItemID = 0;
  
  // this will be set by the attribute message
  this._isFlat = false;
  
  // generate new item in item model:
  
  // default attributes
  this._attributes = new Object();
  
  // create root item
  this._rootItem = new MLABItemModelItem(this, null);
  
  // get root item
  this.getRootItem = function() {
    return self._rootItem;
  }
  
  this.isFlat = function() {
    return self._isFlat
  }
  
  // listeners get notified when items get inserted/removed/changed:
  this._listeners = new Array();
  
  this.addListener = function(listener) {
    if (listener) {
      self._listeners.push(listener);
    } else {
      mlabThrowException("MLABItemModelHandler.addListener: no field listener given");
    }
  };

  this.removeListener = function(listener) {
    if (listener) {
      var i = self._listeners.indexOf(listener);
      self._listeners.splice(i, 1);
    } else {
      mlabThrowException("MLABItemModelHandler.removeListener: no field listener given");
    }
  };
  
  // I think there is no good way to get the number of defined attributes, but I also think
  // that we don't need this here...
  
  // is attribute defined for this model
  this.hasAttribute = function(attrName) {
    return (attrName in self._attributes);
  }
  
  this.getAttributeDefault = function(attrName) {
    return self._attributes[attrName];
  }
  
  this.getItemForID = function(id) {
    return self._idToItem[id];
  }
  
  // handle local change of attribute
  this._valueChanged = function(item, attrName) {
    // this might notify the instance that changed the value itself...
    self._fireDataChanged([item], [attrName]);
    // pass information on to server
    var message = new MLABItemModelDataChanged();
    message.setData(self._field._name, self._generationID,
      [attrName], [item.getID()], [item.getAttribute(attrName)]);
    self._field._moduleContext._remoteManager.sendMessage(message);
  }
  
  // send requestChildren message to master
  this._requestChildren = function(parentItemID) {
    var message = new MLABItemModelGetChildrenMessage();
    message.setData(self._field._name, self._generationID, parentItemID);
    self._field._moduleContext._remoteManager.sendMessage(message);
  }
  
  // message multiplexer:
  this.handleMessage = function(msg) {
    switch (msg.type) {
      case MLAB_MSG_ITEM_MODEL_ATTRIBUTES:
        self._handleAttributesMessage(msg);
        break;
      case MLAB_MSG_ITEM_MODEL_ITEM_CHANGED:
        self._handleItemChangedMessage(msg);
        break;
      case MLAB_MSG_ITEM_MODEL_ITEMS_INSERTED:
        self._handleItemsInsertedMessage(msg);
        break;
      case MLAB_MSG_ITEM_MODEL_ITEMS_REMOVED:
        self._handleItemsRemovedMessage(msg);
        break;
      case MLAB_MSG_ITEM_MODEL_DATA_CHANGED:
        self._handleDataChangedMessage(msg);
        break;
        
      default:
        mlabThrowException("MLABItemModelHandler.handleMessage: unhandled message type: " + msg.type);
    }
  }
  
  // handle the different message types
  this._handleAttributesMessage = function(msg) {
    for (var i=0;i<msg.attributes.length;i++) {
      var entry = msg.attributes[i];
      self._attributes[entry[0]] = entry[1];
    }
    self._isFlat = !msg.hasChildren;
    // all basic information is there, set this handler as the new value of the Base field
    self._field.updateValue(self);
  }

  this._handleItemChangedMessage = function(msg) {
    var item = self._idToItem[msg.itemID];
    if (item) {
      self._fireItemChanged(item, true);
      item._removeChildren();
      item._hasChildren = msg.hasChildren;
      self._fireItemChanged(item, false);
    }
  }

  this._handleItemsInsertedMessage = function(msg) {
    var parentItem = self._idToItem[msg.parentItemID];
    var itemCount = msg.items.length;
    if (parentItem) {
      self._fireItemsInserted(parentItem, msg.position, itemCount, true);
      // if _children property doesn't exist yet, create it:
      if (!("_children" in parentItem)) {
        parentItem._children = new Array();
      }
      // insert children:
      for (var i=0;i<itemCount;i++) {
        var itemData = msg.items[i];
        var item = new MLABItemModelItem(self, parentItem);
        item._values = itemData.data;
        item._hasChildren = itemData.hasChildren;
        parentItem._children.splice(msg.position+i, 0, item);
      }
      self._fireItemsInserted(parentItem, msg.position, itemCount, false);
    }
  }

  this._handleItemsRemovedMessage = function(msg) {
    var parentItem = self._idToItem[msg.parentItemID];
    if (parentItem && ("_children" in parentItem)) {
      self._fireItemsRemoved(parentItem, msg.position, msg.itemCount, true);
      for (var i=0;i<msg.itemCount;i++) {
        parentItem._children[msg.position+i]._remove();
      }
      parentItem._children.splice(msg.position, msg.itemCount)
      self._fireItemsRemoved(parentItem, msg.position, msg.itemCount, false);
    }
  }

  this._handleDataChangedMessage = function(msg) {
    var items = [];
    var attributes = msg.attributeNames;
    for (var i=0;i<msg.itemIDs.length;i++) {
      var item = self._idToItem[msg.itemIDs[i]];
      for (var j=0;j<attributes.length;j++) {
        item._values[attributes[j]] = msg.values[i*attributes.length + j];
      }
      items.push(item);
    }
    self._fireDataChanged(items, attributes);
  }

  // notify listeners:
  this._fireItemChanged = function(item, before) {
    for (var i=0;i<self._listeners.length;i++) {
      self._listeners[i].itemChanged(item, before);
    }
  }
  
  this._fireItemsInserted = function(parentItem, at, amount, before) {
    for (var i=0;i<self._listeners.length;i++) {
      self._listeners[i].itemsInserted(parentItem, at, amount, before);
    }
  }
  
  this._fireItemsRemoved = function(parentItem, at, amount, before) {
    for (var i=0;i<self._listeners.length;i++) {
      self._listeners[i].itemsRemoved(parentItem, at, amount, before);
    }
  }
  
  this._fireDataChanged = function(items, attributes) {
    for (var i=0;i<self._listeners.length;i++) {
      self._listeners[i].dataChanged(items, attributes);
    }
  }
  
}
