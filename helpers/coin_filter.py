"""
This helper is used to filter coins. It accepts a dict of coins and returns the most suitable coin.
"""


def filter_coin(side: str, rank: int, history_time: int, coins: dict, tick: int, rising_rate_restriction: float = 0,
                banned_coins=None) -> str:
    """
    Filter coin by side and rank rising the most or falling the most in the past history time.
    :param side: long or short
    :param rank: rising or falling rank
    :param history_time: past history time
    :param coins: dict
    :param tick: current tick
    :param rising_rate_restriction: history rising rate restriction
    :param banned_coins: banned coins
    :return: symbol: str
    """
    # Pay attention to efficiency not to use sorted() function.
    if banned_coins is None:
        banned_coins = []
    if tick - history_time < 0:
        return ''
    filtered_coins = {}
    for symbol, data in coins.items():
        if data[tick] < 2 or data[tick - history_time] < 2:
            continue
        if side == 'long':
            profit_rate = data[tick] / data[tick - history_time] - 1
        elif side == 'short':
            profit_rate = data[tick - history_time] / data[tick] - 1
        else:
            raise ValueError('side must be long or short.')
        if profit_rate > rising_rate_restriction:
            filtered_coins[symbol] = profit_rate
    while rank >= 0:
        if filtered_coins:
            max_symbol = max(filtered_coins, key=filtered_coins.get)
        else:
            return ''
        if rank == 0:
            return max_symbol
        else:
            filtered_coins.pop(max_symbol)
            if max_symbol not in banned_coins:
                rank -= 1
    return ''
