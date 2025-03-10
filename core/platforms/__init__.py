"""
Platform-specific window capture implementation modules.
This package contains modules for different operating systems (macOS, Windows, Linux).
"""

import platform

# Lazy import platform-specific modules based on the current OS
system = platform.system()

if system == "Darwin":
    from .macos import MacOSWindowCapture as PlatformWindowCapture
elif system == "Windows":
    from .windows import WindowsWindowCapture as PlatformWindowCapture
elif system == "Linux":
    from .linux import LinuxWindowCapture as PlatformWindowCapture
else:
    # Fallback to a dummy implementation
    class PlatformWindowCapture:
        """Dummy implementation for unsupported platforms"""
        def get_window_list(self):
            return []
        
        def capture_window(self, *args, **kwargs):
            return None 