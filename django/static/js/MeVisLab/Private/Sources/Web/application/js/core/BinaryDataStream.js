;(function() {
  this.QtType_Void = 0
  this.QtType_Bool = 1
  this.QtType_Int = 2
  this.QtType_UInt = 3
  this.QtType_LongLong = 4
  this.QtType_ULongLong = 5
  this.QtType_Double = 6
  this.QtType_QChar = 7
  this.QtType_QVariantMap = 8
  this.QtType_QVariantList = 9
  this.QtType_QString = 10
  this.QtType_QStringList = 11
  this.QtType_QByteArray = 12
  this.QtType_QBitArray = 13
  this.QtType_QDate = 14
  this.QtType_QTime = 15
  this.QtType_QDateTime = 16
  this.QtType_QUrl = 17
  this.QtType_QLocale = 18
  this.QtType_QRect = 19
  this.QtType_QRectF = 20
  this.QtType_QSize = 21
  this.QtType_QSizeF = 22
  this.QtType_QLine = 23
  this.QtType_QLineF = 24
  this.QtType_QPoint = 25
  this.QtType_QPointF = 26
  this.QtType_QRegExp = 27
  this.QtType_QVariantHash = 28
  this.QtType_QPixmap = 65
  this.QtType_QBrush = 66
  this.QtType_QColor = 67
  this.QtType_QPalette = 68
  this.QtType_QIcon = 69
  this.QtType_QImage = 70
  this.QtType_QPolygon = 71
  this.QtType_QRegion = 72
  this.QtType_QBitmap = 73
  this.QtType_QCursor = 74
  this.QtType_QSizePolicy = 75
  this.QtType_QKeySequence = 76
  this.QtType_QPen = 77
  this.QtType_QTextLength = 78
  this.QtType_QTextFormat = 79
  this.QtType_QMatrix = 80
  this.QtType_QTransform = 81
  this.QtType_QMatrix4x4 = 82
  this.QtType_QVector2D = 83
  this.QtType_QVector3D = 84
  this.QtType_QVector4D = 85
  this.QtType_QQuaternion = 86
  this.QtType_Short = 130
  this.QtType_Char = 131
  this.QtType_ULong = 132
  this.QtType_UShort = 133
  this.QtType_UChar = 134
  this.QtType_Float = 135
}).apply(MLAB.Core)

// This class currently only supports reading.
// Writing is somewhat complicated, since the size of the underlying
// ArrayBuffer needs to be set in advance. So either you know the
// needed buffer size in advance, make the buffer very big or you need
// to resize the buffer when it is too small (if this is even possible).
MLAB.Core.defineClass("BinaryDataStream", {

  BinaryDataStream: function(arraybuffer) {
    this._buffer = arraybuffer
    this._offset = 0
    this._view = new DataView(arraybuffer)
  },

  getPosition: function() {
    return this._offset
  },
  
  setPosition: function(pos) {
    this._offset = pos
  },
  
  atEnd: function() {
    return (this._offset >= this._buffer.length)
  },
  
  readBool: function() {
    var result = (this._view.getUint8(this._offset) != 0)
    this._offset += 1
    return result
  },
  
  readByte: function() {
    var result = this._view.getUint8(this._offset)
    this._offset += 1
    return result
  },

  readInt16: function() {
    var result = this._view.getInt16(this._offset)
    this._offset += 2
    return result
  },

  readUInt16: function() {
    var result = this._view.getUint16(this._offset)
    this._offset += 2
    return result
  },

  readInt32: function() {
    var result = this._view.getInt32(this._offset)
    this._offset += 4
    return result
  },

  readUInt32: function() {
    var result = this._view.getUint32(this._offset)
    this._offset += 4
    return result
  },

  readInt64: function() {
    var high = this.readInt32()
    var low  = this.readUInt32()
    return (high << 32) + low
  },

  readUInt64: function() {
    var high = this.readUInt32()
    var low  = this.readUInt32()
    return (high << 32) + low
  },

  readFloat: function() {
    var result = this._view.getFloat32(this._offset)
    this._offset += 4
    return result
  },

  readDouble: function() {
    var result = this._view.getFloat64(this._offset)
    this._offset += 8
    return result
  },

  readString: function() {
    var len = this.readInt32()
    if (len < 0)
    {
      return null;
    }
    else if (len === 0)
    {
      return "";
    }

    len = len / 2;
    var result = ""
    for (var i = 0; i < len; i++) {
      result = result + String.fromCharCode(this.readUInt16())
    }
    return result
  },

  readStringList: function() {
    var len = this.readInt32()
    var result = new Array()
    for (var i = 0; i < len; i++)
    {
      result.push(this.readString())
    }
    return result
  },

  readByteArray: function() {
    var len = this.readUInt32()
    if (len === 0xffffffff)
    {
      return null
    }
    else
    {
      var buffer = new Uint8Array(this._buffer, this._offset, len)
      this._offset += len
      return buffer
    }
  },

  readStringFromByteArray: function() {
    var data = this.readByteArray()
    if (data === null)
    {
      return null
    }
    else
    {
      var result = ""
      for (var i = 0; i < data.length; i++) {
        result += String.fromCharCode(data[i])
      }
      return result
    }
  },

  readVariantList: function() {
    var len = this.readUInt32();
    var result = new Array()
    for (var i = 0; i < len; i++)
    {
      result.push(this.readVariant())
    }
    return result
  },

  readVariantMap: function() {
    var len = this.readUInt32();
    var result = {}
    for (var i = 0; i < len; i++)
    {
      var key = this.readString()
      var value = this.readVariant()
      result[key] = value
    }
    return result;
  },

  readVariant: function() {
    var type = this.readUInt32();
    var nullFlag = this.readByte();
    var result = null;
    switch (type)
    {
      case MLAB.Core.QtType_Bool:
        result = this.readBool();
        break;
      case MLAB.Core.QtType_Int:
        result = this.readInt32();
        break;
      case MLAB.Core.QtType_UInt:
        result = this.readUInt32();
        break;
      case MLAB.Core.QtType_LongLong:
        result = this.readInt64();
        break;
      case MLAB.Core.QtType_ULongLong:
        result = this.readUInt64();
        break;
      case MLAB.Core.QtType_Double:
        result = this.readDouble();
        break;
      case MLAB.Core.QtType_Float:
        result = this.readFloat();
        break;
      case MLAB.Core.QtType_QVariantMap:
        result = this.readVariantMap();
        break;
      case MLAB.Core.QtType_QVariantList:
        result = this.readVariantList();
        break;
      case MLAB.Core.QtType_QString:
        result = this.readString();
        break;
      case MLAB.Core.QtType_QStringList:
        result = this.readStringList();
        break;
      case MLAB.Core.QtType_QByteArray:
        result = this.readStringFromByteArray();
        break;
      case MLAB.Core.QtType_Void:
        // Qt writes an empty string here, so we read it...
        this.readString();
        break;
      //TODO... more types
      default:
        MLAB.Core.throwException("Unhandled Qt type code: " + type);
        break;
    }

    return result;
  },

})