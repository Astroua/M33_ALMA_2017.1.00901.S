
'''
Useful numbers to have handy
'''

import astropy.units as u

distance = 840 * u.kpc


def ang_to_phys(ang_size, distance=distance):
    '''
    Convert from angular to physical scales
    '''
    return (ang_size.to(u.rad).value * distance).to(u.pc)


co21_freq = 230.538 * u.GHz
thirtco21_freq = 220.3986842 * u.GHz

line_dict = {"12co": co21_freq,
             "13co": thirtco21_freq}

co21_mass_conversion = 6.7 * (u.Msun / u.pc ** 2) / (u.K * u.km / u.s)
beam_eff_30m_druard = 56 / 92.
