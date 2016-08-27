__author__ = 'christina'

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math as m

TILT_RANGE = np.arange(-60, 65, 5)
TILT_RANGE_E = np.arange(-60, 0, 5)
TILT_RANGE_W = np.arange(0, 65, 5)

def get_block_geometry():
    # define a coordinate system for the NCU block, with origin at the NCU
    n_subblocks = int(raw_input('Number of sub blocks = '))
    n_sb_rows = int(raw_input('Number of rows in a sub block = '))
    L_row = float(raw_input('Row length (m) = '))
    W_row = float(raw_input('Row width (m) = '))
    W_road = float(raw_input('Road width between sub blocks (m) = '))
    x_NCU = float(raw_input('NCU distance from 1st SPC, x (m) = '))
    y_NCU = float(raw_input('NCU distance from 1st SPC, y (m) = '))
    L_panel = float(raw_input('Panel length (m) = '))

    x_panel = 0.5 * L_panel * np.cos(np.radians(TILT_RANGE))  # should be negative for neg tilt angle?
    z_panel = np.abs(0.5 * L_panel * np.sin(np.radians(TILT_RANGE)))  # z values should always be positive

    # Generate block mesh:
    x_coords = np.linspace(-1*x_NCU, -1*x_NCU + n_sb_rows * W_row, num=n_sb_rows, endpoint=True)
    y_coords = np.linspace(-1*y_NCU, -1*y_NCU - n_subblocks * (L_row + W_road), num=n_subblocks, endpoint=True)
    xx, yy = np.meshgrid(x_coords, y_coords)


    return h - z_panel
