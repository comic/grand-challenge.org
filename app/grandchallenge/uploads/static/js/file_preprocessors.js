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

function generateCurationSpec(customConfig, createDummyValueFn) {
    const uidMap = new Map();

    return () => ({
        version: "2.0",
        dicomPS315EOptions: {
            cleanDescriptorsOption: false, // Clean all descriptors by default
            // cleanDescriptorsExceptions: [], // No exceptions by default
            retainLongitudinalTemporalInformationOptions: "Full", // Remove all temporal info
            // retainPatientCharacteristicsOption: [], // Remove all patient characteristics
            retainDeviceIdentityOption: true, // Remove device identity
            retainUIDsOption: "On", // Replace UIDs with new ones (or 'Hashed' for repeatable blinding)
            retainSafePrivateOption: "Quarantine", // Remove all private tags (or 'Quarantine' for review)
            retainInstitutionIdentityOption: true,
        },

        // The modifications function will apply specific rules from the custom config
        modifications(parser) {
            const dicomHeaderModifications = {};
            const dicomTags = parser.getAllDicomTags
                ? parser.getAllDicomTags()
                : Object.keys(dcmjs.data.DicomMetaDictionary.dictionary);
            const sopClassUID = parser.getDicom("SOPClassUID");
            let sopClassRules = {};
            if (customConfig.sopClass?.[sopClassUID]) {
                sopClassRules = customConfig.sopClass[sopClassUID];
            }
            const tagRules = sopClassRules.tag || {};
            const defaultAction = sopClassRules.default || customConfig.default;

            for (const tagKey of dicomTags) {
                const tagRule = tagRules[tagKey];
                // Lookup the DICOM keyword name and VR using the dcmjs dictionary
                const dicomTagInfo =
                    dcmjs.data.DicomMetaDictionary.dictionary[tagKey];
                const tagName = dicomTagInfo?.name;
                const vr = dicomTagInfo?.vr;
                if (!tagName || !vr) {
                    console.warn(
                        `Unknown tag ${tagKey} or VR not found in dictionary. Skipping.`,
                    );
                    continue;
                }
                const action = tagRule ? tagRule.default : defaultAction;
                const justification =
                    tagRule?.justification || "SOP Class is not allowed";
                const tagValue = tagName ? parser.getDicom(tagName) : null;
                switch (action) {
                    case "REJECT":
                        throw new Error(
                            `Image is rejected due to de-identification protocol. Reason: ${justification}`,
                        );
                    case "X":
                        // Remove: default behavior, do nothing
                        break;
                    case "K":
                        dicomHeaderModifications[tagName] = tagValue;
                        break;
                    case "D":
                    case "Z":
                        dicomHeaderModifications[tagName] =
                            createDummyValueFn(vr);
                        break;
                    case "U":
                        if (tagValue) {
                            if (!uidMap.has(tagValue)) {
                                uidMap.set(
                                    tagValue,
                                    dcmjs.data.DicomMetaDictionary.uid(),
                                );
                            }
                            dicomHeaderModifications[tagName] =
                                uidMap.get(tagValue);
                        }
                        break;
                    default:
                        console.warn(
                            `Unknown action "${action}" for tag ${tagKey}. Skipping.`,
                        );
                }
            }

            return {
                dicomHeader: dicomHeaderModifications,
                outputFilePathComponents: [],
            };
        },

        validation(parser) {
            const errors = [];
            return { errors };
        },
    });
}

const curationSpec = generateCurationSpec(
    globalThis.DEIDENTIFICATION_PROTOCOL,
    getDummyValue,
);

// Helper to check if a file is a DICOM file by extension
function isDicomFile(file) {
    const dicomExtensions = [".dcm", ".dicom"];
    const isDicom = dicomExtensions.some(ext =>
        file.name.toLowerCase().endsWith(ext),
    );
    return isDicom;
}

// Async preprocessing for DICOM files using dicom-curate
async function preprocessDicomFile(file) {
    if (
        !globalThis.dicomCurate ||
        typeof globalThis.dicomCurate.curateOne !== "function"
    ) {
        throw new Error("dicomCurate.curateOne is not available");
    }

    const columnMappings = {};

    const mappingOptions = { curationSpec, columnMappings };
    const fileInfo = {
        name: file.name,
        size: file.size,
        kind: "blob",
        blob: file,
    };
    const result = await globalThis.dicomCurate.curateOne(
        fileInfo,
        undefined,
        mappingOptions,
    );
    if (!result.mappedBlob) {
        throw new Error("dicomCurate.curateOne did not return a mappedBlob");
    }
    const processedFile = new File([result.mappedBlob], file.name, {
        type: file.type,
    });
    console.log("[DICOM] Preprocessing complete for file:", file.name);
    return processedFile;
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
