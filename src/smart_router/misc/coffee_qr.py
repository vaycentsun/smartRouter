"""赞助二维码生成和显示模块"""

import io
from pathlib import Path
from typing import Optional

try:
    import qrcode
    from PIL import Image as PILImage
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


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


def generate_short_url_qr(url: str, filename: str = "sponsor") -> Optional[Path]:
    """生成短链接二维码（用于支付宝/微信收款）
    
    Args:
        url: 短链接 URL
        filename: 输出文件名
        
    Returns:
        生成的二维码路径
    """
    if not QR_AVAILABLE:
        return None
    
    try:
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # 生成图片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存到临时目录
        import tempfile
        output_path = Path(tempfile.gettempdir()) / f"{filename}_qr.png"
        img.save(output_path)
        
        return output_path
    except Exception:
        return None


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

# 默认的赞助链接（用户可以替换为自己的）
# 支持支付宝、微信、PayPal 等任何链接
DEFAULT_SPONSOR_LINK = "https://github.com/sponsors"  # 默认使用 GitHub Sponsors

# 二维码图片保存路径
QR_CODE_PATH = Path(__file__).parent / "assets" / "coffee_qr.png"


def generate_qr_code(data: Optional[str] = None, save_path: Optional[Path] = None) -> Optional[Path]:
    """生成二维码图片
    
    Args:
        data: 二维码内容（URL 或文本），默认使用 DEFAULT_SPONSOR_LINK
        save_path: 保存路径，默认使用 QR_CODE_PATH
        
    Returns:
        生成的图片路径，如果失败返回 None
    """
    if not QR_AVAILABLE:
        return None
    
    data = data or DEFAULT_SPONSOR_LINK
    save_path = save_path or QR_CODE_PATH
    
    # 确保目录存在
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # 创建二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # 生成图片
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(save_path)
        
        return save_path
    except Exception:
        return None


def get_qr_code_path() -> Optional[Path]:
    """获取二维码图片路径
    
    如果二维码不存在，尝试生成一个默认的
    
    Returns:
        图片路径，如果不存在返回 None
    """
    # 首先检查是否已有二维码
    if QR_CODE_PATH.exists():
        return QR_CODE_PATH
    
    # 检查 assets 目录下是否有其他二维码图片
    assets_dir = Path(__file__).parent / "assets"
    if assets_dir.exists():
        for ext in ["*.png", "*.jpg", "*.jpeg"]:
            files = list(assets_dir.glob(ext))
            if files:
                return files[0]
    
    # 尝试生成默认二维码
    return generate_qr_code()


def generate_ascii_qr(data: Optional[str] = None) -> str:
    """生成 ASCII 艺术二维码（无需外部库）
    
    Args:
        data: 二维码内容
        
    Returns:
        ASCII 艺术字符串
    """
    if not QR_AVAILABLE:
        # 简单的 ASCII 咖啡杯作为占位符
        return '''
        ☕ 请作者喝一杯咖啡 ☕
        
           ( (
            ) )
          ........
          |      |]
          \\      /
           `----'
        
    感谢您的支持！
        '''
    
    data = data or DEFAULT_SPONSOR_LINK
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # 生成 ASCII 表示
        lines = []
        modules = qr.modules
        for row in modules:
            line = ""
            for cell in row:
                line += "██" if cell else "  "
            lines.append(line)
        
        return "\n".join(lines)
    except Exception:
        return "二维码生成失败"
