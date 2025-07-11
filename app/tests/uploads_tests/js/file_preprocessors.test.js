const {
    getDummyValue,
    isDicomFile,
    preprocessDicomFile,
    _uidMap,
} = require("../../../grandchallenge/uploads/static/js/file_preprocessors");

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

describe("isDicomFile", () => {
    // Helper to create mock DICOM content with optional magic bytes.
    const createDicomContent = (magic = "DICM") => {
        const buffer = new ArrayBuffer(132);
        const view = new Uint8Array(buffer);
        // Set the magic bytes at offset 128
        view.set(new TextEncoder().encode(magic), 128);
        return buffer;
    };

    const validDicomContent = createDicomContent("DICM");
    const invalidDicomContent = createDicomContent("XXXX");
    const shortContent = new ArrayBuffer(100);

    const testCases = [
        {
            name: "a valid DICOM file with .dcm extension",
            filename: "test.dcm",
            content: validDicomContent,
            expected: true,
        },
        {
            name: "a valid DICOM file with .dicom extension",
            filename: "test.dicom",
            content: validDicomContent,
            expected: true,
        },
        {
            name: "a valid DICOM file with an uppercase .DCM extension",
            filename: "test.DCM",
            content: validDicomContent,
            expected: true,
        },
        {
            name: "a file with a non-DICOM extension",
            filename: "test.txt",
            content: validDicomContent,
            expected: false,
        },
        {
            name: "a file with a DICOM extension but incorrect magic bytes",
            filename: "test.dcm",
            content: invalidDicomContent,
            expected: false,
        },
        {
            name: "a file that is too short to contain the magic bytes",
            filename: "test.dcm",
            content: shortContent,
            expected: false,
        },
        {
            name: "a file with a DICOM extension but empty content",
            filename: "test.dcm",
            content: new ArrayBuffer(0),
            expected: false,
        },
    ];

    test.each(testCases)(
        "should return $expected for $name",
        async ({ filename, content, expected }) => {
            // Create a mock Uppy file object, which has a `data` property
            // containing the actual File/Blob object. This matches what the
            // function receives in the browser.
            const uppyFile = {
                name: filename,
                data: new File([content], filename),
            };
            await expect(isDicomFile(uppyFile)).resolves.toBe(expected);
        },
    );
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
        _uidMap.clear();
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
        expect(_uidMap.get(originalUID)).toBe(newUID);
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
        expect(_uidMap.get(differentUID)).toBe(newUID3);
        expect(_uidMap.size).toBe(2);
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
            _uidMap.get("1.2.840.10008.5.1.4.1.1.6.1"),
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
});
