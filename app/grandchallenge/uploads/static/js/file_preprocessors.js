/**
 * Returns a dummy value based on the DICOM Value Representation (VR).
 * This is used to replace sensitive data during de-identification.
 * @param {string} vr - The DICOM Value Representation (VR) of the tag.
 * @returns {*} - A dummy value appropriate for the given VR.
 */
function getDummyValue(vr) {
    switch (vr) {
        case "AE": // Application Entity
        case "AS": // Age String
        case "CS": // Code String
        case "DA": // Date
        case "DS": // Decimal String
        case "IS": // Integer String
        case "LO": // Long String
        case "LT": // Long Text
        case "PN": // Person Name
        case "SH": // Short String
        case "ST": // Short Text
        case "TM": // Time
        case "UI": // UID
        case "UC": // Unlimited Characters
        case "UR": // URI
        case "UT": // Unlimited Text
            return "DUMMY";
        case "FL": // Floating Point Single
        case "FD": // Floating Point Double
            return 0.0;
        case "SL": // Signed Long
        case "SS": // Signed Short
        case "UL": // Unsigned Long
        case "US": // Unsigned Short
            return 0;
        case "AT": // Attribute Tag
            return "(0000,0000)"; // A valid but empty tag
        case "OB": // Other Byte
        case "OD": // Other Double
        case "OF": // Other Float
        case "OW": // Other Word
        case "UN": // Unknown
            return new Uint8Array(0).buffer; // Empty buffer
        case "SQ": // Sequence
            return []; // Empty sequence
        default:
            return null; // Or throw an error for unsupported VR
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
    const newDataset = {};
    for (const tagKey in originalDataset) {
        const vr = originalDataset[tagKey]?.vr;
        const tagValue = originalDataset[tagKey]?.Value?.[0];
        const protocolTagKey =
            dcmjs.data.DicomMetaDictionary.punctuateTag(tagKey);
        const tagRule = tagRules[protocolTagKey];
        const action = tagRule ? tagRule.default : defaultAction;
        switch (action) {
            case "REJECT":
                throw new Error(
                    `Image is rejected due to de-identification protocol. Tag: ${tagKey}`,
                );
            case "X":
                // Remove tag (do not copy)
                break;
            case "K":
                // Keep original value
                newDataset[tagKey] = originalDataset[tagKey];
                break;
            case "D":
            case "Z":
                newDataset[tagKey] = {
                    ...originalDataset[tagKey],
                    Value: [getDummyValue(vr)],
                };
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
