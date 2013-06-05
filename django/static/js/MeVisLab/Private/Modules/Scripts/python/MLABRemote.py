from mevis import *

class MLABRemoteCallInterfaceHandler:
    def __init__(self):
        pass
  
class MLABRemoteClass:
    def __init__(self):
        self._module = None
        self._remoteCallInterfaceHandler = None
        self._remoteCallInterfaceBaseObject = None
        self._allowedRemoteCalls = ["handleRemoteError",
                                    "handleRemoteInfo",
                                    "handleRemoteMDLRequest",
                                    "handleWidgetControlNamesRequest"]

    def setup(self, module):
        self._module = module
        self._createRPCBaseObject()
        self._setupAllowedRemoteCalls()
  
    def _createRPCBaseObject(self):
        if self._module.hasField("webRemoteCallInterface"):
            rci = MLAB.createMLBaseObject("RemoteCallInterface", [])
            if rci != None:
                self._remoteCallInterfaceHandler = MLABRemoteCallInterfaceHandler()
                rci.addInterfaceObject("WebRemoteCallInterfaceHandler", self._remoteCallInterfaceHandler)
                self._module.field("webRemoteCallInterface").setObject(rci)
                self._remoteCallInterfaceBaseObject = rci
            else:
                MLAB.logError("Failed to create RemoteCallInterface base object")

    def callOnModule(self, method, *args):
        self._callInternal(method, *args)
    
    def callWithResultOnModule(self, callback, method, *args):        
        self._callWithResultInternal(callback, method, *args)
        
    def call(self, method, *args):
        self._callInternal("::" + method, *args)
    
    def callWithResult(self, callback, method, *args):        
        self._callWithResultInternal(callback, "::" + method, *args)
    
    def _callInternal(self, method, *args):
        if self._remoteCallInterfaceBaseObject != None:
            if len(args) <= 10:
                self._remoteCallInterfaceBaseObject.call(method, *args)
            else:
                MLAB.logError("MLABRemote.call(): no more than 10 arguments are supported: " + method +  str(args))
        else:
            MLAB.logError("Module misses the 'webRemoteCallInterface' base field")
    
    def _callWithResultInternal(self, callback, method, *args):        
        if self._remoteCallInterfaceBaseObject != None:
            if len(args) <= 10:
                self._remoteCallInterfaceBaseObject.callWithResult(callback, method, *args)
            else:
                MLAB.logError("MLABRemote.callWithResult(): no more than 10 arguments are supported: " + method +  str(args))
        else:
            MLAB.logError("Module misses the 'webRemoteCallInterface' base field")
    
    def getModule(self):
        return self._module
    
    def _setupAllowedRemoteCalls(self):
        # TODO: do we want to automatically search certain control commands, e.g. ListView 
        # selectionChanged commands, and allow them? That would be convenient for developers.
        commands = self._module.mdlTree().findChild("Commands")
        if not commands:
            commands = self._module.mdlTree().appendChild("Commands", "")
    
    def addAllowedCalls(self, newAllowedCalls):
        tree = self._module.mdlTree()
        commands = tree.findChild("Commands")
        if commands:
            allowedCallsTree = commands.findChild("allowedRemoteCalls")
            if allowedCallsTree:
                l = allowedCallsTree.getValue().split(',')
                for c in l:
                    if not c in self._allowedRemoteCalls:
                        self._allowedRemoteCalls.append(c)
                allowedCallsTree.setValue(','.join(self._allowedRemoteCalls))
                allowedCalls = set(allowedCallsTree.getValue().split(','))
                newAllowedCalls = set(newAllowedCalls).union(allowedCalls)
                allowedCallsTree.setValue(','.join(newAllowedCalls))
            else:
                commands.append("allowedRemoteCalls", ','.join(newAllowedCalls))
                commands.append("allowedRemoteCalls", ','.join(self._allowedRemoteCalls))

# decorator to ease adding remote functions from a MacroModule which has self set to its python object
def remoteInterface(decoratedMethod):
    def decoratedMethodDelegate(*args, **kwargs):
        self = MLABRemote._module.scriptVariable("self")
        return getattr(self, decoratedMethod.__name__)(*args, **kwargs)
    MLABRemote._module.setScriptVariable(decoratedMethod.__name__, decoratedMethodDelegate)
    MLABRemote.addAllowedCalls((decoratedMethod.__name__,))
    return decoratedMethod

MLABRemote = MLABRemoteClass()

def setupRemoteContext(module):
    MLABRemote.setup(module)
    return MLABRemote

def handleRemoteError(message):
    MLAB.logErrorHTML(message)

def handleRemoteInfo(message):
    MLAB.logHTML(message)

def handleRemoteMDLRequest():
    return MLABRemote.getModule().getMDLTreeAsJson()

def handleWidgetControlNamesRequest():
    return MLAB.priv().getKnownWidgetControls()
