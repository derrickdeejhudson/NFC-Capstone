import nfc
import listen
import sense
import rfstate

clf = nfc.ContactlessFrontend('usb')


if __name__ == '__main__':

    assert clf.open('usb:001:006') is True    # open device 9 on bus 3
    assert clf.open('usb:054c:02e1') is True  # open first ACR122U
    assert clf.open('usb:003') is True        # open first Reader on bus 3
    clf.connect(rdwr={})
    True

    clf.close()  # previous open calls implicitly closed the device

    try:
        from docopt import docopt
    except ImportError:
        sys.exit("the 'docopt' module is needed to execute this program")

    usage = re.sub(r'(?<=\n)\*\*(\w+:)\*\*.*\n', r'\1', __doc__)
    sys.exit(main(docopt(usage)))
