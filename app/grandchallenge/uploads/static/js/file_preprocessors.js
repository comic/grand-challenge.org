/**
 * Returns a dummy value based on the DICOM Value Representation (VR).
 * This is used to replace sensitive data during de-identification.
 * @param {string} vr - The DICOM Value Representation (VR) of the tag.
 * @returns {*} - A dummy value appropriate for the given VR.
 */
function getDummyValue(vr) {
    switch (vr) {
        case "AE": // Application Entity - up to 16 characters, no leading/trailing spaces
            return "DUMMY_AE";

        case "AS": // Age String - 4 characters (nnnD, nnnW, nnnM, nnnY)
            return "030Y"; // 30 years

        case "AT": // Attribute Tag - 4 bytes as hex pairs
            return new Uint16Array([0x0000, 0x0000]); // (0000,0000)

        case "CS": // Code String - up to 16 characters, uppercase
            return "DUMMY";

        case "DA": // Date - YYYYMMDD format
            return "20000101"; // January 1, 2000

        case "DS": // Decimal String - floating point as string, up to 16 chars
            return "0.0";

        case "DT": // Date Time - YYYYMMDDHHMMSS.FFFFFF&ZZXX format
            return "20000101120000.000000";

        case "FL": // Floating Point Single - 4 bytes
            return new Float32Array([0.0])[0];

        case "FD": // Floating Point Double - 8 bytes
            return new Float64Array([0.0])[0];

        case "IS": // Integer String - integer as string, up to 12 chars
            return "0";

        case "LO": // Long String - up to 64 characters
            return "DUMMY_LONG_STRING";

        case "LT": // Long Text - up to 10240 characters
            return "DUMMY LONG TEXT";

        case "OB": // Other Byte - sequence of bytes
            return new Uint8Array([0x00]); // Single zero byte

        case "OD": // Other Double - sequence of 64-bit floating point values
            return new Float64Array([0.0]).buffer;

        case "OF": // Other Float - sequence of 32-bit floating point values
            return new Float32Array([0.0]).buffer;

        case "OL": // Other Long - sequence of 32-bit words
            return new Uint32Array([0x00000000]).buffer;

        case "OV": // Other Very Long - sequence of 64-bit words
            return new BigUint64Array([0n]).buffer;

        case "OW": // Other Word - sequence of 16-bit words
            return new Uint16Array([0x0000]).buffer;

        case "PN": // Person Name - up to 64 chars per component, format: Family^Given^Middle^Prefix^Suffix
            return "DUMMY^PATIENT^^^";

        case "SH": // Short String - up to 16 characters
            return "DUMMY";

        case "SL": // Signed Long - 32-bit signed integer
            return new Int32Array([0])[0];

        case "SQ": // Sequence - sequence of items
            return []; // Empty sequence

        case "SS": // Signed Short - 16-bit signed integer
            return new Int16Array([0])[0];

        case "ST": // Short Text - up to 1024 characters
            return "DUMMY SHORT TEXT";

        case "SV": // Signed Very Long - 64-bit signed integer
            return new BigInt64Array([0n])[0];

        case "TM": // Time - HHMMSS.FFFFFF format
            return "120000.000000"; // 12:00:00.000000

        case "UC": // Unlimited Characters - unlimited length
            return "DUMMY UNLIMITED CHARACTERS";

        case "UI": // Unique Identifier - UID format with dots and numbers
            return "1.2.3.4.5.6.7.8.9.0.1.2.3.4.5.6.7.8.9.0"; // Valid UID format

        case "UL": // Unsigned Long - 32-bit unsigned integer
            return new Uint32Array([0])[0];

        case "UN": // Unknown - sequence of bytes
            return new Uint8Array([0x00]).buffer; // Single zero byte buffer

        case "UR": // Universal Resource Identifier/Locator - URI/URL
            return "http://dummy.example.com";

        case "US": // Unsigned Short - 16-bit unsigned integer
            return new Uint16Array([0])[0];

        case "UT": // Unlimited Text - unlimited length text
            return "DUMMY UNLIMITED TEXT";

        case "UV": // Unsigned Very Long - 64-bit unsigned integer
            return new BigUint64Array([0n])[0];

        default:
            throw new Error(`Unsupported DICOM VR: ${vr}`);
    }
}

// Helper to check if a file is a DICOM file by extension
function isDicomFile(file) {
    const dicomExtensions = [".dcm", ".dicom"];
    const isDicom = dicomExtensions.some(ext =>
        file.name.toLowerCase().endsWith(ext),
    );
    return isDicom;
}

const uidMap = new Map(); // Map to store unique identifiers for UIDs

async function preprocessDicomFile(file) {
    if (
        typeof dcmjs === "undefined" ||
        !dcmjs.data ||
        !dcmjs.data.DicomMessage
    ) {
        throw new Error("dcmjs is not available");
    }
    const arrayBuffer = await file.arrayBuffer();
    const dicomData = dcmjs.data.DicomMessage.readFile(arrayBuffer);
    const originalDataset = dicomData.dict;
    const sopClassUID = originalDataset["00080016"]?.Value?.[0] || "";
    const protocol = globalThis.DEIDENTIFICATION_PROTOCOL || {};
    const sopClassRules = protocol.sopClass?.[sopClassUID] || {};
    const tagRules = sopClassRules.tag || {};
    const defaultAction = sopClassRules.default || protocol.default || "X";

    // Build a new dataset, copying only the tags that should be kept or modified
    const debugChanges = {};
    const newDataset = {};
    for (const tagKey in originalDataset) {
        const vr = originalDataset[tagKey]?.vr;
        const tagValue = originalDataset[tagKey]?.Value?.[0];
        const protocolTagKey =
            dcmjs.data.DicomMetaDictionary.punctuateTag(tagKey);
        const tagRule = tagRules[protocolTagKey];
        const action = tagRule ? tagRule.default : defaultAction;
        const name =
            dcmjs.data.DicomMetaDictionary.dictionary[protocolTagKey]?.name ||
            "Unknown Tag";
        switch (action) {
            case "REJECT":
            case "R":
                throw new Error(
                    `Image is rejected due to de-identification protocol. Tag: ${tagKey}`,
                );
            case "X":
                debugChanges[`${protocolTagKey} - ${name}`] = "REMOVED";
                // Remove tag (do not copy)
                break;
            case "K":
                // Keep original value
                debugChanges[`${protocolTagKey} - ${name}`] =
                    `KEEP value: ${tagValue}`;
                newDataset[tagKey] = originalDataset[tagKey];
                break;
            case "D":
            case "Z":
                newDataset[tagKey] = {
                    ...originalDataset[tagKey],
                    Value: [getDummyValue(vr)],
                };
                debugChanges[`${protocolTagKey} - ${name}`] =
                    `REPLACED value: "${tagValue}" with: "${getDummyValue(vr)}"`;
                break;
            case "U":
                if (tagValue) {
                    if (!uidMap.has(tagValue)) {
                        uidMap.set(
                            tagValue,
                            dcmjs.data.DicomMetaDictionary.uid(),
                        );
                    }
                    newDataset[tagKey] = {
                        ...originalDataset[tagKey],
                        Value: [uidMap.get(tagValue)],
                    };
                    debugChanges[`${protocolTagKey} - ${name}`] =
                        `CONSISTENTLY REPLACED value: "${tagValue}" with: "${uidMap.get(tagValue)}"`;
                }
                break;
            default:
                // Remove tag by default (do not copy) and warn
                console.warn(
                    `Unknown action "${action}" for tag ${tagKey}. Skipping.`,
                );
                break;
        }
    }
    // Write back to ArrayBuffer and create a new File, preserving all data (including PixelData)
    const dicomDict = new dcmjs.data.DicomDict(dicomData.meta);
    dicomDict.dict = newDataset;
    // Copy the original _elements buffer to preserve binary data
    dicomDict._elements = dicomData._elements;
    const newBuffer = dicomDict.write();
    console.log("De-identification changes:", debugChanges);
    return new File([newBuffer], file.name, { type: file.type });
}

/**
 * Registers file preprocessors used by Uppy to preprocess files.
 *
 * Each preprocessor object in the array must have the following properties:
 *
 * @property {function(File): boolean} fileMatcher - A function that takes a
 * File object as input and returns a boolean indicating whether the file
 * should be processed by this preprocessor. Typically, this function checks
 * the file extension or inspects the file contents to determine if it
 * matches the expected file type (e.g., DICOM).
 *
 * @property {function(File): Promise<File>} preprocessor - An asynchronous
 * function that takes a File object as input and returns a Promise that
 * resolves to a new, processed File object. This function performs any
 * necessary preprocessing (such as de-identification, conversion, or
 * validation) before the file is uploaded or further handled by Uppy.
 */
globalThis.UPPY_FILE_PREPROCESSORS = [
    {
        fileMatcher: isDicomFile,
        preprocessor: preprocessDicomFile,
    },
];
