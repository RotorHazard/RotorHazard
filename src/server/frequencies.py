import re

# Band/channel frequency table and lookups, shared by the server and (through the page layouts) the web pages

# frequencies in MHz by band and channel; lookups take the first match, so the order decides shared frequencies
BAND_CHANNEL_FREQUENCIES = {
    'R1': 5658, 'R2': 5695, 'R3': 5732, 'R4': 5769, 'R5': 5806, 'R6': 5843, 'R7': 5880, 'R8': 5917,
    'F1': 5740, 'F2': 5760, 'F3': 5780, 'F4': 5800, 'F5': 5820, 'F6': 5840, 'F7': 5860, 'F8': 5880,
    'E1': 5705, 'E2': 5685, 'E3': 5665, 'E4': 5645, 'E5': 5885, 'E6': 5905, 'E7': 5925, 'E8': 5945,
    'B1': 5733, 'B2': 5752, 'B3': 5771, 'B4': 5790, 'B5': 5809, 'B6': 5828, 'B7': 5847, 'B8': 5866,
    'A1': 5865, 'A2': 5845, 'A3': 5825, 'A4': 5805, 'A5': 5785, 'A6': 5765, 'A7': 5745, 'A8': 5725,
    'L1': 5362, 'L2': 5399, 'L3': 5436, 'L4': 5473, 'L5': 5510, 'L6': 5547, 'L7': 5584, 'L8': 5621,
    'U0': 5300, 'U1': 5325, 'U2': 5348, 'U3': 5366, 'U4': 5384, 'U5': 5402, 'U6': 5420, 'U7': 5438,
    'U8': 5456, 'U9': 5985, 'D1': 5660, 'D2': 5695, 'D3': 5735, 'D4': 5770, 'D5': 5805, 'D6': 5880,
    'D7': 5914, 'D8': 5839, 'J1': 5695, 'J2': 5770, 'J3': 5880, 'S1': 5660, 'S2': 5695, 'S3': 5735,
    'S4': 5770, 'S5': 5805, 'S6': 5839, 'S7': 5878, 'S8': 5914, 'O1': 5669, 'O2': 5705, 'O3': 5768,
    'O4': 5804, 'O5': 5839, 'O6': 5876, 'O7': 5912, 'Q1': 5677, 'Q2': 5794, 'Q3': 5902,
}

def band_channel_for(frequency):
    '''The (band, channel) of the first channel on the given frequency, or (None, None) when none matches.'''
    if frequency:
        for key, freq in BAND_CHANNEL_FREQUENCIES.items():
            if freq == frequency:
                match = re.fullmatch(r'([A-Za-z]+)([0-9]+)', key)
                return match.group(1), int(match.group(2))
    return None, None

def frequency_for(band, channel):
    '''The frequency of the given band and channel, or None when there is no such channel.'''
    return BAND_CHANNEL_FREQUENCIES.get('{}{}'.format(band, channel)) if band and channel is not None else None

def fill_missing_band_channels(freqs):
    '''Fills in band and channel, in a frequency-set dict, for seats whose frequency is a known channel; a missing
       band or channel (including zero padding) is set to None. Returns the indexes of the seats filled in.'''
    if not isinstance(freqs, dict) or not isinstance(freqs.get('f'), list):
        return []
    if not isinstance(freqs.get('b'), list):
        freqs['b'] = []
    if not isinstance(freqs.get('c'), list):
        freqs['c'] = []
    bands = freqs['b']
    channels = freqs['c']
    filled = []
    for idx, frequency in enumerate(freqs['f']):
        while len(bands) <= idx:
            bands.append(None)
        while len(channels) <= idx:
            channels.append(None)
        if bands[idx] in (None, 0, ''):  # channel alone is not tested, since 'U0' is channel 0
            band, channel = band_channel_for(frequency)
            if band is not None:
                filled.append(idx)
            bands[idx] = band
            channels[idx] = channel
    return filled
