from PIL import Image
import win32clipboard
from io import BytesIO
import sys

def copy_image_to_clipboard(image_path):
    img = Image.open(image_path)
    output = BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # Remove BMP header
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()
    print('Image copied to clipboard!')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python copy_image.py <image_path>')
        sys.exit(1)
    copy_image_to_clipboard(sys.argv[1])
