def str_time_since(seconds):
    MINUTE, HOUR, DAY, MONTH, YEAR = 60, 60 * 60, 24 * 60 * 60, 30 * 24 * 60 * 60, 365 * 24 * 60 * 60
    if seconds < MINUTE:
        return f"{seconds}s"
    elif seconds < HOUR:
        return f"{seconds // MINUTE}m"
    elif seconds < DAY:
        return f"{seconds // HOUR}h {seconds % HOUR // MINUTE}m"
    elif seconds < MONTH:
        return f"{seconds // DAY}d {seconds % DAY // HOUR}h"
    elif seconds < YEAR:
        return f"{seconds // MONTH} month(s) {seconds % MONTH // DAY}d"
    else:
        return f"{seconds // YEAR} year(s)"