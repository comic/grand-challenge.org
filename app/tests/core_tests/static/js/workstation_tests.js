function handleMessage(event, randomId) {
    const eventString = JSON.stringify(event.data)
    const node = document.createElement("li");
    node.innerHTML = eventString;
    const messages = document.getElementById("messages");
    messages.appendChild(node);

    const msg = {
        sessionControl: {
            meta: {
                acknowledge: {
                    id: `${randomId ? randomId : event.data.sessionControl.meta.id}`
                }
            }
        }
    };
    event.source.postMessage(msg, event.origin);
    const node2 = document.createElement("li");
    node2.innerHTML = JSON.stringify(msg);
    const acks = document.getElementById("acks");
    acks.appendChild(node2);
}

function sendAckWithWrongId(event) {
    return handleMessage(event, crypto.randomUUID());
}

function enableMockAcks() {
    window.addEventListener("message", handleMessage, false);
}

function enableIncorrectMockAck() {
    window.addEventListener("message", sendAckWithWrongId, false);
}

function disableMockAcks() {
    window.removeEventListener("message", handleMessage);
}
