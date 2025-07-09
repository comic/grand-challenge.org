const dcmjs = require("dcmjs");
global.dcmjs = dcmjs;

const { TextEncoder, TextDecoder } = require("node:util");

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// JSDOM doesn't implement Blob.arrayBuffer() yet, which is needed by the
// isDicomFile() test. This polyfill implements it using FileReader.
if (global.Blob && !global.Blob.prototype.arrayBuffer) {
    global.Blob.prototype.arrayBuffer = function () {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsArrayBuffer(this);
            reader.onload = () => resolve(reader.result);
            reader.onerror = err => reject(err);
        });
    };
}
