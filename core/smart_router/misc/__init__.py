"""Smart Router 杂项模块

非核心功能，如运营、工具脚本等。
"""

from .coffee_qr import (
    QR_CODE_PATH,
    copy_to_clipboard,
    get_qr_code_path,
    open_image_system,
)

__all__ = [
    "QR_CODE_PATH",
    "copy_to_clipboard",
    "get_qr_code_path",
    "open_image_system",
]
