
import os
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord


def find_linefree_freq(ms_name, vel_map, spw_dict,
                       vel_width=40 * u.km / u.s,
                       field_name='M33',
                       pb_size=0 * u.deg,
                       debug_printing=False):
    '''
    Use a velocity map (e.g., from HI) to define line-free channels
    in an MS.

    Parameters
    ----------
    ms_name : str
        Name of MS file to open.
    vel_map : spectral_cube.Projection
        Line velocity map to use extents from.
    spw_dict : dict
        Dictionary of SPWs numbers (as keys) and the
        rest frequency. Continuum SPWs can be set to
        the brightest line (e.g., CO) to exclude those
        channels.
    '''

    try:
        # CASA 6
        import casatools
        # iatool = casatools.image()
        tb = casatools.table()
    except ImportError:
        try:
            from taskinit import tbtool
            # iatool = iatool()
            tb = tbtool()
        except ImportError:
            raise ImportError("Could not import CASA (casac).")

    # Get channel frequencies.
    tb.open(os.path.join(ms_name, 'SPECTRAL_WINDOW'))
    chanfreqs = tb.getvarcol('CHAN_FREQ')
    tb.close()

    # Get science field positions to define enclosing box of mosaic.
    tb.open(os.path.join(ms_name, 'FIELD'))
    field_names = tb.getcol('NAME')
    phase_dirns = tb.getcol('PHASE_DIR').squeeze()
    tb.close()

    # Screen out non-science fields
    selected_fields = np.array([True if field_name in name else False
                                for name in field_names])
    ras, decs = (phase_dirns * u.rad).to(u.deg)

    ras = ras[selected_fields]
    decs = decs[selected_fields]

    pointings = SkyCoord(ras, decs, frame='icrs')

    # Make bounding box.

    min_ra = pointings.ra.min() - 0.5 * pb_size.to(u.deg)
    max_ra = pointings.ra.max() + 0.5 * pb_size.to(u.deg)
    min_dec = pointings.dec.min() - 0.5 * pb_size.to(u.deg)
    max_dec = pointings.dec.max() + 0.5 * pb_size.to(u.deg)

    vel_map_box = vel_map.subimage(ylo=min_dec, yhi=max_dec,
                                   xlo=max_ra, xhi=min_ra).to(u.km / u.s)

    if vel_map_box.ndim != 2:
        raise ValueError("Spatial slicing failed. Don't think this should happen?")

    linefree_range = dict.fromkeys(spw_dict.keys())

    for line_name in spw_dict:

        spw_props = spw_dict[line_name]

        spw_num = spw_props['spw_num']
        restfreq = spw_props['restfreq'].to(u.Hz)

        # Check if a velocity padding is defined
        if 'vel_pad' in spw_props:
            vel_pad = spw_props['vel_pad']
        else:
            vel_pad = vel_width

        if debug_printing:
            print('Velocity padding used for {0} is {1}'.format(spw_num,
                                                                vel_pad))

        # Get the channel frequencies
        key_name = "r{0}".format(int(spw_num) + 1)

        chanfreqs_spw = chanfreqs[key_name].squeeze() * u.Hz

        # Convert velocity extrema to freq.

        vel_min = np.nanmin(vel_map_box.quantity) - vel_pad.to(u.km / u.s) / 2.
        vel_max = np.nanmax(vel_map_box.quantity) + vel_pad.to(u.km / u.s) / 2.

        freq_min = vel_min.to(u.Hz, u.doppler_radio(restfreq))
        freq_max = vel_max.to(u.Hz, u.doppler_radio(restfreq))

        if debug_printing:
            print("Min velocity of spw {}".format(chanfreqs_spw.to(u.km / u.s, u.doppler_radio(restfreq)).min()))
            print("Max velocity of spw {}".format(chanfreqs_spw.to(u.km / u.s, u.doppler_radio(restfreq)).max()))
            print("Min velocity of line-free {}".format(vel_min))
            print("Max velocity of line-free {}".format(vel_max))

        # Switch if needed
        if freq_max < freq_min:
            freq_max, freq_min = freq_min, freq_max

        line_chans = np.logical_and(chanfreqs_spw > freq_min,
                                    chanfreqs_spw < freq_max)

        chan_min = np.where(line_chans)[0].min()
        chan_max = np.where(line_chans)[0].max()

        # Make the line-free channel ranges
        linefree_range[line_name] = []

        if debug_printing:
            print("Chan min/max for {0} are {1}/{2}".format(spw_num, chan_min,
                                                            chan_max))

        if chan_min > 0:
            lows = [0, chan_min]
            linefree_range[line_name].append(lows)

        if chan_max < chanfreqs_spw.size - 1:
            highs = [chan_max, chanfreqs_spw.size]
            linefree_range[line_name].append(highs)

    return linefree_range