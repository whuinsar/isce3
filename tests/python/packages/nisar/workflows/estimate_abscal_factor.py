import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest
from numpy.typing import ArrayLike

import isce3
import iscetest
import nisar
from nisar.workflows.estimate_abscal_factor import estimate_abscal_factor


def get_test_data(bandwidth: str = "20mhz") -> Dict[str, Any]:
    """Get corner reflector and RSLC data for testing."""
    datadir = Path(iscetest.data) / "abscal"
    cr_csv = datadir / "REE_CORNER_REFLECTORS_INFO.csv"
    rslc_hdf5 = datadir / f"calib_slc_pass1_{bandwidth}.h5"

    # Parse corner reflector CSV file and RSLC HDF5 file.
    corner_reflectors = isce3.cal.parse_triangular_trihedral_cr_csv(cr_csv)

    # Get RSLC product image data.
    rslc = nisar.products.readers.SLC(hdf5file=os.fspath(rslc_hdf5))
    freq = "A"
    pol = "HH"
    img_dataset = rslc.getSlcDataset(freq, pol)
    img_data = nisar.types.ComplexFloat16Decoder(img_dataset)

    # Get product metadata.
    orbit = rslc.getOrbit()
    radar_grid = rslc.getRadarGrid(freq)
    native_doppler = rslc.getDopplerCentroid(freq)

    # NISAR data is focused to zero-Doppler.
    image_grid_doppler = isce3.core.LUT2d()

    # Corner reflector LLH positions are referenced to WGS 84 ellipsoid.
    ellipsoid = isce3.core.WGS84_ELLIPSOID

    return dict(
        corner_reflectors=corner_reflectors,
        img_data=img_data,
        orbit=orbit,
        radar_grid=radar_grid,
        native_doppler=native_doppler,
        image_grid_doppler=image_grid_doppler,
        ellipsoid=ellipsoid,
    )


def get_triangular_trihedral_cr_peak_rcs(
    side_length: float, wavelength: float
) -> float:
    """
    Compute the maximum RCS, in meters^2, of a triangular trihedral corner reflector.
    """
    return 4.0 * np.pi * side_length ** 4 / (3 * wavelength ** 2)


def pow2db(x: ArrayLike) -> np.ndarray:
    """Convert a power quantity from linear units to decibels (dB)."""
    return 10.0 * np.log10(x)


@pytest.mark.parametrize("bandwidth", ["5mhz", "20mhz"])
def test_predict_triangular_trihedral_cr_rcs(bandwidth):
    d = get_test_data(bandwidth)

    for cr in d["corner_reflectors"]:
        # Compute predicted RCS.
        predicted_rcs = isce3.cal.predict_triangular_trihedral_cr_rcs(
            cr=cr,
            orbit=d["orbit"],
            doppler=d["native_doppler"],
            wavelength=d["radar_grid"].wavelength,
            look_side=d["radar_grid"].lookside,
        )
        predicted_rcs_db = pow2db(predicted_rcs)

        # Get maximum RCS for the corner reflector.
        peak_rcs = get_triangular_trihedral_cr_peak_rcs(
            cr.side_length, d["radar_grid"].wavelength
        )
        peak_rcs_db = pow2db(peak_rcs)

        # These corner reflectors were simulated such that their boresight was aligned
        # with the line-of-sight vector. The predicted RCS for each corner reflector
        # should therefore be close to the peak RCS (within .001 dB).
        assert np.isclose(predicted_rcs_db, peak_rcs_db, rtol=0.0, atol=1e-3)


class TestMeasureTargetRCS:
    @pytest.mark.parametrize("peak_find_domain", ["time", "freq"])
    def test_measure_target_rcs(self, peak_find_domain: str):
        d = get_test_data()

        def measure_rcs_db(cr: isce3.cal.TriangularTrihedralCornerReflector) -> float:
            rcs = isce3.cal.measure_target_rcs(
                target_llh=cr.llh,
                img_data=d["img_data"],
                radar_grid=d["radar_grid"],
                orbit=d["orbit"],
                doppler=d["image_grid_doppler"],
                ellipsoid=d["ellipsoid"],
                nchip=4,
                upsample_factor=128,
                peak_find_domain=peak_find_domain,
            )
            return pow2db(rcs)

        # Get the apparent RCS of each corner reflector.
        rcs_values_db = np.asarray(
            [measure_rcs_db(cr) for cr in d["corner_reflectors"]]
        )
        assert len(rcs_values_db) == 3

        # Check that the RCS of each corner reflector is approximately equal
        # (within 0.1 dB).
        max_rcs_db = np.max(rcs_values_db)
        min_rcs_db = np.min(rcs_values_db)
        assert np.isclose(max_rcs_db, min_rcs_db, atol=0.1)

    def test_out_of_bounds(self):
        d = get_test_data()

        # Get LLH position of a target just outside of the image grid bounds.
        llh = isce3.geometry.rdr2geo(
            aztime=d["radar_grid"].sensing_mid,
            range=d["radar_grid"].end_range + d["radar_grid"].range_pixel_spacing,
            orbit=d["orbit"],
            side=d["radar_grid"].lookside,
            doppler=0.0,
            wavelength=d["radar_grid"].wavelength,
            ellipsoid=d["ellipsoid"],
        )

        # Check that an exception was raised.
        errmsg = (
            "target position in radar coordinates was outside of the supplied image"
            " grid"
        )
        with pytest.raises(RuntimeError, match=errmsg):
            isce3.cal.measure_target_rcs(
                target_llh=isce3.core.LLH(*llh),
                img_data=d["img_data"],
                radar_grid=d["radar_grid"],
                orbit=d["orbit"],
                doppler=d["image_grid_doppler"],
                ellipsoid=d["ellipsoid"],
            )

    def test_near_border(self):
        d = get_test_data()

        # Get LLH position of a target just *inside* of the image grid bounds, but too
        # close to the image border to extract a chip for upsampling.
        llh = isce3.geometry.rdr2geo(
            aztime=d["radar_grid"].sensing_mid,
            range=d["radar_grid"].end_range - d["radar_grid"].range_pixel_spacing,
            orbit=d["orbit"],
            side=d["radar_grid"].lookside,
            doppler=0.0,
            wavelength=d["radar_grid"].wavelength,
            ellipsoid=d["ellipsoid"],
        )

        # Check that an exception was raised.
        errmsg = "target is too close to image border -- consider reducing nchip"
        with pytest.raises(RuntimeError, match=errmsg):
            isce3.cal.measure_target_rcs(
                target_llh=isce3.core.LLH(*llh),
                img_data=d["img_data"],
                radar_grid=d["radar_grid"],
                orbit=d["orbit"],
                doppler=d["image_grid_doppler"],
                ellipsoid=d["ellipsoid"],
            )


@pytest.mark.parametrize("bandwidth", ["5mhz", "20mhz"])
def test_estimate_abscal_factor(bandwidth):
    datadir = Path(iscetest.data) / "abscal"
    cr_csv = datadir / "REE_CORNER_REFLECTORS_INFO.csv"
    rslc_hdf5 = datadir / f"calib_slc_pass1_{bandwidth}.h5"

    # Parse corner reflector CSV file and RSLC HDF5 file.
    corner_reflectors = list(isce3.cal.parse_triangular_trihedral_cr_csv(cr_csv))

    # Get RSLC product.
    rslc = nisar.products.readers.SLC(hdf5file=os.fspath(rslc_hdf5))
    freq = "A"
    pol = "HH"

    abscal_info = estimate_abscal_factor(
        corner_reflectors=corner_reflectors,
        rslc=rslc,
        freq=freq,
        pol=pol,
        nchip=4,
        upsample_factor=128,
    )

    # Check the "id" field of the output JSON-like data.
    cr_ids_expected = [cr.id for cr in corner_reflectors]
    cr_ids = [d["id"] for d in abscal_info]
    assert cr_ids == cr_ids_expected

    # Check that the estimated absolute radiometric calibration factor for each corner
    # reflector is approximately the same.
    abscal_factors_db = np.asarray(
        [pow2db(d["absolute_calibration_factor"]) for d in abscal_info]
    )
    max_abscal_db = np.max(abscal_factors_db)
    min_abscal_db = np.min(abscal_factors_db)
    assert np.isclose(max_abscal_db, min_abscal_db, atol=0.15)

    orbit = rslc.getOrbit()

    def orbit_contains(t: isce3.core.DateTime) -> bool:
        return (t >= orbit.start_datetime) and (t <= orbit.end_datetime)

    # Check that the "timestamp" falls within the span of the orbit data included in the
    # RSLC product.
    cr_times = [d["timestamp"] for d in abscal_info]
    assert all(map(orbit_contains, cr_times))

    # Check the "frequency" and "polarization" fields.
    assert all(d["frequency"] == freq for d in abscal_info)
    assert all(d["polarization"] == pol for d in abscal_info)
