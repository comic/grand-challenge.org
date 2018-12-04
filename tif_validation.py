import traceback

import tifffile as tiff_lib


def validate_tif(path):
    accepted_color_models = {"PHOTOMETRIC.MINISBLACK": 1,
                             "PHOTOMETRIC.RGB": 3,
                             "PHOTOMETRIC.ARGB": 4,
                             "PHOTOMETRIC.YCBCR": 4, }

    required_tile_tags = ("TileWidth",
                          "TileLength",
                          "TileOffsets",
                          "TileByteCounts", )

    forbidden_description_tags = ("DICOM",
                                  "XML",
                                  "xml", )

    try:
        # Reads the TIF tags
        tif_file = tiff_lib.TiffFile(path)
        tif_tags = tif_file.pages[0].tags

        # Checks if the image description exists, if so, ensure there's no DICOM or XML data
        if "ImageDescription" in tif_tags:
            image_description = str(tif_tags["ImageDescription"].value)
            for forbidden in forbidden_description_tags:
                if forbidden in image_description:
                    return False

        # Checks image storage information
        for tag in required_tile_tags:
            if tag not in tif_tags.keys():
                return False

        if len(tif_file.pages) == 1:
            return False

        if (str(tif_tags["PlanarConfiguration"].value) != "PLANARCONFIG.CONTIG"):
            return False

        # Checks colour model information
        if (str(tif_tags["PhotometricInterpretation"].value) not in accepted_color_models):
            return False

        if (accepted_color_models[str(tif_tags["PhotometricInterpretation"].value)]
                != tif_tags["SamplesPerPixel"].value):
            return False

        # Check datatype information
        if str(tif_tags["SampleFormat"].value[0]) == "IEEEFP":
            if tif_tags["BitsPerSample"].value[0] != 32:
                return False
        elif str(tif_tags["SampleFormat"].value[0]) == "UINT":
            if tif_tags["BitsPerSample"].value[0] not in (8, 16, 32):
                return False

        return True
    except:
        traceback.print_exc()
        return False
