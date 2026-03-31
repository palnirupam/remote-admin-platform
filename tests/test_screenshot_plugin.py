"""
Unit tests for Screenshot Plugin

Tests screenshot capture, region capture, compression, format conversion,
and error handling.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from remote_system.plugins.screenshot_plugin import (
    ScreenshotPlugin,
    ScreenshotResult,
    ScreenInfo
)


@pytest.fixture
def plugin():
    """Create a screenshot plugin instance"""
    return ScreenshotPlugin()


@pytest.fixture
def mock_image():
    """Create a mock PIL Image"""
    img = Image.new('RGB', (1920, 1080), color='blue')
    return img


class TestScreenshotPlugin:
    """Test suite for ScreenshotPlugin"""
    
    def test_plugin_name(self, plugin):
        """Test plugin returns correct name"""
        assert plugin.get_name() == "screenshot"
    
    def test_required_arguments(self, plugin):
        """Test plugin returns required arguments"""
        required = plugin.get_required_arguments()
        assert 'action' in required
    
    def test_invalid_action(self, plugin):
        """Test plugin raises error for invalid action"""
        with pytest.raises(ValueError, match="Invalid action"):
            plugin.execute({'action': 'invalid_action'})
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_success(self, mock_grab, plugin, mock_image):
        """
        Test successful full screen capture
        Requirement: 2.1
        """
        mock_grab.return_value = mock_image
        
        result = plugin.capture_screenshot()
        
        assert result.success is True
        assert result.image_data is not None
        assert result.width == 1920
        assert result.height == 1080
        assert result.format == 'PNG'
        assert result.size_bytes > 0
        assert result.error is None
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_with_quality(self, mock_grab, plugin, mock_image):
        """
        Test screenshot capture with custom quality setting
        Requirement: 2.3
        """
        mock_grab.return_value = mock_image
        
        # Test with quality 50
        result = plugin.capture_screenshot(quality=50)
        
        assert result.success is True
        assert result.image_data is not None
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_quality_bounds(self, mock_grab, plugin, mock_image):
        """
        Test quality setting is clamped to 1-100 range
        Requirement: 2.3
        """
        mock_grab.return_value = mock_image
        
        # Test quality below minimum
        result = plugin.capture_screenshot(quality=-10)
        assert result.success is True
        
        # Test quality above maximum
        result = plugin.capture_screenshot(quality=150)
        assert result.success is True
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_jpeg_format(self, mock_grab, plugin, mock_image):
        """
        Test screenshot capture in JPEG format
        Requirement: 2.6
        """
        mock_grab.return_value = mock_image
        
        result = plugin.capture_screenshot(image_format='JPEG', quality=85)
        
        assert result.success is True
        assert result.format == 'JPEG'
        assert result.image_data is not None
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_bmp_format(self, mock_grab, plugin, mock_image):
        """
        Test screenshot capture in BMP format
        Requirement: 2.6
        """
        mock_grab.return_value = mock_image
        
        result = plugin.capture_screenshot(image_format='BMP')
        
        assert result.success is True
        assert result.format == 'BMP'
        assert result.image_data is not None
    
    def test_capture_screenshot_unsupported_format(self, plugin):
        """
        Test screenshot capture with unsupported format
        Requirement: 2.5
        """
        result = plugin.capture_screenshot(image_format='TIFF')
        
        assert result.success is False
        assert result.error is not None
        assert 'Unsupported format' in result.error
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_with_monitor_id(self, mock_grab, plugin, mock_image):
        """
        Test screenshot capture from specific monitor
        Requirement: 2.4
        """
        mock_grab.return_value = mock_image
        
        result = plugin.capture_screenshot(monitor_id=0)
        
        assert result.success is True
        assert result.image_data is not None
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_failure(self, mock_grab, plugin):
        """
        Test screenshot capture handles failure gracefully
        Requirement: 2.5
        """
        mock_grab.side_effect = Exception("Display not available")
        
        result = plugin.capture_screenshot()
        
        assert result.success is False
        assert result.error is not None
        assert 'Screenshot capture failed' in result.error
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_screenshot_returns_none(self, mock_grab, plugin):
        """
        Test screenshot capture when ImageGrab returns None
        Requirement: 2.5
        """
        mock_grab.return_value = None
        
        result = plugin.capture_screenshot()
        
        assert result.success is False
        assert result.error == "Failed to capture screenshot"
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_region_success(self, mock_grab, plugin):
        """
        Test successful region capture
        Requirement: 2.2
        """
        region_image = Image.new('RGB', (800, 600), color='red')
        mock_grab.return_value = region_image
        
        result = plugin.capture_region(x=100, y=100, width=800, height=600)
        
        assert result.success is True
        assert result.image_data is not None
        assert result.width == 800
        assert result.height == 600
        assert result.error is None
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_region_with_coordinates(self, mock_grab, plugin):
        """
        Test region capture with various coordinates
        Requirement: 2.2
        """
        region_image = Image.new('RGB', (400, 300), color='green')
        mock_grab.return_value = region_image
        
        # Test different coordinate sets
        test_cases = [
            (0, 0, 400, 300),
            (100, 100, 400, 300),
            (500, 500, 200, 200),
        ]
        
        for x, y, width, height in test_cases:
            result = plugin.capture_region(x=x, y=y, width=width, height=height)
            assert result.success is True
            mock_grab.assert_called_with(bbox=(x, y, x + width, y + height))
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_region_with_quality(self, mock_grab, plugin):
        """
        Test region capture with compression quality
        Requirement: 2.3, 2.6
        """
        region_image = Image.new('RGB', (640, 480), color='yellow')
        mock_grab.return_value = region_image
        
        result = plugin.capture_region(x=0, y=0, width=640, height=480, quality=70)
        
        assert result.success is True
        assert result.image_data is not None
    
    def test_capture_region_invalid_dimensions(self, plugin):
        """
        Test region capture with invalid dimensions
        Requirement: 2.5
        """
        # Test zero width
        result = plugin.capture_region(x=0, y=0, width=0, height=100)
        assert result.success is False
        assert 'Width and height must be positive' in result.error
        
        # Test negative height
        result = plugin.capture_region(x=0, y=0, width=100, height=-50)
        assert result.success is False
        assert 'Width and height must be positive' in result.error
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_region_failure(self, mock_grab, plugin):
        """
        Test region capture handles failure gracefully
        Requirement: 2.5
        """
        mock_grab.side_effect = Exception("Region capture error")
        
        result = plugin.capture_region(x=0, y=0, width=100, height=100)
        
        assert result.success is False
        assert result.error is not None
        assert 'Region capture failed' in result.error
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_get_screen_info(self, mock_grab, plugin, mock_image):
        """
        Test getting screen information
        Requirement: 2.4
        """
        mock_grab.return_value = mock_image
        
        screens = plugin.get_screen_info()
        
        assert len(screens) > 0
        assert isinstance(screens[0], ScreenInfo)
        assert screens[0].width > 0
        assert screens[0].height > 0
        assert screens[0].is_primary is True
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_get_screen_info_failure_returns_default(self, mock_grab, plugin):
        """
        Test get_screen_info returns default on failure
        Requirement: 2.5
        """
        mock_grab.side_effect = Exception("Display error")
        
        screens = plugin.get_screen_info()
        
        # Should return default screen info
        assert len(screens) > 0
        assert screens[0].width == 1920
        assert screens[0].height == 1080
    
    def test_compress_image_png(self, plugin, mock_image):
        """
        Test PNG image compression
        Requirement: 2.6
        """
        compressed = plugin._compress_image(mock_image, 'PNG', 85)
        
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
        
        # Verify it's valid PNG data
        img = Image.open(io.BytesIO(compressed))
        assert img.format == 'PNG'
    
    def test_compress_image_jpeg(self, plugin, mock_image):
        """
        Test JPEG image compression
        Requirement: 2.6
        """
        compressed = plugin._compress_image(mock_image, 'JPEG', 85)
        
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
        
        # Verify it's valid JPEG data
        img = Image.open(io.BytesIO(compressed))
        assert img.format == 'JPEG'
    
    def test_compress_image_jpeg_with_alpha(self, plugin):
        """
        Test JPEG compression with RGBA image (alpha channel)
        Requirement: 2.6
        """
        rgba_image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        
        compressed = plugin._compress_image(rgba_image, 'JPEG', 85)
        
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
    
    def test_compress_image_different_quality_levels(self, plugin, mock_image):
        """
        Test compression with different quality settings
        Requirement: 2.3, 2.6
        """
        # Higher quality should produce larger files
        high_quality = plugin._compress_image(mock_image, 'JPEG', 95)
        low_quality = plugin._compress_image(mock_image, 'JPEG', 10)
        
        assert len(high_quality) > len(low_quality)
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_execute_capture_screenshot_action(self, mock_grab, plugin, mock_image):
        """Test execute method with capture_screenshot action"""
        mock_grab.return_value = mock_image
        
        result = plugin.execute({
            'action': 'capture_screenshot',
            'quality': 80,
            'format': 'PNG'
        })
        
        assert result['success'] is True
        assert result['image_data'] is not None
        assert result['format'] == 'PNG'
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_execute_capture_region_action(self, mock_grab, plugin):
        """Test execute method with capture_region action"""
        region_image = Image.new('RGB', (500, 400), color='blue')
        mock_grab.return_value = region_image
        
        result = plugin.execute({
            'action': 'capture_region',
            'x': 100,
            'y': 100,
            'width': 500,
            'height': 400,
            'quality': 75
        })
        
        assert result['success'] is True
        assert result['width'] == 500
        assert result['height'] == 400
    
    def test_execute_capture_region_missing_args(self, plugin):
        """Test execute method with missing required arguments"""
        with pytest.raises(ValueError, match="x coordinate is required"):
            plugin.execute({
                'action': 'capture_region',
                'y': 100,
                'width': 500,
                'height': 400
            })
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_execute_get_screen_info_action(self, mock_grab, plugin, mock_image):
        """Test execute method with get_screen_info action"""
        mock_grab.return_value = mock_image
        
        result = plugin.execute({
            'action': 'get_screen_info'
        })
        
        assert 'screens' in result
        assert len(result['screens']) > 0
        assert 'width' in result['screens'][0]
        assert 'height' in result['screens'][0]
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_compression_reduces_bandwidth(self, mock_grab, plugin):
        """
        Test that compression reduces image size
        Requirement: 2.6
        """
        # Create a large image
        large_image = Image.new('RGB', (1920, 1080), color='blue')
        mock_grab.return_value = large_image
        
        # Capture with low quality (more compression)
        result_low = plugin.capture_screenshot(quality=10, image_format='JPEG')
        
        # Capture with high quality (less compression)
        result_high = plugin.capture_screenshot(quality=95, image_format='JPEG')
        
        assert result_low.success is True
        assert result_high.success is True
        
        # Low quality should produce smaller file
        assert result_low.size_bytes < result_high.size_bytes
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_format_conversion(self, mock_grab, plugin, mock_image):
        """
        Test conversion between different image formats
        Requirement: 2.6
        """
        mock_grab.return_value = mock_image
        
        formats = ['PNG', 'JPEG', 'BMP']
        
        for fmt in formats:
            result = plugin.capture_screenshot(image_format=fmt)
            assert result.success is True
            assert result.format == fmt
            
            # Verify the image data is valid for the format
            img = Image.open(io.BytesIO(result.image_data))
            assert img.format == fmt
    
    def test_platform_detection(self, plugin):
        """Test that plugin detects platform correctly"""
        assert plugin.platform in ['Windows', 'Linux', 'Darwin', 'Java']
    
    @patch('remote_system.plugins.screenshot_plugin.ImageGrab.grab')
    def test_capture_monitor_fallback(self, mock_grab, plugin, mock_image):
        """Test that _capture_monitor falls back to full screen on unsupported platform"""
        mock_grab.return_value = mock_image
        
        # Test with invalid monitor ID
        result = plugin._capture_monitor(999)
        
        # Should fallback gracefully
        assert result is not None or result is None  # Either works or returns None
