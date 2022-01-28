"""Functions for calculating Shading of two-axis tracking solar collectors.

.. codeauthor:: Adam R. Jensen<adam-r-j@hotmail.com>
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import EllipseCollection
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import matplotlib.colors as mcolors
from matplotlib import cm
import shapely


def _rotate_origin(x, y, rotation_deg):
    """Rotate a set of 2D points counterclockwise around the origin (0, 0)."""
    rotation_rad = np.deg2rad(rotation_deg)
    # Rotation is set negative to make counterclockwise rotation
    xx = x * np.cos(-rotation_rad) + y * np.sin(-rotation_rad)
    yy = -x * np.sin(-rotation_rad) + y * np.cos(-rotation_rad)
    return xx, yy


def _plot_field_layout(X, Y, Z, L_min):
    """Plot field layout."""
    norm = mcolors.Normalize(vmin=min(Z), vmax=max(Z))
    cmap = cm.viridis_r
    colors = cmap(norm(Z))
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'aspect': 'equal'})
    # Plot a circle with a diameter equal to L_min
    ax.add_collection(EllipseCollection(widths=L_min, heights=L_min,
                                        angles=0, units='xy',
                                        facecolors=colors,
                                        edgecolors=("black",),
                                        linewidths=(1,),
                                        offsets=list(zip(X, Y)),
                                        transOffset=ax.transData))
    # Similarly, add a circle for the origin
    ax.add_collection(EllipseCollection(widths=L_min, heights=L_min,
                                        angles=0, units='xy',
                                        facecolors='red',
                                        edgecolors=("black",),
                                        linewidths=(1,), offsets=[0, 0],
                                        transOffset=ax.transData))
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=0.8,
                 label='Relative tracker height (vertical)')
    ax.grid()
    ax.set_ylim(min(Y)-L_min, max(Y)+L_min)
    ax.set_xlim(min(X)-L_min, max(X)+L_min)


def generate_field_layout(gcr, collector_area, L_min, neighbor_order,
                          aspect_ratio=None, offset=None, rotation=None,
                          layout_type=None, slope_azimuth=0,
                          slope_tilt=0, plot=True):
    """
    Generate a regularly-spaced collector field layout.

    See [1]_ for examples on how to use the function. Field layout parameters
    and limits are described in [2]_.

    Notes
    -----
    The field layout can be specified either using selecting a standard layout
    using the layout_type argument or by specifying the individual layout
    parameters aspect_ratio, offset, and rotation. For both cases also the
    ground cover ratio needs to be specified.

    Any length unit can be used as long as the usage is consistent with the
    collector geometry.

    Parameters
    ----------
    gcr: float
        Ground cover ratio. Ratio of collector area to ground area.
    collector_area: float
        Surface area of one collector.
    L_min: float
        Minimum distance between collectors. Calculated as the maximum distance
        between any two points on the collector surface area.
    neighbor_order: int
        Order of neighbors to include in layout. neighbor_order=1 includes only
        the 8 directly adjacent collectors.
    aspect_ratio: float, optional
        Ratio of the spacing in the primary direction to the secondary.
    offset: float, optional
        Relative row offset in the secondary direction as fraction of the
        spacing in the secondary direction. -0.5 <= offset < 0.5.
    rotation: float, optional
        Counterclockwise rotation of the field [degrees]. 0 <= rotation < 180
    layout_type: {square, square_rotated, hexagon_e_w, hexagon_n_s}, optional
        Specification of the special layout type (only depend on gcr).
    slope_azimuth : float
        Direction of normal to slope on horizontal [degrees]
    slope_tilt : float
        Tilt of slope relative to horizontal [degrees]
    plot: bool, default: True
        Whether to plot the field layout.

    Returns
    -------
    X: array of floats
        Distance of neighboring trackers to the reference tracker in the east-
        west direction. East is positive.
    Y: array of floats
        Distance of neighboring trackers to the reference tracker in the north-
        south direction. North is positive.
    Z: array of floats
        Relative heights of neighboring trackers.
    tracker_distance: array of floats
        Distances between neighboring trackers and the reference tracker.
    relative_azimuth: array of floats
        Relative azimuth of neighboring trackers - measured clockwise from
        north [degrees].
    relative_slope: array of floats
        Slope between neighboring trackers and reference tracker. A positive
        slope means neighboring collector is higher than reference collector.

    References
    ----------
    .. [1] `GitHub repository for this code
       <https://github.com/AdamRJensen/two_axis_tracker_shading/>`_
    .. [2] `Shading and land use in regularly-spaced sun-tracking collectors, Cumpston & Pye.
       <https://doi.org/10.1016/j.solener.2014.06.012>`_
    """  # noqa: E501
    # Consider special layouts which can be defined only by GCR
    if layout_type == 'square':
        aspect_ratio = 1
        offset = 0
        rotation = 0
    # Diagonal layout is the square layout rotated 45 degrees
    elif layout_type == 'diagonal':
        aspect_ratio = 1
        offset = 0
        rotation = 45
    # Hexagonal layouts are defined by an aspect ratio=0.866 and offset=-0.5
    elif layout_type == 'hexagonal_n_s':
        aspect_ratio = np.sqrt(3)/2
        offset = -0.5
        rotation = 0
    # The hexagonal E-W layout is the hexagonal N-S layout rotated 90 degrees
    elif layout_type == 'hexagonal_e_w':
        aspect_ratio = np.sqrt(3)/2
        offset = -0.5
        rotation = 90
    elif layout_type is not None:
        raise ValueError('The layout type specified was not recognized.')
    elif ((aspect_ratio is None) or (offset is None) or (rotation is None)):
        raise ValueError('Aspect ratio, offset, and rotation needs to be '
                         'specified when no layout type has not been selected')

    # Check parameters are within their ranges
    if aspect_ratio < np.sqrt(1-offset**2):
        raise ValueError('Aspect ratio is too low and not feasible')
    if aspect_ratio > collector_area/(gcr*L_min**2):
        raise ValueError('Apsect ratio is too high and not feasible')
    if (offset < -0.5) | (offset >= 0.5):
        raise ValueError('The specified offset is outside the valid range.')
    if (rotation < 0) | (rotation >= 180):
        raise ValueError('The specified rotation is outside the valid range.')
    # Check if mimimum and maximum ground cover ratios are exceded
    gcr_max = collector_area / (L_min**2 * np.sqrt(1-offset**2))
    if (gcr < 0) or (gcr > gcr_max):
        raise ValueError('Maximum ground cover ratio exceded.')
    # Check if Lmin is physically possible given the collector area.
    if (L_min < np.sqrt(4*collector_area/np.pi)):
        raise ValueError('Lmin is not physically possible.')
    if (slope_azimuth >= 360) | (slope_azimuth < 0):
        raise ValueError('slope_azimuth is out of range (0-360)')
    if slope_tilt < 0:
        raise ValueError('slope_tilt has to be positive')
    elif slope_tilt > 20:
        raise Warning('A slope_tilt greater than 20 degrees is probably not'
                      'realistic')

    N = 1 + 2 * neighbor_order  # Number of collectors along each side

    # Generation of X and Y arrays with coordinates
    X = np.tile(np.arange(int(-N/2), int(N/2)+1), N)
    Y = np.repeat(np.arange(int(-N/2), int(N/2)+1), N)
    # Remove reference collector point (origin)
    X = np.delete(X, int(N**2/2))
    Y = np.delete(Y, int(N**2/2))

    # Add offset and implement aspect ratio. Note that it is important to first
    # calculate offset as it relies on the original X array.
    Y = Y + offset*X
    X = X * aspect_ratio
    # Apply field rotation
    X, Y = _rotate_origin(X, Y, rotation)
    # Calculate and apply the scaling factor based on GCR
    scaling = np.sqrt(collector_area / (gcr * aspect_ratio))
    X, Y = X*scaling, Y*scaling
    # Calculate relative tracker height based on surface slope
    Z = - X * np.sin(np.deg2rad(slope_azimuth)) * \
        np.tan(np.deg2rad(slope_tilt)) \
        - Y * np.cos(np.deg2rad(slope_azimuth)) * \
        np.tan(np.deg2rad(slope_tilt))
    # Calculate distance and angle of shading trackers relative to the center
    tracker_distance = np.sqrt(X**2 + Y**2)
    # The relative azimuth is defined clockwise eastwards from north
    relative_azimuth = np.mod(450-np.rad2deg(np.arctan2(Y, X)), 360)
    # Relative slope of collectors
    # positive means collector is higher than reference collector
    relative_slope = -np.cos(np.deg2rad(slope_azimuth - relative_azimuth)) * slope_tilt  # noqa: E501

    # Visualize layout
    if plot:
        _plot_field_layout(X, Y, Z, L_min)

    return X, Y, Z, tracker_distance, relative_azimuth, relative_slope


def two_axis_shading_fraction(solar_azimuth, solar_elevation,
                              collector_geometry, L_min, tracker_distance,
                              relative_azimuth, relative_slope,
                              slope_azimuth=0, slope_tilt=0, plot=False):
    """Calculate shading fraction for any layout of two-axis trackers.

    See [1]_ for examples on how to use the function.

    Parameters
    ----------
    solar_azimuth: float
        Solar azimuth angle in degrees.
    solar_elevation: float
        Solar elevation angle in degrees.
    collector_geometry: Shapely geometry object
        The collector aperture geometry.
    L_min: float
        Minimum distance between collectors. Used for selecting possible
        shading collectors.
    tracker_distance: array of floats
        Distances between neighboring trackers and reference tracker.
    relative_azimuth: array of floats
        Relative azimuth between neigboring trackers and reference tracker.
    relative_slope: array of floats
        Slope between neighboring trackers and reference tracker. A positive
        slope means neighboring collector is higher than reference collector.
    slope_azimuth : float
        Direction of normal to slope on horizontal [degrees].
    slope_tilt : float
        Tilt of slope relative to horizontal [degrees].
    plot: bool, default: True
        Whether to plot the projected shadows.

    Returns
    -------
    shading_fraction: float
        Shading fraction for the specific solar position, collector geometry,
        and field layout.

    References
    ----------
    .. [1] `GitHub repository for this code
       <https://github.com/AdamRJensen/two_axis_tracker_shading/>`_
    """  # noqa: E501
    # If the sun is below the horizon, set the shading fraction to nan
    if solar_elevation < 0:
        return np.nan
    # Set shading fraction to 1 (fully shaded) if the solar elevation is below
    # the horizon line caused by the tilted ground
    elif solar_elevation < \
            - np.cos(np.deg2rad(slope_azimuth-solar_azimuth)) * slope_tilt:
        return 1

    azimuth_difference = solar_azimuth - relative_azimuth

    # Create mask to only calculate shading for collectors within +/-90° view
    mask = np.where(np.cos(np.deg2rad(azimuth_difference)) > 0)

    xoff = tracker_distance[mask]*np.sin(np.deg2rad(azimuth_difference[mask]))
    yoff = - tracker_distance[mask] *\
        np.cos(np.deg2rad(azimuth_difference[mask])) * \
        np.sin(np.deg2rad(solar_elevation-relative_slope[mask])) / \
        np.cos(np.deg2rad(relative_slope[mask]))

    # Initialize the unshaded area as the collector area
    unshaded_area = collector_geometry
    shade_patches = []
    for i, (x, y) in enumerate(zip(xoff, yoff)):
        if np.sqrt(x**2+y**2) < L_min:
            # Project the geometry of the shading collector onto the plane
            # of the investigated collector
            shade_geometry = shapely.affinity.translate(collector_geometry, x, y)  # noqa: E501
            # Update the unshaded area based on overlapping shade
            unshaded_area = unshaded_area.difference(shade_geometry)
            if plot:
                shade_patches.append(Polygon(shade_geometry.exterior))

    shading_fraction = 1 - unshaded_area.area / collector_geometry.area

    if plot:
        shade_patches = PatchCollection(shade_patches, facecolor='blue',
                                        linewidth=0.5, alpha=0.5)
        collector_patch = PatchCollection(
            [Polygon(collector_geometry.exterior)],
            facecolor='red', linewidth=0.5, alpha=0.5)
        unshaded_patch = PatchCollection([Polygon(unshaded_area.exterior)],
                                         facecolor='green', linewidth=0.5,
                                         alpha=0.5)
        fig, ax = plt.subplots(1, 2, subplot_kw=dict(aspect='equal'))
        ax[0].add_collection(collector_patch, autolim=True)
        ax[0].add_collection(shade_patches, autolim=True)
        ax[1].add_collection(unshaded_patch, autolim=True)
        ax[0].set_xlim(-6, 6), ax[1].set_xlim(-6, 6)
        ax[0].set_ylim(-2, 2), ax[1].set_ylim(-2, 2)
        ax[0].set_title("Solar elevation: {:.1f}°".format(solar_elevation))
        ax[1].set_title("Shading fraction: {:.1f}%".format(
            shading_fraction*100))
        plt.show()

    return shading_fraction
