# Utility to display version and build-timestamp strings in RotorHazard node firmware '.bin' file
#
# Example Usage:
#
# cd ~/RotorHazard/src
# python -m server.util.rhBinInfo http://www.rotorhazard.com/fw/rel/current/RH_S32_BPill_node.bin
#

import sys

from server import RHUtils, RHInterface
from . import stm32loader as stm32loader

def showFirmwareBinInfo(fileStr):
    dataStr = None
    try:
        dataStr = stm32loader.load_source_file(fileStr, False)
    except Exception as ex:
        print("Error reading file '{}' in 'check_bpillfw_file()': {}".format(fileStr, ex))
        return
    try:
        rStr = RHUtils.findPrefixedSubstring(dataStr, RHInterface.FW_VERSION_PREFIXSTR, \
                                             RHInterface.FW_TEXT_BLOCK_SIZE)
        fwVerStr = rStr if rStr else "(unknown)"
        rStr = RHUtils.findPrefixedSubstring(dataStr, RHInterface.FW_PROCTYPE_PREFIXSTR, \
                                             RHInterface.FW_TEXT_BLOCK_SIZE)
        fwTypStr = (rStr + ", ") if rStr else ""
        rStr = RHUtils.findPrefixedSubstring(dataStr, RHInterface.FW_BUILDDATE_PREFIXSTR, \
                                             RHInterface.FW_TEXT_BLOCK_SIZE)
        if rStr:
            fwTimStr = rStr
            rStr = RHUtils.findPrefixedSubstring(dataStr, RHInterface.FW_BUILDTIME_PREFIXSTR, \
                                                 RHInterface.FW_TEXT_BLOCK_SIZE)
            if rStr:
                fwTimStr += " " + rStr
        else:
            fwTimStr = "unknown"
        print("Firmware file version: {} ({}Build timestamp: {})".format(fwVerStr, fwTypStr, fwTimStr))
    except Exception:
        print("Error processing file '{}' in 'check_bpillfw_file()'".format(fileStr))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        showFirmwareBinInfo(sys.argv[1])
    else:
        print("Missing filename parameter")
