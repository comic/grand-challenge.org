/**
 * Webworker that converts any int/uint TypedArray of higher than 8-bit into
 * a normalized Float32Array.
 **/
addEventListener("message", (message) => {
    const arr = message.data;
    const arrName = arr.constructor.name.toLowerCase();
    if (arr.BYTES_PER_ELEMENT <= 1 || !arrName.includes("int")) {
        postMessage(arr);
        return;
    }
    const bitDepth = arr.BYTES_PER_ELEMENT * 8;
    let maxPixelValue = 2 ** bitDepth / 2;
    let minPixelValue = -maxPixelValue;
    if (arrName[0] === "u") {
        // === unsigned
        minPixelValue = 0;
        maxPixelValue = 2 ** bitDepth;
    }
    const normalizeFn = (v) =>
        (v - minPixelValue) / (maxPixelValue - minPixelValue);
    const result = new Float32Array(arr.length);
    arr.forEach((v, i) => {
        result[i] = normalizeFn(v);
    });
    postMessage(result);
});
