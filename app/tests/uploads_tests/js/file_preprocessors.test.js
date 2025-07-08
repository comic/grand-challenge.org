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
