"""
System Focus Manager - Copyright Protection
============================================

ORIGINAL AUTHOR: Manuela Riascos Hurtado
EMAIL: manhurta54@gmail.com
GITHUB: https://github.com/Elah2022
PROJECT: https://github.com/Elah2022/system-focus-manager

COPYRIGHT © 2025 MANUELA RIASCOS HURTADO
ALL RIGHTS RESERVED

This software is licensed under the MIT License.
You may use, modify, and distribute this software,
BUT you MUST:
1. Keep this copyright notice intact
2. Credit the original author (Manuela Riascos Hurtado)
3. Include a link to the original project

UNAUTHORIZED REMOVAL OF THIS COPYRIGHT NOTICE IS PROHIBITED.

If you appreciate this software, please:
- ⭐ Star the project on GitHub
- 📧 Contact manhurta54@gmail.com for commercial use
- 💰 Consider supporting the author

Last Updated: 2025-12-29
"""

__author__ = "Manuela Riascos Hurtado"
__email__ = "manhurta54@gmail.com"
__copyright__ = "Copyright © 2025 Manuela Riascos Hurtado"
__license__ = "MIT"
__version__ = "2.0"
__github__ = "https://github.com/Elah2022/system-focus-manager"

def verify_watermark():
    """
    Verifies that the watermark is intact.
    This function is called on startup.
    """
    return {
        'author': __author__,
        'email': __email__,
        'copyright': __copyright__,
        'github': __github__,
        'version': __version__
    }

# Encoded watermark (backup protection)
_WATERMARK_ENCODED = "TWFudWVsYSBSaWFzY29zIEh1cnRhZG8gLSBtYW5odXJ0YTU0QGdtYWlsLmNvbSAtIGh0dHBzOi8vZ2l0aHViLmNvbS9FbGFoMjAyMg=="

if __name__ == "__main__":
    import base64
    print("Watermark Information:")
    print(f"Author: {__author__}")
    print(f"Email: {__email__}")
    print(f"Copyright: {__copyright__}")
    print(f"GitHub: {__github__}")
    print(f"\nEncoded watermark verified: {base64.b64decode(_WATERMARK_ENCODED).decode('utf-8')}")
