
from __future__ import print_function

import re
import sys
import time
import errno
import logging

import nfc
import nfc.clf
import nfc.clf.pn53x


def main(args):
    if args["--debug"]:
        loglevel = logging.DEBUG - (1 if args["--verbose"] else 0)
        logging.getLogger("nfc.clf").setLevel(loglevel)

    try:
        time_to_return = time.time() + float(args['--time'])
    except ValueError as e:
        logging.error("while parsing '--time' " + str(e))
        sys.exit(-1)

    clf = nfc.ContactlessFrontend()
    if clf.open(args['--device']):
        try:
            assert isinstance(clf.device, nfc.clf.pn53x.Device), \
                "rfstate.py does only work with PN53x based devices"
            chipset = clf.device.chipset

            regs = [("CIU_FIFOLevel", 0b10000000)]  # clear fifo
            regs.extend(zip(25 * ["CIU_FIFOData"], bytearray(25)))
            regs.extend([
                ("CIU_Command", 0b00000001),  # Configure command
                ("CIU_Control", 0b00000000),  # act as target (b4=0)
                ("CIU_TxControl", 0b10000000),  # disable output on TX1/TX2
                ("CIU_TxAuto", 0b00100000),  # wake up when rf level detected
                ("CIU_CommIRq", 0b01111111),  # clear interrupt request bits
                ("CIU_DivIRq", 0b01111111),  # clear interrupt request bits
            ])
            chipset.write_register(*regs)

            if args["--verbose"]:
                time_t0 = time.time()
                chipset.read_register("CIU_Status1", "CIU_Status2")
                delta_t = time.time() - time_t0
                print("approx. %d samples/s" % int(1 / delta_t))

            status = chipset.read_register("CIU_Status1", "CIU_Status2")
            rfstate = "ON" if status[1] & 0b00100000 else "OFF"
            time_t0 = time.time()
            print("%.6f RF %s" % (time_t0, rfstate))

            while time.time() < time_to_return:
                status = chipset.read_register("CIU_Status1", "CIU_Status2")
                if rfstate == "OFF" and status[1] & 0x20 == 0x20:
                    rfstate = "ON"
                    time_t1 = time.time()
                    delta_t = time_t1 - time_t0
                    print("%.6f RF ON  after %.6f" % (time_t1, delta_t))
                    time_t0 = time_t1
                if rfstate == "ON" and status[1] & 0x20 == 0x00:
                    rfstate = "OFF"
                    time_t1 = time.time()
                    delta_t = time_t1 - time_t0
                    print("%.6f RF OFF after %.6f" % (time_t1, delta_t))
                    time_t0 = time_t1
        except nfc.clf.UnsupportedTargetError as error:
            print(repr(error))
        except IOError as error:
            if error.errno == errno.EIO:
                print("lost connection to local device")
            else:
                print(repr(error))
        except (NotImplementedError, AssertionError) as error:
            print(str(error))
        except KeyboardInterrupt:
            pass
        finally:
            clf.close()


if __name__ == '__main__':
    logging.basicConfig(format='%(relativeCreated)d ms [%(name)s] %(message)s')

    try:
        from docopt import docopt
    except ImportError:
        sys.exit("the 'docopt' module is needed to execute this program")

    # remove restructured text formatting before input to docopt
    usage = re.sub(r'(?<=\n)\*\*(\w+:)\*\*.*\n', r'\1', __doc__)
    sys.exit(main(docopt(usage)))
