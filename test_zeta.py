from typing import Union

import cv2
import matplotlib.pyplot as plt
import numpy as np

from zetastitcher import FileMatrix, VirtualFusedVolume
from zetastitcher.align.__main__ import Runner


def transform_vfv2image(path_vfv_file: Union[str, FileMatrix]) -> np.ndarray:
    """
    Transform VirtualFusedVolume created by ZetaStitcher library to stitched picture. VirtualFusedVolume class takes as
    entry the path of yaml file. This file is created by align.Runner() class. The yaml file remembers the filepath of
    all pictures and their location (in X, Y and Z axis) in the stitched picture.
    Because we took shot at optimal Z, we only have one shot by XY position. Therefore, we have to wrap all the pictures
    at the same height (same Z) -> flat picture and return it as numpy array format.
    :param path_vfv_file: path of file taken as entry of VirtualFusedVolume class. VirutalFusedVolume enables to access
    portions of your volume programmatically.
    :return: RGB stitched picture.
    """
    vfv = VirtualFusedVolume(path_vfv_file)

    result = np.zeros(vfv[0].transpose(1, 2, 0).shape, dtype=int)

    for idx in range(vfv.shape[0]):
        layer = vfv[idx].transpose(1, 2, 0)
        possibility_to_add = np.less(result.astype(bool), layer.astype(bool))

        np.add(result, layer, where=possibility_to_add, out=result)

    return cv2.cvtColor(result.astype(np.float32), cv2.COLOR_BGR2RGB)


def stitch_folder_tiles(folder_path: str) -> FileMatrix:
    """
    Function which enables to create FileMatrix object referencing all filenames and their locations.
    This FileMatrix object enables to use the *fuse* function from *zetastitcher* creating the warped picture.
    :param folder_path: folder where tiles are lying.
    :return: FileMatrix object used to fuse tiles
    """
    output_file = "stitch_tmp.yml"
    nb_cpus = 8

    d = {'input_folder': folder_path, 'output_file': output_file, 'channel': None, 'max_dx': 100, 'max_dy': 100,
         'max_dz': 1, 'z_samples': 1, 'z_stride': None, 'overlap_v': 819, 'overlap_h': 979,
         'ascending_tiles_x': True, 'ascending_tiles_y': True, 'px_size_xy': 1,
         'px_size_z': 1, 'n_of_workers': int(nb_cpus / 4), 'recursive': False, 'equal_shape': True}

    r = Runner()

    for key, value in d.items():
        setattr(r, key, value)

    fm = r.run(return_fm=True)
    return fm


if __name__ == "__main__":
    path_folder_zeta = r"C:\Users\tristan_cotte\Pictures\Stitching\test_new_device\zeta_jpg"

    fm = stitch_folder_tiles(folder_path=path_folder_zeta)
    img_rgb = transform_vfv2image(path_vfv_file=fm)
    cv2.imwrite("test.jpg", img_rgb)
    plt.imshow(img_rgb.astype(int))
    plt.show()
