"""Copy image to Windows clipboard using ctypes (no external dependencies)"""
import ctypes
from ctypes import wintypes
from PIL import Image
from io import BytesIO
import sys

# Windows API constants
CF_DIB = 8

# Load Windows DLLs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Define function signatures
OpenClipboard = user32.OpenClipboard
OpenClipboard.argtypes = [wintypes.HWND]
OpenClipboard.restype = wintypes.BOOL

CloseClipboard = user32.CloseClipboard
CloseClipboard.argtypes = []
CloseClipboard.restype = wintypes.BOOL

EmptyClipboard = user32.EmptyClipboard
EmptyClipboard.argtypes = []
EmptyClipboard.restype = wintypes.BOOL

SetClipboardData = user32.SetClipboardData
SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
SetClipboardData.restype = wintypes.HANDLE

GlobalAlloc = kernel32.GlobalAlloc
GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
GlobalAlloc.restype = wintypes.HGLOBAL

GlobalLock = kernel32.GlobalLock
GlobalLock.argtypes = [wintypes.HGLOBAL]
GlobalLock.restype = wintypes.LPVOID

GlobalUnlock = kernel32.GlobalUnlock
GlobalUnlock.argtypes = [wintypes.HGLOBAL]
GlobalUnlock.restype = wintypes.BOOL

GMEM_MOVEABLE = 0x0002

def copy_image_to_clipboard(image_path):
    # Load image and convert to BMP format
    img = Image.open(image_path)
    output = BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # Remove BMP file header (14 bytes)
    output.close()
    
    # Allocate global memory
    h_mem = GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not h_mem:
        raise Exception("Failed to allocate global memory")
    
    # Lock memory and copy data
    p_mem = GlobalLock(h_mem)
    if not p_mem:
        raise Exception("Failed to lock global memory")
    
    ctypes.memmove(p_mem, data, len(data))
    GlobalUnlock(h_mem)
    
    # Open clipboard and set data
    if not OpenClipboard(None):
        raise Exception("Failed to open clipboard")
    
    try:
        EmptyClipboard()
        if not SetClipboardData(CF_DIB, h_mem):
            raise Exception("Failed to set clipboard data")
        print("Image copied to clipboard successfully!")
    finally:
        CloseClipboard()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python copy_image_ctypes.py <image_path>')
        sys.exit(1)
    copy_image_to_clipboard(sys.argv[1])
