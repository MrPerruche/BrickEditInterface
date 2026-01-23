import os

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


def parse_float_tuple(text: str):
    text = text.strip().strip("()")
    return tuple(map(float, text.split(",")))


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total


def get_vehicles_path():
    return os.path.expanduser("~\\AppData\\Local\\BrickRigs\\SavedRemastered\\Vehicles")


def repr_file_size(size_bytes: int, digits: int = 2, unit_change_threshold: int = 1024):
    # If you're dealing with RiB or QiB wth are you doing playing Brick Rigs and using this sht "software" in 2200 ?
    size_names = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    i = 0
    assert unit_change_threshold >= 1024, f"Invalid unit change threshold {unit_change_threshold}"
    while size_bytes >= unit_change_threshold:
        size_bytes /= 1024
        i += 1
    if digits == 0:
        return f"{int(size_bytes)} {size_names[i]}"
    else:
        return f"{round(size_bytes, digits)} {size_names[i]}"


def blockwise_exp(n, p=3, base=2):
    r"""
    Compute a stepwise accelerating integer value for a slider or similar control.

    The function works like this:
    - The output increases in blocks of width `p`.
    - Within each block of `p` steps, the output increases by a constant amount (the "slope").
    - Each new block has a larger slope than the previous one, multiplying by `base` each time.
    - This produces a smooth, accelerating feel while keeping all outputs as integers.

    Args:
        n (int): The current step or position (integer).
        p (int, optional): The width of each block before the slope increases, by default 3.
            Larger `p` makes the acceleration feel slower and smoother.
        base (int, optional): The multiplier for slope growth at each new block, by default 2.
            A larger base increases the acceleration more quickly.

    Returns:
        int
            The integer value corresponding to step `n`.

    Example:
        With p=3 and base=2, the derivative of the output looks like:
            0,0,0, 1,1,1, 2,2,2, 4,4,4, 8,8,8, ...
        and the cumulative output (f(n)) increases accordingly.
        
        Paste the following statements in desmos to preview the function:
        p\ =3
        b\ =2
        n=x
        k=\operatorname{floor}\left(\frac{n}{p}\right)
        r\ =\ n-kp
        f\left(x\right)=p\frac{b^{k}-1}{b-1}+r\cdot b^{k}
    """
    k = n // p
    r = n - k * p
    if base == 1:
        return n  # linear case
    return (base**k - 1) // (base - 1) * p + r * base**k



def blockwise_exp_inverse(value, p=3, base=2):
    """
    Given a value, find the slider step n that would produce it
    using blockwise_exp.
    """
    if base == 1:
        return value  # linear

    n = 0
    while n < 10000:  # Safe limit
        val = blockwise_exp(n, p, base)
        if val > value:
            return max(0, n - 1)
        n += 1