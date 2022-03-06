import shapely
import numpy as np
from twoaxistracking import plotting


def get_horizon_elevation_angle(azimuth, slope_azimuth, slope_tilt):
    """Calculate horizon elevation angle caused by a sloped field.

    Parameters
    ----------
    azimuth : float
        Azimuth angle for which the horizon elevation angle is to be calculated
        [degrees]
    slope_azimuth : float
        Direction of normal to slope on horizontal [degrees]
    slope_tilt : float
        Tilt of slope relative to horizontal [degrees]

    Returns
    -------
    horizon_elevation_angle : float
        Horizon elevation angle [degrees]
    """
    horizon_elevation_angle = np.rad2deg(np.arctan(
        - np.cos(np.deg2rad(slope_azimuth - azimuth))
        * np.tan(np.deg2rad(slope_tilt))))
    # Horizon elevation angle cannot be less than zero
    horizon_elevation_angle = np.clip(horizon_elevation_angle, a_min=0, a_max=None)
    return horizon_elevation_angle


def shaded_fraction(solar_elevation, solar_azimuth,
                    total_collector_geometry, active_collector_geometry,
                    min_tracker_spacing, tracker_distance, relative_azimuth,
                    relative_slope, slope_azimuth=0, slope_tilt=0,
                    max_elevation_angle=90, plot=False):
    """Calculate the shaded fraction for any layout of two-axis tracking collectors.

    Parameters
    ----------
    solar_elevation: float
        Solar elevation angle in degrees.
    solar_azimuth: float
        Solar azimuth angle in degrees.
    total_collector_geometry: Shapely Polygon
        Polygon corresponding to the total collector area.
    active_collector_geometry: Shapely Polygon or MultiPolygon
        One or more polygons defining the active collector area.
    min_tracker_spacing: float
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
        Direction of normal to slope on horizontal [degrees]. Used to determine
        horizon shading.
    slope_tilt : float
        Tilt of slope relative to horizontal [degrees]. Used to determine
        horizon shading.
    max_elevation_angle : float, optional
        The maximum elevation angle for which shading may occur. If the solar
        elevation angle is greater then the shaded fraction is set to zero.
    plot: bool, default: True
        Whether to plot the projected shadows and unshaded area.

    Returns
    -------
    shaded_fraction: float
        Shaded fraction for the specific solar position and field layout.
    """
    # If the sun is below the horizon, set the shaded fraction to nan
    if solar_elevation < 0:
        return np.nan
    # Set shaded fraction to 1 (fully shaded) if the solar elevation is below
    # the horizon line caused by the tilted ground
    elif solar_elevation <= get_horizon_elevation_angle(solar_azimuth, slope_azimuth, slope_tilt):
        return 1

    azimuth_difference = solar_azimuth - relative_azimuth

    # Create mask to only calculate shading for collectors within +/-90° view
    mask = np.where(np.cos(np.deg2rad(azimuth_difference)) > 0)

    xoff = tracker_distance[mask]*np.sin(np.deg2rad(azimuth_difference[mask]))
    yoff = - tracker_distance[mask] *\
        np.cos(np.deg2rad(azimuth_difference[mask])) * \
        np.sin(np.deg2rad(solar_elevation-relative_slope[mask])) / \
        np.cos(np.deg2rad(relative_slope[mask]))

    # Initialize the unshaded area as the collector active collector area
    unshaded_geometry = active_collector_geometry
    shading_geometries = []
    for i, (x, y) in enumerate(zip(xoff, yoff)):
        if np.sqrt(x**2+y**2) < min_tracker_spacing:
            # Project the geometry of the shading collector (total area) onto
            # the plane of the reference collector
            shading_geometry = shapely.affinity.translate(total_collector_geometry, x, y)  # noqa: E501
            # Update the unshaded area based on overlapping shade
            unshaded_geometry = unshaded_geometry.difference(shading_geometry)
            if plot:
                shading_geometries.append(shading_geometry)

    if plot:
        plotting._plot_shading(active_collector_geometry, unshaded_geometry,
                               shading_geometries, min_tracker_spacing)


    shaded_fraction = 1 - unshaded_geometry.area / active_collector_geometry.area
    return shaded_fraction
