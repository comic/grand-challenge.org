import os
import numpy as np
import glob
import SimpleITK as sitk
from pathlib import Path
from app.tests.datasets_tests.screenshots_gen import draw_mask_tile_3view_lite, \
    windowing, VISUALIZATION_COLOR_TABLE


def test_draw_mask_tile_3view_lite(input_scan_path, input_prediction_path, output_path,
                                   title=("Segmentation", ), alpha=0.3,
                                   sparseness=200, duration=1200):
    """

    :param input_scan_path: a place to store scans in mhd format
    :param input_prediction_path: a place to store predictions in mhd format
    :param sparseness: controls sampling sparsity, e.g. 100 means, each 100x100x100 region has only 1 location sampled.
    :param output_path: output file locations.
    :param alpha: blending options for showing predictions on top of scans.
    :param duration: duration for each frame
    :return:
    """

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    scans_files = glob.glob(f'{input_scan_path}/**/*.mhd', recursive=True)
    preds_files = glob.glob(f'{input_prediction_path}/**/*.mhd', recursive=True)

    scans_file_maps = {Path(scan_file).stem: scan_file
         for idx, scan_file in enumerate(scans_files)}
    preds_files_maps = {Path(pred_file).stem: pred_file
         for idx, pred_file in enumerate(preds_files)}

    assert(len(scans_file_maps.keys()) == len(preds_files_maps.keys()))
    for file_key in scans_file_maps.keys():
        scan = sitk.GetArrayFromImage(sitk.ReadImage(scans_file_maps[file_key]))
        pred = sitk.GetArrayFromImage(sitk.ReadImage(preds_files_maps[file_key]))

        labels = np.unique(pred)[1:]
        path = os.path.join(output_path, file_key)
        if not os.path.exists(path):
            os.makedirs(path)
        # scans needs to be windowed, default window is (-1150, 350), windowing gives a graylevel image(0, 255)
        # all unique labels will be drawn except background-0.
        # axial, sagital and coronal views will be drawn for each location which will be sampled based on pred > 0
        # which is the foreground region in pred. Sparseness parameter controls how many locations will be sampled.
        # sparseness 200 means that in each 200x200x200 region, there will be only one location sampled.
        draw_mask_tile_3view_lite(windowing(scan).astype(np.uint8),
                                  [[pred == label for label in labels]],
                                  pred > 0, sparseness,
                                  path,
                                  colors=
                                  [VISUALIZATION_COLOR_TABLE[n] for n in range(len(labels))],
                                  thickness=[-1] * len(labels), alpha=alpha,
                                  titles=title, duration=duration)


if __name__ == "__main__":
    output_path = "resources/tmp/"
    input_scan_path = "resources/scans/"
    input_prediction_path = "resources/pred/"
    test_draw_mask_tile_3view_lite(input_scan_path, input_prediction_path, output_path)