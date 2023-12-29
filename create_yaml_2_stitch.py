import os
from typing import List

import yaml
from imagesize import imagesize
from natsort import natsort
from tqdm import tqdm

RATIO_PX_UM = 7.8


def get_grid_origin(img_name_list: List) -> [int, int]:
    """
    Get start position of the grid thanks to the filenames of each picture.
    :param img_name_list: list of images filenames.
    Images filenames have this type of format : {x_position}_{y_position}.{extension_file}. Extension file is almost
    always "jpg".
    :return: position from start in the grid acquisition. The start position is the top-left corner position of the
    grid. The returned position is defined as two integers, the first is the abscissa of the start position and the
    second the ordinate.
    """
    # start position can be retrieved with *natsorted* function because it is the position at top-left corner of the
    # grid, so with the minimum x and the minimum y
    first_picture = natsort.natsorted(img_name_list)[0]
    first_picture_without_ext = first_picture.split(".")[0]
    x_origin, y_origin = first_picture_without_ext.split("_")
    return int(x_origin), int(y_origin)


def get_x_y_from_filename(img_name: str) -> [int, int]:
    """
    Get x and y coordinates from filename.
    :param img_name: Image filename has this type of format : {x_position}_{y_position}.{extension_file}. Extension file
    is almost always "jpg".
    :return: position where the picture was acquired. This position is returned as a list of two integers: the first is
    the abscissa and the second, the ordinate (in microscope coordinates format).
    """
    img_name_without_ext = img_name.split(".")[0]
    x, y = img_name_without_ext.split("_")
    return int(x), int(y)


def get_img_list_from_folder(folder_path: str) -> List[str]:
    """
    Get list of image filenames in a folder. To know if the files are pictures, the filenames are filtered by their
    extension.
    :param folder_path: folder where image filenames are extracted.
    :return: list of image filenames lying in the folder sent as parameter
    """
    img_name_list = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            img_name_list.append(filename)
    return img_name_list


def create_zeta_input_yaml(path_folder_tiles: str, ratio_px_um: float, yaml_filename: str="input_zeta.yaml") -> None:
    """
    Create zeta input yaml file which enables to get all pictures used to use stitching function from *zetastitcher*.
    :param path_folder_tiles: Folder where tiles are lying
    :param ratio_px_um: number of pixels in one µm (this number has been calculated from calibration)
    :param yaml_filename: name of yaml file created by this function
    """
    # get list of pictures in the folder
    img_list = get_img_list_from_folder(folder_path=path_folder_tiles)
    # get origin of the grid -> xy position of the top-left corner tile in the grid
    x_origin, y_origin = get_grid_origin(img_list)

    # data which has to be written in the output file
    data = {"filematrix": []}

    # iterate through all the tiles
    for img_name in tqdm(natsort.natsorted(img_list)):
        # get xy position of the current tile
        x, y = get_x_y_from_filename(img_name)
        # compute the position without offset of the xy position of the top-left corner tile in the grid and in the
        # pixel referential (and not in the referential of the micro-meter)
        x_position = round((x - x_origin) * ratio_px_um)
        y_position = round((y - y_origin) * ratio_px_um)

        # get the absolute path of the current analyzed tile
        absolute_path_file = os.path.join(path_folder_tiles, img_name)
        # get size of the current tile
        width_image, height_image = imagesize.get(absolute_path_file)

        # add definition of the current tile in the input yaml file
        file_object = {"X": x_position,
                       "Y": y_position,
                       "Z": 0,
                       "filename": absolute_path_file,
                       "nfrms": 1,
                       "xsize": width_image,
                       "ysize": height_image}
        data["filematrix"].append(file_object)

    # write definitions of all tiles in a yaml file
    input_yaml = os.path.join(path_folder_tiles, yaml_filename)
    with open(input_yaml, 'w') as file:
        yaml.dump(data, file)


path_folder_tiles = r"C:\Users\tristan_cotte\Pictures\Stitching\test_new_device\from_vai"

if __name__ == "__main__":
    create_zeta_input_yaml(path_folder_tiles=path_folder_tiles, ratio_px_um=RATIO_PX_UM)
