import numpy as np
import cv2
import os
from PIL import Image

VISUALIZATION_COLOR_TABLE = [
    (0, 0, 255),
    (0, 255, 0),
    (255, 0, 0),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (100, 0, 0),
    (100, 100, 0),
    (100, 100, 100),
    (50, 200, 0),
    (50, 200, 200),
    (50, 50, 200),
    (200, 50, 200),
    (50, 200, 50),
]


def windowing(image, from_span=(-1150, 350), to_span=(0, 255)):
    image = np.copy(image)
    if from_span is None:
        min_input = np.min(image)
        max_input = np.max(image)
    else:
        min_input = from_span[0]
        max_input = from_span[1]
    image[image < min_input] = min_input
    image[image > max_input] = max_input
    image = ((image - min_input) / float(max_input - min_input)) * (to_span[1] - to_span[0]) + to_span[0]
    return image


def padding(img, size, pad_center=None):
    if pad_center is None:
        pad_center = np.asarray(img.shape) // 2

    padding = tuple([(max(0, si // 2 - cc),
                      max(0, cc + si - si // 2 - sh))
                     for sh, si, cc in zip(img.shape, size, pad_center)])
    img = np.pad(img, padding, mode='constant', constant_values=np.min(img))
    assert (img.shape == tuple(size))
    return img


def sliding_over_region(proposal_mask, output_resolution, overlaps):
    proposal_mask_coors = np.asarray(np.where(proposal_mask > 0))
    tls, brs = np.min(proposal_mask_coors, axis=1), np.max(proposal_mask_coors, axis=1)
    slices = tuple([slice(tl + o // 2, br - o // 2, int(o * (1 - ol)))
                    for tl, br, o, ol in zip(tls, brs, output_resolution, overlaps)])
    spans = tuple(np.append(np.arange(ss.start, ss.stop, ss.step), ss.stop) for ss in slices)
    g = np.meshgrid(*spans, sparse=False)
    grid = np.vstack([gg.ravel() for gg in g]).T
    return grid


def mask_sparsity_filtering(mask, block_size, overlap):
    newmask = np.zeros_like(mask, dtype=bool)
    dense_coords = sliding_over_region(mask, [block_size] * mask.ndim, [overlap] * mask.ndim)
    for coor in dense_coords:
        set_slice = tuple([slice(n - block_size // 2, n + block_size - block_size // 2) for n in coor])
        if len(set_slice) != 3:
            continue
        hit_coords = np.where(mask[set_slice] > 0)
        if len(hit_coords[0]) > 0:
            one_coord = np.asarray(coor) - block_size // 2 + np.asarray(np.where(mask[set_slice] > 0)).T[0]
            newmask[tuple(one_coord)] = True
    return newmask

def draw_2d(image_2d, masks_2d, colors, thickness, alpha=0.5):
    original = np.dstack((image_2d, image_2d, image_2d))
    blending = np.dstack((image_2d, image_2d, image_2d))

    for mask, color, thick in zip(masks_2d, colors, thickness):
        _, contours, _ = cv2.findContours(mask.astype(np.uint8).copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(blending, contours, -1, color, thick)

    return original * (1 - alpha) + blending * alpha


def draw_mask_tile_3view_lite(image, masks_list, coord_mask, sparseness, output_path, colors,
                              thickness, alpha=0.5, flip_axis=0, draw_anchor=True, anchor_color=(0, 255, 0),
                              titles=None, title_offset=50, title_color=(0, 255, 0), duration=1500, loop=0,
                              output_name='out.gif'):
    """

    :param image: a 3d gray level image (0-255)
    :param masks_list: a list of list of mask images, each mask is a 3d binary image. the function will
    draw multiple rows, first row shows the image, second rows to the last will be masks.
    :param coord_mask: used to sample drawing locations, only drawing
    locations inside objects in coord_mask(coord_mask > 0)
    :param sparseness: controls sampling sparsity, e.g. 100 means, each 100x100x100 region has only 1 location sampled.
    :param output_path: output file locations.
    :param colors:
    :param thickness:
    :param alpha:
    :param flip_axis: default = 0, we flip z axis by default.
    :param draw_anchor: draw locations where the slices are sampled from.
    :param anchor_color: default anchor color is green.
    :param titles: explanation about the screenshots.
    :param title_offset:
    :param title_color:
    :param duration: gif duration for each frame
    :param loop: loop to show gif or not, default is 0, meaning yes.
    :param output_name: specify output file name
    :return:
    """
    assert (all([image.shape == mask.shape for mask_list in masks_list for mask in mask_list]))
    num_mask_group = len(masks_list)
    num_mask_sub_group = len(masks_list[0])
    pad_size = [max(image.shape)] * image.ndim
    if flip_axis is not None:
        image = np.flip(image, axis=flip_axis)
        coord_mask = np.flip(coord_mask, axis=flip_axis)
        m_shape = np.asarray(masks_list).shape
        masks_list = np.asarray([np.flip(mask, axis=flip_axis)
                                 for mask_list in masks_list for mask in mask_list]).reshape(m_shape)
    if np.sum(coord_mask) > 0:
        sparse_mask = mask_sparsity_filtering(coord_mask > 0, sparseness, 0)
    else:
        return

    show_images = []
    for pc in np.asarray(np.where(sparse_mask > 0)).T:
        multiview_image = np.hstack([padding(np.moveaxis(image, n, -1)[..., pc[n]], pad_size[:2])
                                     for n in range(image.ndim)])

        image_tile = np.tile(multiview_image, [num_mask_group + 1, 1])
        mask_tile_array = np.zeros((num_mask_sub_group,) + image_tile.shape, dtype=np.uint8)
        for l_id in range(num_mask_group):
            for m_id in range(num_mask_sub_group):
                mask_tile_array[m_id, pad_size[0] * (l_id + 1):pad_size[0] * (l_id + 2), ::] = \
                    np.hstack([padding(np.moveaxis(masks_list[l_id][m_id], n, -1)[..., pc[n]], pad_size[:2])
                               for n in range(image.ndim)])

        rendered_image = draw_2d(image_tile, mask_tile_array, colors, thickness, alpha=alpha)
        if draw_anchor:
            anchor_mask = np.zeros((pad_size[0], pad_size[0], pad_size[0]), dtype=np.uint8)
            anchor_slices = tuple([slice(pcc - 3 + (ps - ims) // 2, pcc + 3 + (ps - ims) // 2)
                                   for pcc, ims, ps in zip(pc, image.shape, pad_size)])
            anchor_mask[anchor_slices] = 1
            multiview_anchor_mask = np.hstack(
                [np.moveaxis(anchor_mask, n, -1)[..., pc[n] + (pad_size[n] - image.shape[n]) // 2]
                 for n in range(anchor_mask.ndim)])
            rendered_image[:pad_size[0], ...] = draw_2d(multiview_image,
                                                        [multiview_anchor_mask], colors=[anchor_color],
                                                        thickness=[-2], alpha=1.0)
        if titles:
            assert (len(titles) == len(masks_list))
            cv2.putText(rendered_image, 'Original', (title_offset, title_offset), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, title_color, 2, cv2.LINE_AA)
            for idx, title in enumerate(titles):
                cv2.putText(rendered_image, title, (title_offset, pad_size[0] * (idx + 1) + title_offset),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, title_color, 2, cv2.LINE_AA)
        # if output_path:
        #     cv2.imwrite(os.path.join(output_path, '{}.{}'.format(pc, ext)), rendered_image)
        show_images.append(Image.fromarray(rendered_image.astype(np.uint8)))
    if output_path:
        # fourcc = cv2.VideoWriter_fourcc(*'MP4V')
        # writer = cv2.VideoWriter(os.path.join(output_path, 'out.mp4'), fourcc, fps,
        #                          show_images[0].shape[:2], True)
        # for frame in show_images:
        #     writer.write(frame)
        #
        # writer.release()
        show_images[0].save(os.path.join(output_path, output_name), save_all=True,
                            append_images=show_images[1:], duration=duration, loop=loop)



