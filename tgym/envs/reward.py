# -*- coding:utf-8 -*-
from tgym.logger import logger


def simple(daily_return, *args):
    if daily_return <= 0:
        return -1
    else:
        return 1


def daily_return(daily_return, *args):
    return daily_return


def daily_return_add_count_rate(daily_return, highs, lows,
                                closes, sell_prices, buy_prices):
    fail, success, profit_count, loss_count = 0, 0, 0
    for i in range(len(highs)):
        # 买
        if buy_prices[i] >= lows[i]:
            success += 1
            if buy_prices[i] <= closes[i]:
                profit_count += 1
            else:
                loss_count += 1
        else:
            fail += 1

        # 卖
        if sell_prices[i] <= highs[i]:
            success += 1
            if sell_prices[i] <= closes[i]:
                loss_count += 1
            else:
                profit_count += 1
        else:
            fail += 1

    success_rate = (success * 2) / (success + fail)
    profit_rate = (profit_count * 2) / (profit_count + loss_count)

    reward = daily_return + success_rate + profit_rate

    return reward


def mean_squared_error(a, b):
    v = 0.0
    n = len(a)
    for i in range(n):
        v += (10.0 * (1 - b[i] / a[i])) ** 2
    return v / n


def daily_return_add_price_bound(daily_return, highs, lows,
                                 closes, sell_prices, buy_prices):
    reward = daily_return
    n = len(highs)
    # 如果出现买价>卖价 增加一个较大的惩罚
    for i in range(n):
        if sell_prices[i] < buy_prices[i]:
            reward -= 1.0
    # 计算 bound
    sell_error = mean_squared_error(highs, sell_prices)
    buy_error = mean_squared_error(lows, buy_prices)

    reward = reward - sell_error - buy_error
    return reward


def daily_return_with_chl_penalty(daily_return, highs, lows,
                                  closes, sell_prices, buy_prices):
    reward = daily_return_add_price_bound(daily_return, highs, lows, closes,
                                          sell_prices, buy_prices)
    # 增加相对于收盘价的惩罚
    close_error_sum = 0
    n = len(highs)
    for i in range(n):
        if sell_prices[i] < closes[i]:
            close_error = (closes[i] - sell_prices[i]) * 10 / closes[i]
            close_error_sum += close_error ** 2
        if buy_prices[i] > closes[i]:
            close_error = (buy_prices[i] - closes[i]) * 10 / closes[i]
            close_error_sum += close_error ** 2
    reward = reward + close_error_sum
    return reward


def get_reward_func(name="simple"):
    logger.info("tgym.envs.reward use reward function: %s" % name)
    if name == "simple":
        return simple
    if name == "daily_return":
        return daily_return
    if name == "daily_return_add_count_rate":
        return daily_return_add_count_rate
    if name == "daily_return_add_price_bound":
        return daily_return_add_price_bound
    if name == "daily_return_with_chl_penalty":
        return daily_return_with_chl_penalty


def main():
    r_func = get_reward_func(name="simple")
    assert -1 == r_func(0)
    assert 1 == r_func(0.01)
    assert -1 == r_func(-0.01)


if __name__ == '__main__':
    main()
