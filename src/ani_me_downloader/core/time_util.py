# coding: utf-8
"""Time-difference helpers for airing ETAs."""
import time


def get_time_difference(req_time: int) -> tuple[int, int, int]:
    """Return (days, hours, minutes) until req_time (unix seconds)."""
    delta = req_time - int(time.time())
    days, delta = divmod(delta, 24 * 3600)
    hours, delta = divmod(delta, 3600)
    minutes = delta // 60
    return days, hours, minutes
