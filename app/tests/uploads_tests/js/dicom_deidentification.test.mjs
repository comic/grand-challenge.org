import { jest } from "@jest/globals";
import Uppy from "../../../grandchallenge/core/static/vendored/uppy/uppy.min.js";
global.Uppy = Uppy;
const {
    getDummyValue,
    preprocessDicomFile,
    DicomDeidentifierPlugin,
    uidMap: _uidMap,
} = await import(
    "../../../grandchallenge/uploads/static/js/dicom_deidentification"
);

describe("getDummyValue", () => {
    const testCases = [
        { vr: "AE", expected: "DUMMY_AE" },
        { vr: "AS", expected: "030Y" },
        { vr: "AT", expected: new Uint16Array([0x0000, 0x0000]) },
        { vr: "CS", expected: "DUMMY" },
        { vr: "DA", expected: "20000101" },
        { vr: "DS", expected: "0.0" },
        { vr: "DT", expected: "20000101120000.000000" },
        { vr: "FL", expected: new Float32Array([0.0])[0] },
        { vr: "FD", expected: new Float64Array([0.0])[0] },
        { vr: "IS", expected: "0" },
        { vr: "LO", expected: "DUMMY_LONG_STRING" },
        { vr: "LT", expected: "DUMMY LONG TEXT" },
        { vr: "OB", expected: new Uint8Array([0x00]) },
        { vr: "OD", expected: new Float64Array([0.0]).buffer },
        { vr: "OF", expected: new Float32Array([0.0]).buffer },
        { vr: "OL", expected: new Uint32Array([0x00000000]).buffer },
        { vr: "OV", expected: new BigUint64Array([0n]).buffer },
        { vr: "OW", expected: new Uint16Array([0x0000]).buffer },
        { vr: "PN", expected: "DUMMY^PATIENT^^^" },
        { vr: "SH", expected: "DUMMY" },
        { vr: "SL", expected: new Int32Array([0])[0] },
        { vr: "SQ", expected: [] },
        { vr: "SS", expected: new Int16Array([0])[0] },
        { vr: "ST", expected: "DUMMY SHORT TEXT" },
        { vr: "SV", expected: new BigInt64Array([0n])[0] },
        { vr: "TM", expected: "120000.000000" },
        { vr: "UC", expected: "DUMMY UNLIMITED CHARACTERS" },
        { vr: "UI", expected: "1.2.3.4.5.6.7.8.9.0.1.2.3.4.5.6.7.8.9.0" },
        { vr: "UL", expected: new Uint32Array([0])[0] },
        { vr: "UN", expected: new Uint8Array([0x00]).buffer },
        { vr: "UR", expected: "http://dummy.example.com" },
        { vr: "US", expected: new Uint16Array([0])[0] },
        { vr: "UT", expected: "DUMMY UNLIMITED TEXT" },
        { vr: "UV", expected: new BigUint64Array([0n])[0] },
    ];

    test.each(testCases)(
        "should return the correct dummy value for VR $vr",
        ({ vr, expected }) => {
            expect(getDummyValue(vr)).toEqual(expected);
        },
    );

    test("should throw an error for an unsupported VR", () => {
        const unsupportedVR = "XX";
        expect(() => getDummyValue(unsupportedVR)).toThrow(
            `Unsupported DICOM VR: ${unsupportedVR}`,
        );
    });
});

describe("preprocessDicomFile", () => {
    const createDicomFileBuffer = tags => {
        const meta = {
            "00020010": { vr: "UI", Value: ["1.2.840.10008.1.2.1"] }, // TransferSyntaxUID
        };
        const dicomDict = new dcmjs.data.DicomDict(meta);
        dicomDict.dict = tags;
        return dicomDict.write();
    };

    const createDicomFile = (tags, filename = "test.dcm") => {
        const buffer = createDicomFileBuffer(tags);
        return new File([buffer], filename, { type: "application/dicom" });
    };

    const getProcessedDataset = async processedFile => {
        const buffer = await processedFile.arrayBuffer();
        return dcmjs.data.DicomMessage.readFile(buffer).dict;
    };

    beforeEach(() => {
        global.GrandChallengeDICOMDeIdProcedure = {};
        globalThis.uidMap.clear();
    });

    test("should throw an error if dcmjs is not available", async () => {
        const originalDcmjs = global.dcmjs;
        global.dcmjs = undefined;
        const file = new File([new ArrayBuffer(1)], "test.dcm");
        await expect(preprocessDicomFile(file)).rejects.toThrow(
            "dcmjs is not available",
        );
        global.dcmjs = originalDcmjs;
    });

    test("should reject non-dicom files", async () => {
        const buffer = createDicomFileBuffer({});
        const validFile = new File([buffer], "valid");

        await expect(preprocessDicomFile(validFile)).resolves.toBeDefined();

        const view = new Uint8Array(buffer);
        // Set the magic bytes at offset 128, for valid dicom this is "DICM"
        view.set(new TextEncoder().encode("XXXX"), 128);

        const invalidFile = new File([buffer], "invalid");
        await expect(preprocessDicomFile(invalidFile)).rejects.toThrow(
            "Invalid DICOM file, expected header is missing",
        );
    });

    test("should remove tags by default ('X') and keep specified tags ('K')", async () => {
        const file = createDicomFile({
            "00100010": { vr: "PN", Value: ["Patient Name"] }, // To be removed
            "00080050": { vr: "SH", Value: ["ACC123"] }, // To be kept
        });

        global.GrandChallengeDICOMDeIdProcedure = {
            default: "X",
            sopClass: { "": { tag: { "(0008,0050)": { default: "K" } } } },
            version: "1.0",
        };

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);

        expect(dataset["00100010"]).toBeUndefined();
        expect(dataset["00080050"]).toBeDefined();
        expect(dataset["00080050"].Value[0]).toBe("ACC123");
        expect(dataset["00120063"]).toBeDefined(); // De-id method tag
        expect(processedFile).toBeInstanceOf(File);
    });

    test("should dummy tags with 'D' action", async () => {
        const file = createDicomFile({
            "00080070": { vr: "LO", Value: ["Healthcare Ultrasound"] },
        });
        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: { "": { tag: { "(0008,0070)": { default: "D" } } } },
        };

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);

        expect(dataset["00080070"].Value[0]).toBe("DUMMY_LONG_STRING");
    });

    test("should map UIDs consistently with 'U' action", async () => {
        const originalUID = "1.2.3.4";
        const file = createDicomFile({
            "00080018": { vr: "UI", Value: [originalUID] },
        });
        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: { "": { tag: { "(0008,0018)": { default: "U" } } } },
        };

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);
        const newUID = dataset["00080018"].Value[0];

        expect(newUID).toBeDefined();
        expect(newUID).not.toBe(originalUID);

        // Check consistency with a new file using the same original UID
        expect(globalThis.uidMap.get(originalUID)).toBe(newUID);
        const file2 = createDicomFile({
            "00080018": { vr: "UI", Value: [originalUID] },
        });
        const processedFile2 = await preprocessDicomFile(file2);
        const dataset2 = await getProcessedDataset(processedFile2);
        const newUID2 = dataset2["00080018"].Value[0];
        expect(newUID2).toBe(newUID);

        // Check inconsistency with a different original UID
        const differentUID = "1.2.3.5";
        const file3 = createDicomFile({
            "00080018": { vr: "UI", Value: [differentUID] },
        });
        const processedFile3 = await preprocessDicomFile(file3);
        const dataset3 = await getProcessedDataset(processedFile3);
        const newUID3 = dataset3["00080018"].Value[0];
        expect(newUID3).not.toBe(newUID);
        expect(globalThis.uidMap.get(differentUID)).toBe(newUID3);
        expect(globalThis.uidMap.size).toBe(2);
    });

    test("should reject files with 'R' action", async () => {
        const file = createDicomFile({
            "00100010": { vr: "PN", Value: ["Patient Name"] },
        });
        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: {
                "": {
                    tag: {
                        "(0010,0010)": {
                            default: "R",
                            justification: "Test Reject",
                        },
                    },
                },
            },
        };

        await expect(preprocessDicomFile(file)).rejects.toThrow(
            "Image is rejected due to de-identification protocol. Tag: 00100010; Justification: Test Reject",
        );
    });

    test("should handle D sequences by dummying all nested tags", async () => {
        const file = createDicomFile({
            "00540016": {
                vr: "SQ",
                Value: [
                    {
                        "00080070": {
                            vr: "LO",
                            Value: ["Healthcare Ultrasound"],
                        },
                    },
                ],
            },
        });
        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: { "": { tag: { "(0054,0016)": { default: "D" } } } },
        };

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);
        const processedSequence = dataset["00540016"].Value;

        expect(processedSequence[0]["00080070"].Value[0]).toBe(
            "DUMMY_LONG_STRING",
        );
    });

    test("should handle U sequences by consistently replacing all nested tags", async () => {
        const file = createDicomFile({
            "00540016": {
                vr: "SQ",
                Value: [
                    {
                        "00081150": {
                            vr: "UI",
                            Value: ["1.2.840.10008.5.1.4.1.1.6.1"],
                        },
                    },
                ],
            },
        });
        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: { "": { tag: { "(0054,0016)": { default: "U" } } } },
        };

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);
        const processedSequence = dataset["00540016"].Value;

        expect(processedSequence[0]["00081150"].Value[0]).toBe(
            globalThis.uidMap.get("1.2.840.10008.5.1.4.1.1.6.1"),
        );
    });

    test("should handle K sequences by iterating all nested tags and actions", async () => {
        const file = createDicomFile({
            "00540016": {
                vr: "SQ",
                Value: [
                    {
                        "00080070": {
                            vr: "LO",
                            Value: ["Healthcare Ultrasound"],
                        },
                        "00540017": { vr: "LO", Value: ["Nested Long String"] },
                    },
                ],
            },
        });
        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: {
                "": {
                    tag: {
                        "(0054,0016)": { default: "K" },
                        "(0008,0070)": { default: "D" },
                        "(0054,0017)": { default: "X" },
                    },
                },
            },
        };

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);
        const processedSequence = dataset["00540016"].Value;

        expect(processedSequence[0]["00080070"].Value[0]).toBe(
            "DUMMY_LONG_STRING",
        );
        expect(processedSequence[0]["00540017"]).toBeUndefined();
    });

    test("should set Patient Identity Removed tag (0012,0062) to 'YES'", async () => {
        const file = createDicomFile({
            "00100010": { vr: "PN", Value: ["Patient Name"] },
        });
        // No special procedure required; use defaults
        global.GrandChallengeDICOMDeIdProcedure = {};

        const processedFile = await preprocessDicomFile(file);
        const dataset = await getProcessedDataset(processedFile);

        expect(dataset["00120062"]).toBeDefined();
        expect(dataset["00120062"].vr).toBe("CS");
        expect(dataset["00120062"].Value[0]).toBe("YES");
    });

    describe("setDeidentificationMethodTag", () => {
        test("adds description when tag absent", async () => {
            const file = createDicomFile({}, "absent.dcm");
            global.GrandChallengeDICOMDeIdProcedure = {
                default: "K",
                version: "2.5",
            };
            const processedFile = await preprocessDicomFile(file);
            const dataset = await getProcessedDataset(processedFile);
            expect(dataset["00120063"]).toBeDefined();
            expect(dataset["00120063"].Value[0]).toMatch(
                /^grand-challenge-dicom-client-de-identifier:procedure:2\.5:date:/,
            );
        });

        test("appends description when single existing value present", async () => {
            const file = createDicomFile(
                {
                    "00120063": { vr: "LO", Value: "existing" },
                },
                "single.dcm",
            );
            global.GrandChallengeDICOMDeIdProcedure = {
                default: "K",
                version: "v1",
            };
            const processedFile = await preprocessDicomFile(file);
            const dataset = await getProcessedDataset(processedFile);
            expect(dataset["00120063"].Value[0]).toBe("existing");
            const appended = dataset["00120063"].Value.slice(-1)[0];
            expect(dataset["00120063"].Value[1]).toMatch(
                /^grand-challenge-dicom-client-de-identifier:procedure:v1:date:/,
            );
        });

        test("appends description when multiple existing values present", async () => {
            const file = createDicomFile(
                {
                    "00120063": { vr: "LO", Value: ["a", "b"] },
                },
                "multiple.dcm",
            );
            global.GrandChallengeDICOMDeIdProcedure = {
                default: "K",
                version: "v2",
            };
            const processedFile = await preprocessDicomFile(file);
            const dataset = await getProcessedDataset(processedFile);
            expect(dataset["00120063"].Value[0]).toBe("a");
            expect(dataset["00120063"].Value[1]).toBe("b");
            const appended = dataset["00120063"].Value.slice(-1)[0];
            expect(dataset["00120063"].Value[2]).toMatch(
                /^grand-challenge-dicom-client-de-identifier:procedure:v2:date:/,
            );
        });
    });
});

describe("DicomDeidentifierPlugin", () => {
    let uppy;
    let plugin;

    beforeEach(() => {
        global.GrandChallengeDICOMDeIdProcedure = {};

        uppy = new Uppy.Core();
        uppy.use(DicomDeidentifierPlugin);
        plugin = uppy.getPlugin("DicomDeidentifierPlugin");
    });

    afterEach(() => {
        uppy.close();
        globalThis.uidMap.clear();
    });

    const createDicomFileBuffer = tags => {
        const meta = {
            "00020010": { vr: "UI", Value: ["1.2.840.10008.1.2.1"] }, // TransferSyntaxUID
        };
        const dicomDict = new global.dcmjs.data.DicomDict(meta);
        dicomDict.dict = tags;
        return dicomDict.write();
    };

    test("should preprocess all files through Uppy", async () => {
        global.GrandChallengeDICOMDeIdProcedure = {
            default: "X",
            sopClass: { "": { tag: { "(0008,0050)": { default: "K" } } } },
            version: "1.0",
        };

        const buffer1 = createDicomFileBuffer({
            "00100010": { vr: "PN", Value: ["Patient One"] },
            "00080050": { vr: "SH", Value: ["ACC001"] },
        });
        const buffer2 = createDicomFileBuffer({
            "00100010": { vr: "PN", Value: ["Patient Two"] },
            "00080050": { vr: "SH", Value: ["ACC002"] },
        });

        const file1 = new File([buffer1], "file1.dcm", {
            type: "application/dicom",
        });
        const file2 = new File([buffer2], "file2.dcm", {
            type: "application/dicom",
        });

        uppy.addFile({ name: file1.name, type: file1.type, data: file1 });
        uppy.addFile({ name: file2.name, type: file2.type, data: file2 });

        const fileIDs = Object.keys(uppy.getState().files);
        await plugin.prepareUpload(fileIDs);

        const processedFile1 = uppy.getFile(fileIDs[0]).data;
        const processedFile2 = uppy.getFile(fileIDs[1]).data;

        const dataset1 = global.dcmjs.data.DicomMessage.readFile(
            await processedFile1.arrayBuffer(),
        ).dict;

        const dataset2 = global.dcmjs.data.DicomMessage.readFile(
            await processedFile2.arrayBuffer(),
        ).dict;

        expect(dataset1["00100010"]).toBeUndefined();
        expect(dataset1["00080050"].Value[0]).toBe("ACC001");
        expect(dataset1["00120062"].Value[0]).toBe("YES"); // PatientIdentityRemoved

        expect(dataset2["00100010"]).toBeUndefined();
        expect(dataset2["00080050"].Value[0]).toBe("ACC002");
        expect(dataset2["00120062"].Value[0]).toBe("YES"); // PatientIdentityRemoved
    });

    test("should remove files that fail preprocessing and show alert", async () => {
        const alertSpy = jest.spyOn(window, "alert").mockImplementation();

        const buffer = createDicomFileBuffer({
            "00100010": { vr: "PN", Value: ["Patient Name"] },
        });
        const file = new File([buffer], "reject.dcm", {
            type: "application/dicom",
        });

        global.GrandChallengeDICOMDeIdProcedure = {
            sopClass: {
                "": {
                    tag: {
                        "(0010,0010)": {
                            default: "R",
                            justification: "Test rejection",
                        },
                    },
                },
            },
        };

        uppy.addFile({ name: file.name, type: file.type, data: file });
        const fileIDs = Object.keys(uppy.getState().files);

        await plugin.prepareUpload(fileIDs);

        expect(uppy.getFile(fileIDs[0])).toBeUndefined();
        expect(alertSpy).toHaveBeenCalledWith(
            expect.stringContaining(
                "Could not upload reject.dcm (application/dicom):",
            ),
        );

        alertSpy.mockRestore();
    });

    test("should handle mixed success and failure files", async () => {
        const alertSpy = jest.spyOn(window, "alert").mockImplementation();

        const successBuffer = createDicomFileBuffer({
            "00080050": { vr: "SH", Value: ["ACC123"] },
        });
        const rejectBuffer = createDicomFileBuffer({
            "00100010": { vr: "PN", Value: ["Patient Name"] },
        });

        const successFile = new File([successBuffer], "success.dcm", {
            type: "application/dicom",
        });
        const rejectFile = new File([rejectBuffer], "reject.dcm", {
            type: "application/dicom",
        });

        global.GrandChallengeDICOMDeIdProcedure = {
            default: "K",
            sopClass: {
                "": {
                    tag: {
                        "(0010,0010)": {
                            default: "R",
                            justification: "Test rejection",
                        },
                    },
                },
            },
            version: "1.0",
        };

        uppy.addFile({
            name: successFile.name,
            type: successFile.type,
            data: successFile,
        });
        uppy.addFile({
            name: rejectFile.name,
            type: rejectFile.type,
            data: rejectFile,
        });

        const fileIDs = Object.keys(uppy.getState().files);
        const results = await plugin.prepareUpload(fileIDs);

        expect(results.length).toBe(2);
        expect(results[0].status).toBe("fulfilled");
        expect(results[1].status).toBe("rejected");

        const remainingFiles = Object.values(uppy.getState().files);
        expect(remainingFiles.length).toBe(1);
        expect(remainingFiles[0].name).toBe("success.dcm");

        alertSpy.mockRestore();
    });
});
