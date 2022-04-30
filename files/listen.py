
from __future__ import print_function

import os
import re
import sys
import struct
import time
import errno
import logging
from binascii import hexlify

import nfc
import nfc.clf


def main(args):
    if args['--debug']:
        loglevel = logging.DEBUG - (1 if args['--verbose'] else 0)
        logging.getLogger("nfc.clf").setLevel(loglevel)
        logging.getLogger().setLevel(loglevel)

    try:
        try:
            waittime = float(args['--wait'])
        except ValueError:
            assert 0, "the '--wait T' argument must be a number"
        assert waittime >= 0, "the '--wait T' argument must be positive"
        try:
            timeout = float(args['--time'])
        except ValueError:
            assert 0, "the '--time T' argument must be a number"
        assert timeout >= 0, "the '--time T' argument must be positive"
    except AssertionError as error:
        print(str(error), file=sys.stderr)
        return 2

    try:
        clf = nfc.ContactlessFrontend(args['--device'])
    except IOError:
        print("no device found on path %r" % args['--device'], file=sys.stderr)
        return 3

    try:
        while True:
            target = None
            try:
                if args['tt2']:
                    target = listen_tta(timeout, clf, args)
                if args['tt3']:
                    target = listen_ttf(timeout, clf, args)
                if args['tt4']:
                    target = listen_tta(timeout, clf, args)
                if args['dep']:
                    target = listen_dep(timeout, clf, args)
                if target:
                    print("{0} {1}".format(time.strftime("%X"), target))
            except nfc.clf.CommunicationError as error:
                if args['--verbose']:
                    logging.error("%r", error)
            except AssertionError as error:
                print(str(error), file=sys.stderr)
                return 2

            if args['--repeat']:
                time.sleep(waittime)
            else:
                return 0 if target is not None else 1

    except nfc.clf.UnsupportedTargetError as error:
        logging.error("%r", error)
        return 2

    except IOError as error:
        if error.errno != errno.EIO:
            logging.error("%r", error)
        else:
            logging.error("lost connection to local device")
        return 3

    except KeyboardInterrupt:
        pass

    finally:
        clf.close()


def listen_tta(timeout, clf, args):
    try:
        bitrate = (int(args['--bitrate']) if args['--bitrate'] else 106)
    except ValueError:
        assert 0, "the '--bitrate' argument must be an integer"
    assert bitrate >= 0, "the '--bitrate' argument must be a positive integer"

    try:
        uid = bytearray.fromhex(args['--uid'])
    except ValueError:
        assert 0, "the '--uid' argument must be hexadecimal"
    assert len(uid) in (4, 7, 10), "the '--uid' must be 4, 7, or 10 bytes"

    target = nfc.clf.LocalTarget(str(bitrate) + 'A')
    target.sens_res = bytearray(b"\x01\x01")
    target.sdd_res = uid
    target.sel_res = bytearray(b"\x00" if args['tt2'] else b"\x20")

    target = clf.listen(target, timeout)

    if target and target.tt2_cmd:
        logging.debug("rcvd TT2_CMD %s", hexlify(target.tt2_cmd).decode())

        # Verify that we can send a response.
        if target.tt2_cmd == b"\x30\x00":
            data = bytearray.fromhex("046FD536 11127A00 79C80000 E110060F")
        elif target.tt2_cmd[0] == 0x30:
            data = bytearray(16)
        else:
            logging.warning("communication not verified")
            return target

        try:
            clf.exchange(data, timeout=1)
            return target
        except nfc.clf.CommunicationError:
            logging.error("communication failure after activation")

    if target and target.tt4_cmd:
        logging.debug("rcvd TT4_CMD %s", hexlify(target.tt4_cmd).decode())
        logging.warning("communication not verified")
        return target


def listen_ttf(timeout, clf, args):
    try:
        bitrate = (int(args['--bitrate']) if args['--bitrate'] else 212)
    except ValueError:
        assert 0, "the '--bitrate' argument must be an integer"
    assert bitrate >= 0, "the '--bitrate' argument must be a positive integer"

    try:
        idm = bytearray.fromhex(args['--idm'][0:16])
    except ValueError:
        assert 0, "the '--idm' argument must be hexadecimal"
    idm += os.urandom(8 - len(idm))

    try:
        pmm = bytearray.fromhex(args['--pmm'][0:16])
    except ValueError:
        assert 0, "the '--pmm' argument must be hexadecimal"
    pmm += (8 - len(pmm)) * b"\xFF"

    try:
        _sys = bytearray.fromhex(args['--sys'][0:4])
    except ValueError:
        assert 0, "the '--sys' argument must be hexadecimal"
    _sys += (2 - len(_sys)) * b"\xFF"

    target = nfc.clf.LocalTarget(str(bitrate) + 'F')
    target.sensf_res = b"\x01" + idm + pmm + _sys

    target = clf.listen(target, timeout)

    if target and target.tt3_cmd:
        if target.tt3_cmd[0] == 0x06:
            response = struct.pack("B", 29) + b"\7" + idm + b"\0\0\1" + \
                bytearray(16)
            clf.exchange(response, timeout=0)
        elif target.tt3_cmd[0] == 0x0C:
            response = struct.pack("B", 13) + b"\x0D" + idm + b"\x01" + _sys
        else:
            logging.warning("communication not verified")
            return target

        try:
            clf.exchange(response, timeout=1)
            return target
        except nfc.clf.CommunicationError:
            logging.error("communication failure after activation")


def listen_dep(timeout, clf, args):
    try:
        id3 = bytearray.fromhex(args['--id3'][0:20])
    except ValueError:
        assert 0, "the '--id3' argument must be hexadecimal"
    id3 += os.urandom(10 - len(id3))

    try:
        gbt = bytearray.fromhex(args['--gbt'])
    except ValueError:
        assert 0, "the '--gbt' argument must be hexadecimal"

    target = nfc.clf.LocalTarget()
    target.sensf_res = bytearray.fromhex("01") + id3[0:8] + bytearray(10)
    target.sens_res = bytearray.fromhex("0101")
    target.sdd_res = bytearray.fromhex("08") + id3[-3:]
    target.sel_res = bytearray.fromhex("60" if args['--hce'] else "40")
    target.atr_res = b"\xD5\x01" + id3 + b"\0\0\0\x08" + (
        b"\x32" if gbt else b"\0") + gbt

    target = clf.listen(target, timeout)
    if target and target.dep_req:
        logging.debug("rcvd DEP_REQ %s", hexlify(target.dep_req).decode())

        # Verify that we can indeed send a response. Note that we do
        # not handle a DID, but nobody is sending them anyway. Further
        # note that target.dep_req is without the frame length byte
        # but exchange() works on frames and so it has to be added.
        if target.dep_req.startswith(b"\xD4\x06\x80"):
            # older phones start with attention
            dep_res = bytearray.fromhex("04 D5 07 80")
        elif target.dep_req.startswith(b"\xD4\x06\x00"):
            # newer phones send information packet
            dep_res = bytearray.fromhex("06 D5 07 00 00 00")
        else:
            logging.warning("communication not verified")
            return target

        logging.debug("send DEP_RES %s",
                      hexlify(memoryview(dep_res)[1:]).decode())
        try:
            data = clf.exchange(dep_res, timeout=1)
            assert data and data[0] == len(data)
        except (nfc.clf.CommunicationError, AssertionError):
            logging.error("communication failure after activation")
            return None

        logging.debug("rcvd DEP_REQ %s",
                      hexlify(memoryview(data)[1:]).decode())
        mode = "passive" if target.sens_res or target.sensf_res else "active"
        logging.debug("activated in %s communication mode", mode)
        return target


if __name__ == '__main__':
    logging.basicConfig(format='%(relativeCreated)d ms [%(name)s] %(message)s')

    try:
        from docopt import docopt
    except ImportError:
        sys.exit("the 'docopt' module is needed to execute this program")

    # remove restructured text formatting before input to docopt
    usage = re.sub(r'(?<=\n)\*\*(\w+:)\*\*.*\n', r'\1', __doc__)
    sys.exit(main(docopt(usage)))
