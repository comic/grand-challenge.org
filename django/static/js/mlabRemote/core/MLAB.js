//=============================================================================
// MLAB
//=============================================================================
var MLAB = (new function(){
  var self = this;
  
  this.log = function(message) { app.log(message); };
  this.logError = function(message) { app.logError(message); };
  this.logException = function(message) { app.logException(message); };
  
  this.getMDLChild = function(tree, childName) {
    if (tree.children) {
      for (var i=0; i<tree.children.length; i++) {
        var c = tree.children[i];
        if (c.name == childName) {
          return c;
        }
      }
    }
    return null;
  };
}());
