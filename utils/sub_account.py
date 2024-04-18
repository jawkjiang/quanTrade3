"""
SubAccount is the most basic trading unit in the backtesting system.
"""

import helpers.indicator_calculator as ic
import helpers.coin_filter as cf
from utils.exceptions import OpenMarketError, CloseMarketError
import math


class SubAccount:
    def __init__(self, rank, side, balance, **kwargs):
        # Required parameters
        self.rank = rank
        self.side = side
        self.leverage = kwargs.get('leverage', 1)
        self.history_time = round(kwargs.get('history_time', 168))
        self.close_time = round(kwargs.get('close_time', 168))
        self.stop_loss = kwargs.get('stop_loss', 0.1)
        self.trading_fee = 0.0005

        # Optional parameters
        self.rising_rate_restriction = kwargs.get('rising_rate_restriction', 0)
        self.trailing_time = round(kwargs.get('trailing_time', None))
        self.trailing_stop = kwargs.get('trailing_stop', None)
        self.add_position_profit_rate1 = kwargs.get('add_position_profit_rate1', None)
        self.add_position_profit_rate2 = kwargs.get('add_position_profit_rate2', None)
        self.profit_time = round(kwargs.get('profit_time', None))
        self.profit_stop = kwargs.get('profit_stop', None)
        self.cool_down_time = round(kwargs.get('cool_down_time', None))
        self.draw_down_restriction = 0.3

        # Indicators and internal variables
        self.profit_rate = 0
        self.trade_count = 0
        self.win_rate = 0
        self.win_count = 0
        self.profit_rate_peak = 0
        self.max_profit_rate_single_trade = 0
        self.max_loss_rate_single_trade = 0
        self.max_streak = 0
        self.current_streak = 0
        self.max_loss_streak = 0
        self.current_loss_streak = 0
        self.max_draw_down = 0
        self.profit_factor = 0
        self.total_profit = 0
        self.total_loss = 0

        # Trading status
        self.base = 10000
        self.balance = balance
        self.entry_position_value = 0
        self.value = balance
        self.value_peak = balance
        self.value_valley = balance
        self.symbol = ''
        self.position = 0
        self.entry_price = 0
        self.entry_tick = 0
        self.stop_loss_price = 0
        self.trailing_stop_price = 0
        self.add_position_price1 = 0
        self.add_position_flag1 = False
        self.add_position_price2 = 0
        self.add_position_flag2 = False
        self.profit_stop_price = 0
        self.history = []
        self.banned_coins = {}
        self.draw_down_flag = False
        self.hang = False

        # Data
        self.data = {}
        self.min_qty = {}
        self.data_length = 0
        self.tick = 0

        self.overview = []

    def load_data(self, data, data_length, min_qty):
        self.data = data
        self.data_length = data_length
        self.min_qty = min_qty

    def generate_args(self):
        args = {
            'Rank': self.rank,
            'Side': self.side,
            'Leverage': self.leverage,
            'History Time': self.history_time,
            'Close Time': self.close_time,
            'Stop Loss': self.stop_loss,
            'Trailing Time': self.trailing_time,
            'Trailing Stop': self.trailing_stop,
            'Add Position Profit Rate1': self.add_position_profit_rate1,
            'Add Position Profit Rate2': self.add_position_profit_rate2,
            'Profit Time': self.profit_time,
            'Profit Stop': self.profit_stop,
            'Cool Down Time': self.cool_down_time
        }
        return args

    def generate_overview(self):
        # Calculate some indicators after the backtesting
        self.win_rate = self.win_count / self.trade_count
        self.profit_factor = self.total_profit / self.total_loss
        # Generate overview and arguments
        overview = {
            'Trade Count': self.trade_count,
            'Win Rate': self.win_rate,
            'Lowest Value': self.value_valley,
            'Profit Rate Peak': self.profit_rate_peak,
            'Final Profit Rate': self.profit_rate,
            'Max Profit Rate Single Trade': self.max_profit_rate_single_trade,
            'Max Loss Rate Single Trade': self.max_loss_rate_single_trade,
            'Max Streak': self.max_streak,
            'Max Loss Streak': self.max_loss_streak,
            'Max Draw Down': self.max_draw_down,
            'Profit Factor': self.profit_factor
        }
        return overview

    def run(self):
        while self.tick < self.data_length:
            self.update(self.tick)
            self.tick += 1
        return

    # Update is the core method in SubAccount. It updates the account status by each tick.
    def update(self, tick):
        try:
            self.tick = tick
            # Judge if the subAccount is newly created, or unactivated
            if self.entry_tick == 0 or self.symbol == '':
                self.open_market()

            # Close market first
            # Fetch basic information
            price = self.data[self.symbol][self.tick]
            self.value = self.balance + self.position * price
            self.value_peak = max(self.value_peak, self.value)
            self.value_valley = min(self.value_valley, self.value)
            self.profit_rate = self.value / self.base - 1
            self.profit_rate_peak = max(self.profit_rate_peak, self.profit_rate)
            self.trailing_stop_price = ic.trailing_stop_loss_calculate(self.side, price, self.trailing_stop_price,
                                                                       self.trailing_stop)
            # Mention: common stop_loss and profit_stop won't be updated by each tick.
            # They're updated in the open_market method.

            # Update indicators
            self.max_draw_down = ic.max_draw_down_calculate(self.value, self.value_peak, self.max_draw_down)
            if self.draw_down_restriction is not None and self.max_draw_down > self.draw_down_restriction:
                self.close_market()
                self.draw_down_flag = True
                return

            # Detect closing conditions
            past_tick = self.tick - self.entry_tick
            closing_conditions = [
                past_tick >= self.close_time,
                price <= self.stop_loss_price and self.side == 'long',
                # price >= self.stop_loss_price and self.side == 'short',
                price <= self.trailing_stop_price and self.side == 'long' and past_tick >= self.trailing_time,
                # price >= self.trailing_stop_price and self.side == 'short' and past_tick >= self.trailing_time,
                price <= self.profit_stop_price and self.side == 'long' and past_tick >= self.profit_time,
                # price >= self.profit_stop_price and self.side == 'short' and past_tick >= self.profit_time
            ]
            if any(closing_conditions):
                symbol = cf.filter_coin(self.side, self.rank, self.history_time, self.data, self.tick,
                                        self.rising_rate_restriction)
                if self.symbol != symbol or price <= self.entry_price:
                    self.close_market()
            # Judge if the subAccount is just closed
            if self.symbol == '':
                self.open_market()
            else:
                # Judge if adding position conditions triggered
                add_position_conditions1 = [
                    price >= self.add_position_price1 and self.side == 'long' and not self.add_position_flag1,
                    # price <= self.add_position_price1 and self.side == 'short' and not self.add_position_flag1
                ]
                if any(add_position_conditions1):
                    self.add_position(1)
                add_position_conditions2 = [
                    price >= self.add_position_price2 and self.side == 'long' and not self.add_position_flag2,
                    # price <= self.add_position_price2 and self.side == 'short' and not self.add_position_flag2
                ]
                if any(add_position_conditions2):
                    self.add_position(2)
            return
        except OpenMarketError:
            return
        except CloseMarketError:
            return

    def open_market(self):
        # Open market is the method to open a new position.
        # It's called when the subAccount is newly created and just closed.
        if self.hang:
            raise OpenMarketError
        self.banned_coins = {key: value for key, value in self.banned_coins.items()
                             if value >= self.tick - self.cool_down_time}
        banned_coins = [value for key, value in self.banned_coins.items()]
        symbol = cf.filter_coin(self.side, self.rank, self.history_time, self.data, self.tick,
                                self.rising_rate_restriction, banned_coins)
        self.symbol = symbol
        if symbol == '':
            raise OpenMarketError
        self.entry_price = self.data[symbol][self.tick]
        self.entry_tick = self.tick
        min_qty = self.min_qty[symbol]
        self.position = math.floor(self.balance / (1 + self.trading_fee) * self.leverage / self.entry_price) // min_qty * min_qty
        self.entry_position_value = self.position * self.entry_price
        self.balance -= self.entry_position_value * (1 + self.trading_fee)
        if self.side == 'long':
            self.stop_loss_price = self.entry_price * (1 - self.stop_loss)
            self.profit_stop_price = self.entry_price * (1 + self.profit_stop)
            self.add_position_price1 = self.entry_price * (1 + self.add_position_profit_rate1)
            self.add_position_price2 = self.entry_price * (1 + self.add_position_profit_rate2)
        elif self.side == 'short':
            self.stop_loss_price = self.entry_price * (1 + self.stop_loss)
            self.profit_stop_price = self.entry_price * (1 - self.profit_stop)
            self.add_position_price1 = self.entry_price * (1 - self.add_position_profit_rate1)
            self.add_position_price2 = self.entry_price * (1 - self.add_position_profit_rate2)
        else:
            raise ValueError('side must be long or short.')
        return

    def close_market(self):
        # Close market is the method to close a position.
        # It's called when the subAccount is newly created and just closed.
        price = self.data[self.symbol][self.tick]

        # Update indicators
        self.trade_count += 1
        if (self.side == 'long' and price > self.entry_price) or (self.side == 'short' and price < self.entry_price):
            self.win_count += 1
            self.current_streak += 1
            self.max_streak = max(self.max_streak, self.current_streak)
            self.current_loss_streak = 0
            profit_rate = price / self.entry_price - 1 if self.side == 'long' else self.entry_price / price - 1
            self.max_profit_rate_single_trade = max(self.max_profit_rate_single_trade, profit_rate)

            self.total_profit += self.position * (price - self.entry_price)
        else:
            self.current_loss_streak += 1
            self.max_loss_streak = max(self.max_loss_streak, self.current_loss_streak)
            self.current_streak = 0
            loss_rate = price / self.entry_price - 1 if self.side == 'long' else self.entry_price / price - 1
            self.max_loss_rate_single_trade = min(self.max_loss_rate_single_trade, loss_rate)
            self.banned_coins[self.symbol] = self.tick

            self.total_loss += self.position * (self.entry_price - price)

        # Update trading status
        self.balance += self.position * price * (1 - self.trading_fee)
        self.symbol = ''
        self.position = 0
        self.stop_loss_price = 0
        self.trailing_stop_price = 0
        self.profit_stop_price = 0
        self.history.append((self.tick, self.profit_rate))
        self.add_position_flag1 = False
        self.add_position_flag2 = False

    def add_position(self, index):
        # Add position is the method to add a new position.
        # It's called when the subAccount has already opened a position.
        """
        Add position.
        :param index: 1 or 2
        """
        price = self.data[self.symbol][self.tick]
        min_qty = self.min_qty[self.symbol]
        if index == 1:
            position_change = 0.5 * math.floor(self.entry_position_value * self.leverage / price) // min_qty * min_qty
            self.add_position_flag1 = True
        elif index == 2:
            position_change = 0.25 * math.floor(self.entry_position_value * self.leverage / price) // min_qty * min_qty
            self.add_position_flag2 = True
        else:
            raise ValueError('index must be 1 or 2.')
        self.position += position_change
        self.balance -= position_change * (1 + self.trading_fee) * price
        return
