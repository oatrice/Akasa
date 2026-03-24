import re
from typing import Optional

def format_duration_str(duration: Optional[str]) -> Optional[str]:
    """
    Parses a duration string like '7565s' or '7565' and formats it to 'Xh Ym Zs'.
    If it's already formatted or non-numeric, it returns the original string.
    """
    if not duration:
        return duration
        
    duration = str(duration).strip()
    
    # Check if it is purely numeric or ends with 's' followed by nothing
    match = re.match(r'^(\d+(?:\.\d+)?)\s*s?$', duration, re.IGNORECASE)
    if match:
        try:
            total_seconds = int(float(match.group(1)))
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except ValueError:
            return duration
            
    return duration
