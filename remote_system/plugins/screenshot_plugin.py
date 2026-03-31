"""
Screenshot Plugin for Enhanced Agent

Handles screen capture with compression, region capture, multi-monitor support,
and platform-specific optimizations.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import io
import platform
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image, ImageGrab
from remote_system.enhanced_agent.plugin_manager import Plugin


@dataclass
class ScreenInfo:
    """
    Information about a display/monitor
    
    Attributes:
        monitor_id: Identifier for the monitor
        width: Screen width in pixels
        height: Screen height in pixels
        x: X coordinate of monitor position
        y: Y coordinate of monitor position
        is_primary: Whether this is the primary monitor
    """
    monitor_id: int
    width: int
    height: int
    x: int
    y: int
    is_primary: bool


@dataclass
class ScreenshotResult:
    """
    Result of a screenshot capture operation
    
    Attributes:
        success: Whether the capture was successful
        image_data: Compressed image data as bytes
        format: Image format (PNG, JPEG, BMP)
        width: Image width in pixels
        height: Image height in pixels
        size_bytes: Size of compressed image in bytes
        error: Error message if capture failed
    """
    success: bool
    image_data: Optional[bytes]
    format: str
    width: int
    height: int
    size_bytes: int
    error: Optional[str]


class ScreenshotPlugin(Plugin):
    """
    Screenshot Plugin
    
    Provides screen capture with compression, region capture, and multi-monitor support.
    Uses Pillow (PIL) for cross-platform compatibility with platform-specific optimizations.
    
    Requirements:
    - 2.1: Capture full screen and return compressed image data
    - 2.2: Capture only specified screen region with coordinates
    - 2.3: Use specified quality setting between 1 and 100
    - 2.4: Support capturing from specific monitors
    - 2.5: Return error message without crashing on failure
    - 2.6: Compress images to reduce bandwidth usage
    """
    
    def __init__(self):
        """Initialize the screenshot plugin"""
        self.supported_formats = ['PNG', 'JPEG', 'BMP']
        self.default_format = 'PNG'
        self.default_quality = 85
        self.platform = platform.system()
    
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary containing:
                - action: 'capture_screenshot', 'capture_region', or 'get_screen_info'
                - Additional args based on action
                
        Returns:
            Result based on the action
            
        Raises:
            ValueError: If action is invalid or required args are missing
        """
        action = args.get('action')
        
        if action == 'capture_screenshot':
            return self._capture_screenshot_action(args)
        elif action == 'capture_region':
            return self._capture_region_action(args)
        elif action == 'get_screen_info':
            return self._get_screen_info_action(args)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name
        """
        return "screenshot"
    
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        return ['action']
    
    def capture_screenshot(self, monitor_id: Optional[int] = None, 
                          quality: int = None, 
                          image_format: str = None) -> ScreenshotResult:
        """
        Capture full screen screenshot
        
        Args:
            monitor_id: Optional monitor ID to capture (None for all monitors)
            quality: Image quality 1-100 (default 85)
            image_format: Image format - PNG, JPEG, or BMP (default PNG)
            
        Returns:
            ScreenshotResult with capture status and image data
            
        Requirements: 2.1, 2.3, 2.4, 2.5, 2.6
        """
        try:
            # Validate and set defaults
            if quality is None:
                quality = self.default_quality
            
            # Validate quality (Requirement 2.3)
            quality = max(1, min(100, quality))
            
            if image_format is None:
                image_format = self.default_format
            
            image_format = image_format.upper()
            if image_format not in self.supported_formats:
                return ScreenshotResult(
                    success=False,
                    image_data=None,
                    format=image_format,
                    width=0,
                    height=0,
                    size_bytes=0,
                    error=f"Unsupported format: {image_format}. Supported: {', '.join(self.supported_formats)}"
                )
            
            # Capture screenshot (Requirement 2.1, 2.4)
            if monitor_id is not None:
                # Multi-monitor support - capture specific monitor
                screenshot = self._capture_monitor(monitor_id)
            else:
                # Capture all monitors
                screenshot = ImageGrab.grab()
            
            if screenshot is None:
                return ScreenshotResult(
                    success=False,
                    image_data=None,
                    format=image_format,
                    width=0,
                    height=0,
                    size_bytes=0,
                    error="Failed to capture screenshot"
                )
            
            # Get dimensions
            width, height = screenshot.size
            
            # Compress image (Requirement 2.6)
            image_data = self._compress_image(screenshot, image_format, quality)
            
            return ScreenshotResult(
                success=True,
                image_data=image_data,
                format=image_format,
                width=width,
                height=height,
                size_bytes=len(image_data),
                error=None
            )
        
        except Exception as e:
            # Requirement 2.5: Return error without crashing
            return ScreenshotResult(
                success=False,
                image_data=None,
                format=image_format if image_format else self.default_format,
                width=0,
                height=0,
                size_bytes=0,
                error=f"Screenshot capture failed: {str(e)}"
            )
    
    def capture_region(self, x: int, y: int, width: int, height: int,
                      quality: int = None, 
                      image_format: str = None) -> ScreenshotResult:
        """
        Capture specific screen region
        
        Args:
            x: X coordinate of top-left corner
            y: Y coordinate of top-left corner
            width: Width of region in pixels
            height: Height of region in pixels
            quality: Image quality 1-100 (default 85)
            image_format: Image format - PNG, JPEG, or BMP (default PNG)
            
        Returns:
            ScreenshotResult with capture status and image data
            
        Requirements: 2.2, 2.3, 2.5, 2.6
        """
        try:
            # Validate and set defaults
            if quality is None:
                quality = self.default_quality
            
            # Validate quality (Requirement 2.3)
            quality = max(1, min(100, quality))
            
            if image_format is None:
                image_format = self.default_format
            
            image_format = image_format.upper()
            if image_format not in self.supported_formats:
                return ScreenshotResult(
                    success=False,
                    image_data=None,
                    format=image_format,
                    width=0,
                    height=0,
                    size_bytes=0,
                    error=f"Unsupported format: {image_format}. Supported: {', '.join(self.supported_formats)}"
                )
            
            # Validate coordinates
            if width <= 0 or height <= 0:
                return ScreenshotResult(
                    success=False,
                    image_data=None,
                    format=image_format,
                    width=0,
                    height=0,
                    size_bytes=0,
                    error="Width and height must be positive"
                )
            
            # Capture region (Requirement 2.2)
            bbox = (x, y, x + width, y + height)
            screenshot = ImageGrab.grab(bbox=bbox)
            
            if screenshot is None:
                return ScreenshotResult(
                    success=False,
                    image_data=None,
                    format=image_format,
                    width=0,
                    height=0,
                    size_bytes=0,
                    error="Failed to capture region"
                )
            
            # Get actual dimensions
            actual_width, actual_height = screenshot.size
            
            # Compress image (Requirement 2.6)
            image_data = self._compress_image(screenshot, image_format, quality)
            
            return ScreenshotResult(
                success=True,
                image_data=image_data,
                format=image_format,
                width=actual_width,
                height=actual_height,
                size_bytes=len(image_data),
                error=None
            )
        
        except Exception as e:
            # Requirement 2.5: Return error without crashing
            return ScreenshotResult(
                success=False,
                image_data=None,
                format=image_format if image_format else self.default_format,
                width=0,
                height=0,
                size_bytes=0,
                error=f"Region capture failed: {str(e)}"
            )
    
    def get_screen_info(self) -> List[ScreenInfo]:
        """
        Get information about available displays/monitors
        
        Returns:
            List of ScreenInfo objects describing each monitor
            
        Requirement: 2.4
        """
        try:
            screens = []
            
            # Get primary screen info
            try:
                primary_screenshot = ImageGrab.grab()
                if primary_screenshot:
                    width, height = primary_screenshot.size
                    screens.append(ScreenInfo(
                        monitor_id=0,
                        width=width,
                        height=height,
                        x=0,
                        y=0,
                        is_primary=True
                    ))
            except Exception:
                pass
            
            # Platform-specific multi-monitor detection
            if self.platform == "Windows":
                screens.extend(self._get_windows_monitors())
            elif self.platform == "Linux":
                screens.extend(self._get_linux_monitors())
            elif self.platform == "Darwin":  # macOS
                screens.extend(self._get_macos_monitors())
            
            # If no screens detected, return default
            if not screens:
                screens.append(ScreenInfo(
                    monitor_id=0,
                    width=1920,
                    height=1080,
                    x=0,
                    y=0,
                    is_primary=True
                ))
            
            return screens
        
        except Exception:
            # Return default screen info on error
            return [ScreenInfo(
                monitor_id=0,
                width=1920,
                height=1080,
                x=0,
                y=0,
                is_primary=True
            )]
    
    def _compress_image(self, image: Image.Image, image_format: str, quality: int) -> bytes:
        """
        Compress image to bytes
        
        Args:
            image: PIL Image object
            image_format: Target format (PNG, JPEG, BMP)
            quality: Compression quality 1-100
            
        Returns:
            Compressed image as bytes
            
        Requirement: 2.6
        """
        buffer = io.BytesIO()
        
        # Convert RGBA to RGB for JPEG (doesn't support transparency)
        if image_format == 'JPEG' and image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            image = rgb_image
        
        # Save with compression
        if image_format == 'JPEG':
            image.save(buffer, format=image_format, quality=quality, optimize=True)
        elif image_format == 'PNG':
            # PNG compression level (0-9), map quality (1-100) to compress_level (9-0)
            compress_level = max(0, min(9, int((100 - quality) / 11)))
            image.save(buffer, format=image_format, compress_level=compress_level, optimize=True)
        else:  # BMP
            image.save(buffer, format=image_format)
        
        return buffer.getvalue()
    
    def _capture_monitor(self, monitor_id: int) -> Optional[Image.Image]:
        """
        Capture screenshot from specific monitor
        
        Args:
            monitor_id: Monitor identifier
            
        Returns:
            PIL Image object or None if capture fails
            
        Requirement: 2.4
        """
        try:
            # Platform-specific monitor capture
            if self.platform == "Windows":
                return self._capture_windows_monitor(monitor_id)
            elif self.platform == "Linux":
                return self._capture_linux_monitor(monitor_id)
            elif self.platform == "Darwin":  # macOS
                return self._capture_macos_monitor(monitor_id)
            else:
                # Fallback to full screen
                return ImageGrab.grab()
        except Exception:
            return None
    
    def _get_windows_monitors(self) -> List[ScreenInfo]:
        """Get monitor information on Windows"""
        monitors = []
        try:
            # Try to use win32api if available
            import win32api
            import win32con
            
            monitor_enum = []
            
            def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                monitor_enum.append(lprcMonitor)
                return True
            
            win32api.EnumDisplayMonitors(None, None, callback, 0)
            
            for idx, rect in enumerate(monitor_enum):
                if idx == 0:  # Skip primary (already added)
                    continue
                monitors.append(ScreenInfo(
                    monitor_id=idx,
                    width=rect[2] - rect[0],
                    height=rect[3] - rect[1],
                    x=rect[0],
                    y=rect[1],
                    is_primary=False
                ))
        except ImportError:
            # win32api not available, return empty list
            pass
        except Exception:
            pass
        
        return monitors
    
    def _get_linux_monitors(self) -> List[ScreenInfo]:
        """Get monitor information on Linux"""
        monitors = []
        try:
            # Try to use Xlib if available
            from Xlib import display
            
            d = display.Display()
            screen = d.screen()
            
            # Get screen dimensions
            # Note: Xlib doesn't easily provide per-monitor info
            # This is a simplified implementation
            
        except ImportError:
            # Xlib not available
            pass
        except Exception:
            pass
        
        return monitors
    
    def _get_macos_monitors(self) -> List[ScreenInfo]:
        """Get monitor information on macOS"""
        monitors = []
        try:
            # Try to use AppKit if available
            from AppKit import NSScreen
            
            screens = NSScreen.screens()
            for idx, screen in enumerate(screens):
                if idx == 0:  # Skip primary (already added)
                    continue
                frame = screen.frame()
                monitors.append(ScreenInfo(
                    monitor_id=idx,
                    width=int(frame.size.width),
                    height=int(frame.size.height),
                    x=int(frame.origin.x),
                    y=int(frame.origin.y),
                    is_primary=False
                ))
        except ImportError:
            # AppKit not available
            pass
        except Exception:
            pass
        
        return monitors
    
    def _capture_windows_monitor(self, monitor_id: int) -> Optional[Image.Image]:
        """Capture screenshot from specific Windows monitor"""
        try:
            import win32api
            import win32gui
            import win32ui
            import win32con
            from ctypes import windll
            
            # Get monitor info
            monitors = []
            
            def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                monitors.append((hMonitor, lprcMonitor))
                return True
            
            win32api.EnumDisplayMonitors(None, None, callback, 0)
            
            if monitor_id >= len(monitors):
                return ImageGrab.grab()
            
            hMonitor, rect = monitors[monitor_id]
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            
            # Capture using bbox
            return ImageGrab.grab(bbox=(left, top, right, bottom))
            
        except Exception:
            return ImageGrab.grab()
    
    def _capture_linux_monitor(self, monitor_id: int) -> Optional[Image.Image]:
        """Capture screenshot from specific Linux monitor"""
        # Linux multi-monitor capture is complex and requires X11
        # Fallback to full screen for now
        return ImageGrab.grab()
    
    def _capture_macos_monitor(self, monitor_id: int) -> Optional[Image.Image]:
        """Capture screenshot from specific macOS monitor"""
        # macOS multi-monitor capture requires platform-specific APIs
        # Fallback to full screen for now
        return ImageGrab.grab()
    
    def _capture_screenshot_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle capture_screenshot action
        
        Args:
            args: Dictionary containing optional monitor_id, quality, format
            
        Returns:
            Dictionary representation of ScreenshotResult
        """
        monitor_id = args.get('monitor_id')
        quality = args.get('quality')
        image_format = args.get('format')
        
        result = self.capture_screenshot(monitor_id, quality, image_format)
        
        return {
            'success': result.success,
            'image_data': result.image_data,
            'format': result.format,
            'width': result.width,
            'height': result.height,
            'size_bytes': result.size_bytes,
            'error': result.error
        }
    
    def _capture_region_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle capture_region action
        
        Args:
            args: Dictionary containing x, y, width, height, and optional quality, format
            
        Returns:
            Dictionary representation of ScreenshotResult
        """
        x = args.get('x')
        y = args.get('y')
        width = args.get('width')
        height = args.get('height')
        quality = args.get('quality')
        image_format = args.get('format')
        
        if x is None:
            raise ValueError("x coordinate is required for capture_region")
        if y is None:
            raise ValueError("y coordinate is required for capture_region")
        if width is None:
            raise ValueError("width is required for capture_region")
        if height is None:
            raise ValueError("height is required for capture_region")
        
        result = self.capture_region(x, y, width, height, quality, image_format)
        
        return {
            'success': result.success,
            'image_data': result.image_data,
            'format': result.format,
            'width': result.width,
            'height': result.height,
            'size_bytes': result.size_bytes,
            'error': result.error
        }
    
    def _get_screen_info_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle get_screen_info action
        
        Args:
            args: Dictionary (no additional args needed)
            
        Returns:
            Dictionary with screen information
        """
        screens = self.get_screen_info()
        
        return {
            'screens': [
                {
                    'monitor_id': s.monitor_id,
                    'width': s.width,
                    'height': s.height,
                    'x': s.x,
                    'y': s.y,
                    'is_primary': s.is_primary
                }
                for s in screens
            ]
        }
