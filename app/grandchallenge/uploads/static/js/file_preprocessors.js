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

// Helper to check if a file is a DICOM file by extension or magic byte
async function isDicomFile(file) {
    const dicomExtensions = [".dcm", ".dicom"];
    if (!dicomExtensions.some(ext => file.name.toLowerCase().endsWith(ext))) {
        return false;
    }

    // Check magic byte: DICOM files have "DICM" at byte offset 128
    const header = new Uint8Array(
        await file.data.slice(128, 132).arrayBuffer(),
    );
    const isDicomMagic =
        header.length === 4 &&
        header[0] === 0x44 && // 'D'
        header[1] === 0x49 && // 'I'
        header[2] === 0x43 && // 'C'
        header[3] === 0x4d; // 'M'

    return isDicomMagic;
}

const uidMap = new Map(); // Map to store unique identifiers for UIDs

// Recursive de-identification for a dataset (object with DICOM tags)
function deidentifyDataset(
    dataset,
    tagRules,
    defaultAction,
    debugChanges,
    defaultJustification,
) {
    const newDataset = {};
    for (const tagKey in dataset) {
        const vr = dataset[tagKey]?.vr;
        const tagValue = dataset[tagKey]?.Value?.[0];
        const protocolTagKey =
            dcmjs.data.DicomMetaDictionary.punctuateTag(tagKey);
        const tagRule = tagRules[protocolTagKey];
        const action = tagRule ? tagRule.default : defaultAction;
        const actionJustification = tagRule
            ? tagRule.justification
            : defaultJustification;
        const name =
            dcmjs.data.DicomMetaDictionary.dictionary[protocolTagKey]?.name ||
            "Unknown Tag";
        if (vr === "SQ" && Array.isArray(dataset[tagKey]?.Value)) {
            switch (action) {
                case "R":
                    throw new Error(
                        `Image is rejected due to de-identification protocol. Tag: ${tagKey}; Justification: ${actionJustification}`,
                    );
                case "K": {
                    // Recurse into each item, using the rules for this sequence
                    const items = dataset[tagKey].Value.map(item =>
                        deidentifyDataset(
                            item,
                            tagRules, // Use item-specific rules if present
                            defaultAction,
                            debugChanges,
                            defaultJustification,
                        ),
                    );
                    newDataset[tagKey] = { ...dataset[tagKey], Value: items };
                    debugChanges[`${protocolTagKey} - ${name}`] =
                        "RECURSE KEEP";
                    break;
                }
                case "D":
                case "Z": {
                    // Recurse and replace all items with dummy values
                    const items = dataset[tagKey].Value.map(item =>
                        deidentifyDataset(
                            item,
                            {}, // Disregard tagrules for nested items
                            "D", // Force dummy for all nested
                            debugChanges,
                            defaultJustification,
                        ),
                    );
                    newDataset[tagKey] = { ...dataset[tagKey], Value: items };
                    debugChanges[`${protocolTagKey} - ${name}`] =
                        "RECURSE DUMMY";
                    break;
                }
                case "U": {
                    // Recurse and consistently replace all items with mapped UID
                    const items = dataset[tagKey].Value.map(item =>
                        deidentifyDataset(
                            item,
                            {}, // Disregard tagrules for nested items
                            "U", // Force U for all nested
                            debugChanges,
                            defaultJustification,
                        ),
                    );
                    newDataset[tagKey] = { ...dataset[tagKey], Value: items };
                    debugChanges[`${protocolTagKey} - ${name}`] = "RECURSE UID";
                    break;
                }
                case "X":
                    debugChanges[`${protocolTagKey} - ${name}`] =
                        "REMOVED (SQ)";
                    break;
                default:
                    // Remove by default
                    debugChanges[`${protocolTagKey} - ${name}`] =
                        `REMOVED (SQ, unknown action: ${action})`;
                    break;
            }
            continue;
        }
        switch (action) {
            case "REJECT":
            case "R":
                throw new Error(
                    `Image is rejected due to de-identification protocol. Tag: ${tagKey}; Justification: ${actionJustification}`,
                );
            case "X":
                debugChanges[`${protocolTagKey} - ${name}`] = "REMOVED";
                break;
            case "K":
                debugChanges[`${protocolTagKey} - ${name}`] =
                    `KEEP value: ${tagValue}`;
                newDataset[tagKey] = dataset[tagKey];
                break;
            case "D":
            case "Z":
                newDataset[tagKey] = {
                    ...dataset[tagKey],
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
                        ...dataset[tagKey],
                        Value: [uidMap.get(tagValue)],
                    };
                    debugChanges[`${protocolTagKey} - ${name}`] =
                        `CONSISTENTLY REPLACED value: "${tagValue}" with: "${uidMap.get(tagValue)}"`;
                }
                break;
            default:
                console.warn(
                    `Unknown action "${action}" for tag ${tagKey}. Skipping.`,
                );
                break;
        }
    }
    return newDataset;
}

function setDeidentificationMethodTag(dataset, version) {
    const tagKey = "00120063"; // DICOM tag for De-identification Method
    const vr = "LO";
    const method = `De-identified by Grand Challenge client-side using procedure version ${version} on ${new Date().toISOString()}.`;
    if (dataset[tagKey]) {
        dataset[tagKey].Value[0] += `; ${method}`;
    } else {
        dataset[tagKey] = {
            vr: vr,
            Value: [method],
        };
    }
    return dataset;
}

function setPatientIdentityRemovedTag(dataset) {
    const tagKey = "00120062"; // DICOM tag for Patient Identity Removed
    const vr = "CS";
    const value = "YES";
    if (dataset[tagKey]) {
        // Overwrite or ensure value is YES
        dataset[tagKey].vr = vr;
        dataset[tagKey].Value[0] = value;
    } else {
        dataset[tagKey] = {
            vr: vr,
            Value: [value],
        };
    }
    return dataset;
}

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
    const protocol = globalThis.GrandChallengeDICOMDeIdProcedure || {};
    const sopClassRules = protocol.sopClass?.[sopClassUID] || {};
    const tagRules = sopClassRules.tag || {};
    const defaultAction = sopClassRules.default || protocol.default || "X";
    const debugChanges = {};
    let newDataset = deidentifyDataset(
        originalDataset,
        tagRules,
        defaultAction,
        debugChanges,
        protocol.justification || "No justification provided",
    );
    newDataset = setDeidentificationMethodTag(
        newDataset,
        protocol.version || "unknown",
    );
    newDataset = setPatientIdentityRemovedTag(newDataset);
    const dicomDict = new dcmjs.data.DicomDict(dicomData.meta);
    dicomDict.dict = newDataset;
    dicomDict._elements = dicomData._elements;
    const newBuffer = dicomDict.write();
    console.debug("De-identification changes:", debugChanges);
    return new File([newBuffer], file.name, { type: file.type });
}

/**
 * Registers file preprocessors used by Uppy to preprocess files.
 *
 * Each preprocessor object in the array must have the following properties:
 *
 * @property {function(File): Promise<boolean>} fileMatcher - An asynchronous
 * function that takes a File object as input and returns a Promise that
 * resolves tot a boolean indicating whether the file should be processed by
 * this preprocessor. Typically, this function checks the file extension or
 * inspects the file contents to determine if it matches the expected file
 * type (e.g., DICOM).
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

// Export for testing in Node.js environment
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        getDummyValue,
        isDicomFile,
        preprocessDicomFile,
        // For testing only
        _uidMap: uidMap,
    };
}
