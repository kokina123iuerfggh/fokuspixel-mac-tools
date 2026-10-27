"""Bildschirmbereich aufnehmen, ohne die eigenen schwebenden Fenster mit aufzunehmen (macOS).

Der Leuchtkreis liegt genau über dem Bereich, den er vergrößern soll. Eine normale Aufnahme
würde ihn also selbst mit abbilden. macOS kann stattdessen alles aufnehmen, was *unter* einem
bestimmten Fenster liegt. Das wird hier über die Systembibliotheken aufgerufen.
Auf anderen Systemen oder bei einem Fehler gibt es None zurück.
"""
import ctypes
import sys
from ctypes import c_char_p, c_double, c_long, c_size_t, c_uint32, c_void_p

from PySide6.QtGui import QImage

ON_SCREEN_BELOW_WINDOW = 1 << 2  # kCGWindowListOptionOnScreenBelowWindow
IMAGE_DEFAULT = 0  # kCGWindowImageDefault


class _CGRect(ctypes.Structure):
    _fields_ = [("x", c_double), ("y", c_double), ("width", c_double), ("height", c_double)]


class _Native:
    """Lädt die Systemfunktionen einmal. Scheitert das, bleibt die Aufnahme abgeschaltet."""

    def __init__(self):
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

        objc.sel_registerName.restype = c_void_p
        objc.sel_registerName.argtypes = [c_char_p]
        address = ctypes.cast(objc.objc_msgSend, c_void_p).value
        self.send_object = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p)(address)
        self.send_long = ctypes.CFUNCTYPE(c_long, c_void_p, c_void_p)(address)
        self.sel_window = objc.sel_registerName(b"window")
        self.sel_window_number = objc.sel_registerName(b"windowNumber")

        cg.CGWindowListCreateImage.restype = c_void_p
        cg.CGWindowListCreateImage.argtypes = [_CGRect, c_uint32, c_uint32, c_uint32]
        for name in ("CGImageGetWidth", "CGImageGetHeight", "CGImageGetBytesPerRow", "CGImageGetBitsPerPixel"):
            function = getattr(cg, name)
            function.restype = c_size_t
            function.argtypes = [c_void_p]
        cg.CGImageGetDataProvider.restype = c_void_p
        cg.CGImageGetDataProvider.argtypes = [c_void_p]
        cg.CGDataProviderCopyData.restype = c_void_p
        cg.CGDataProviderCopyData.argtypes = [c_void_p]
        cf.CFDataGetBytePtr.restype = c_void_p
        cf.CFDataGetBytePtr.argtypes = [c_void_p]
        cf.CFDataGetLength.restype = c_long
        cf.CFDataGetLength.argtypes = [c_void_p]
        cf.CFRelease.restype = None
        cf.CFRelease.argtypes = [c_void_p]
        self.cg = cg
        self.cf = cf

    def window_number(self, widget):
        view = int(widget.winId())
        window = self.send_object(view, self.sel_window)
        if not window:
            return 0
        return self.send_long(window, self.sel_window_number)

    def capture_below(self, window_number, rect):
        cg, cf = self.cg, self.cf
        bounds = _CGRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()))
        image_ref = cg.CGWindowListCreateImage(bounds, ON_SCREEN_BELOW_WINDOW, window_number, IMAGE_DEFAULT)
        if not image_ref:
            return None
        try:
            width = cg.CGImageGetWidth(image_ref)
            height = cg.CGImageGetHeight(image_ref)
            if width == 0 or height == 0 or cg.CGImageGetBitsPerPixel(image_ref) != 32:
                return None
            stride = cg.CGImageGetBytesPerRow(image_ref)
            data = cg.CGDataProviderCopyData(cg.CGImageGetDataProvider(image_ref))
            if not data:
                return None
            try:
                raw = ctypes.string_at(cf.CFDataGetBytePtr(data), cf.CFDataGetLength(data))
            finally:
                cf.CFRelease(data)
        finally:
            cf.CFRelease(image_ref)
        # macOS liefert BGRA mit vormultipliziertem Alpha, das entspricht diesem Qt-Format
        return QImage(raw, width, height, stride, QImage.Format.Format_ARGB32_Premultiplied).copy()


_native = None
_native_failed = False


def available():
    global _native, _native_failed
    if _native is None and not _native_failed:
        if sys.platform != "darwin":
            _native_failed = True
        else:
            try:
                _native = _Native()
            except Exception:  # Bibliothek fehlt oder Aufruf schlägt fehl
                _native_failed = True
    return _native is not None


def capture_below(widget, rect):
    """Bild des Bildschirmbereichs rect (in Bildschirmkoordinaten) ohne das Fenster widget und alles darüber.

    Gibt None zurück, wenn das auf diesem System nicht geht.
    """
    if not available():
        return None
    try:
        number = _native.window_number(widget)
        if not number:
            return None
        return _native.capture_below(number, rect)
    except Exception:
        return None
