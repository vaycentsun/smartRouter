"""赞助二维码显示模块"""

import base64
import io
from pathlib import Path
from typing import Optional


def display_image_terminal(image_path: Path, width: int = 300) -> bool:
    """尝试在终端中直接显示图片
    
    支持多种终端类型：
    - iTerm2 (macOS) - inline image protocol
    - kitty - icat protocol
    - 支持 Sixel 的终端
    - 通用工具 (chafa, catimg, viu)
    
    Args:
        image_path: 图片路径
        width: 显示宽度（像素）
        
    Returns:
        是否成功显示
    """
    import os
    import sys
    import shutil
    import subprocess
    
    try:
        # 1. 检测 kitty 终端 (使用 icat)
        if os.environ.get("TERM") == "xterm-kitty" or shutil.which("kitty"):
            try:
                result = subprocess.run(
                    ["kitty", "+kitten", "icat", "--align", "center", str(image_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except:
                pass
        
        # 2. 检测 iTerm2 (macOS) - inline image protocol
        if os.environ.get("TERM_PROGRAM") == "iTerm.app":
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
                encoded = base64.b64encode(image_data).decode()
                
                # iTerm2 图片协议
                # width=300px 控制显示大小
                sys.stdout.write(f"\033]1337;File=inline=1;width={width}px:{encoded}\007\n")
                sys.stdout.flush()
                return True
            except:
                pass
        
        # 3. 尝试使用 chafa (最通用的终端图片查看器)
        if shutil.which("chafa"):
            try:
                # 计算合适的终端尺寸
                cols = min(40, os.get_terminal_size().columns // 2)
                result = subprocess.run(
                    ["chafa", f"--size={cols}x{cols}", str(image_path)],
                    capture_output=False,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except:
                pass
        
        # 4. 尝试使用 catimg
        if shutil.which("catimg"):
            try:
                result = subprocess.run(
                    ["catimg", "-w", "80", str(image_path)],
                    capture_output=False,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except:
                pass
        
        # 5. 尝试使用 viu
        if shutil.which("viu"):
            try:
                result = subprocess.run(
                    ["viu", "-w", "40", str(image_path)],
                    capture_output=False,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except:
                pass
        
        # 6. 尝试使用 imgcat (iTerm2 的工具)
        if shutil.which("imgcat"):
            try:
                result = subprocess.run(
                    ["imgcat", str(image_path)],
                    capture_output=False,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except:
                pass
                
    except Exception:
        pass
    
    return False


def open_image_terminal(image_path: Path) -> bool:
    """兼容旧版本的别名"""
    return display_image_terminal(image_path)


def open_image_system(image_path: Path) -> bool:
    """使用系统默认程序打开图片
    
    Args:
        image_path: 图片路径
        
    Returns:
        是否成功打开
    """
    import platform
    import subprocess
    import os
    
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(image_path)], check=True)
            return True
        elif system == "Linux":
            subprocess.run(["xdg-open", str(image_path)], check=True)
            return True
        elif system == "Windows":
            os.startfile(str(image_path))
            return True
            
    except Exception:
        pass
    
    return False


def copy_to_clipboard(text: str) -> bool:
    """复制文本到剪贴板
    
    Args:
        text: 要复制的文本
        
    Returns:
        是否成功复制
    """
    import platform
    import subprocess
    
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif system == "Linux":
            subprocess.run(["xclip", "-selection", "clipboard"], 
                         input=text.encode(), check=True)
            return True
        elif system == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True)
            return True
            
    except Exception:
        pass
    
    return False


QR_CODE_PATH = Path(__file__).parent / "assets" / "coffee_qr.png"


def get_qr_code_path() -> Optional[Path]:
    """获取赞助二维码图片路径
    
    Returns:
        静态二维码图片路径
    """
    if QR_CODE_PATH.exists():
        return QR_CODE_PATH
    return None