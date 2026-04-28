"""Smart Router 杂项模块

非核心功能，如运营、工具脚本等。
"""

from .coffee_qr import get_qr_code_path, QR_CODE_PATH, open_image_system, copy_to_clipboard

__all__ = [
    "get_qr_code_path",
    "QR_CODE_PATH",
    "open_image_system",
    "copy_to_clipboard",
]
