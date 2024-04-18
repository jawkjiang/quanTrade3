import os.path

from utils import Account, SubAccount
from helpers.data_loader import src_loader, args_loader, min_qty_loader
from helpers.arguments_generator import generate, random_index_genenrate
from helpers.outputter import overview_outputter, args_outputter, indexes_outputter, curves_painter

import time


def primarily_filter():
    # Initialize
    data = src_loader('data/src.csv')
    """
    In the first roll, the args are generated instead of loading from a file.
    """
    min_qty = min_qty_loader('data/min_qty.csv')
    """
    for arg in args:
        sub_account = SubAccount(*arg)
        account.add_sub_account(sub_account)
    """
    args_generating_rules = {
        'leverage': (1, 3.3, 0.1),
        'history_time': (50*12, 168*12, 1*12),
        'close_time': (50*12, 168*12, 1*12),
        'stop_loss': (0.05, 0.1, 0.005),
        'trailing_time': (50*12, 120*12, 1*12),
        'trailing_stop': (0.035, 0.08, 0.005),
        'profit_time': (6*12, 24*12, 1*12),
        'profit_stop': (0.02, 0.05, 0.001),
        'rising_rate_restriction': (0, 0.035, 0.001),
        'add_position_profit_rate1': (0.1, 0.15, 0.002),
        'add_position_profit_rate2': (0.18, 0.23, 0.002),
        'cool_down_time': (48*12, 120*12, 1*12),
    }

    def loop(rank):
        args = generate(args_generating_rules, 10000)
        overviews = []
        for arg in args:
            sub_account = SubAccount(rank, side="long", balance=10000, **arg)
            sub_account.load_data(data, 100000, min_qty)
            sub_account.run()
            overviews.append(sub_account.generate_overview())
            print(args.index(arg))
        # Output
        timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        overview_outputter(timestamp, overviews)
        args_outputter(timestamp, args)

    for i in range(1):
        loop(2)


def secondarily_filter():
    # Initialize
    data = src_loader('data/src.csv')
    min_qty = min_qty_loader('data/min_qty.csv')
    args = args_loader(('data/args_rank_0.csv', 'data/args_rank_1.csv', 'data/args_rank_2.csv'))

    def loop():
        indexes = random_index_genenrate('data/index.csv', 2000)
        print('Data loaded.')
        overviews = []
        timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        if not os.path.exists(f"output/{timestamp}"):
            os.makedirs(f"output/{timestamp}")
        for index in indexes:
            account = Account()
            account.load_data(data=data, args=args, min_qty=min_qty, indexes=index)
            account.run()
            curves_painter(timestamp, [account.values], indexes.index(index))
            overviews.append(account.generate_overview())
            print(indexes.index(index))
            del account

        # Output
        overview_outputter(timestamp, overviews)
        indexes_outputter(timestamp, indexes)

    for i in range(5):
        loop()


if __name__ == '__main__':
    secondarily_filter()
