import imageio

import pandas as pd
import numpy as np


def make_image(filepath, dest_filepath):
    df = pd.read_csv(filepath, header=None)
    arr = df.values
    arr = np.interp(arr, (arr.min(), arr.max()), (0, 65536))
    arr = arr.astype(np.uint16)
    imageio.imwrite(dest_filepath, arr)


if __name__ == '__main__':
    make_image('6519.txt', 'heightfield.png')