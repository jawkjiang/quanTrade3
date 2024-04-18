"""
This helper contains some useful functions to calculate indicators.
"""


def trailing_stop_loss_calculate(side, price, stop_loss_price, rate) -> float:
    """
    Calculate trailing stop loss price.
    :param side: long or short
    :param price: current price
    :param stop_loss_price: latest stop loss price
    :param rate: trailing stop loss rate
    :return: new_stop_loss_price
    """
    if side == 'long':
        new_stop_loss_price = max(price * (1 - rate), stop_loss_price)
    elif side == 'short':
        new_stop_loss_price = min(price * (1 + rate), stop_loss_price)
    else:
        raise ValueError('side must be long or short.')
    return new_stop_loss_price


def max_draw_down_calculate(value, value_peak, max_draw_down) -> float:
    """
    Calculate max draw down.
    :param value: current value
    :param value_peak: peak value
    :param max_draw_down: max draw down
    :return: new_max_draw_down
    """
    draw_down = (value_peak - value) / value_peak
    new_max_draw_down = max(draw_down, max_draw_down)
    return new_max_draw_down
