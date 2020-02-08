# -*- coding:utf-8 -*-
import random

import numpy as np

from tgym.envs.base import BaseEnv
from tgym.envs.reward import get_reward_func
from tgym.logger import logger


class AverageEnv(BaseEnv):
    """
    多支股票平均分仓日内买卖
    action: [scaled_sell_price, scaled_buy_price]*n, 取值[-1, 1], 对应[-0.1, 0.1]
    即: 出价较前一交易日的涨跌幅
    n: 是股票的个数
    对每支股票, 先以sell_price 卖出, 再以 buy_price 买进
    NOTE(wen): 实际交易时，可能与模拟环境存在差异
        1. 先到最高价，然后再到最低价：与模拟环境一致
        2. 先到最低价，再到最高价，这里出价有两种情况
            有现金，则按最低价买进，与模拟环境一致
            无现金(满仓)，模拟环境可以成交，实盘交易时的成交状态不一定可以成交
    """

    def __init__(self, market=None, investment=100000.0, look_back_days=10,
                 used_infos=["equities_hfq_info", "indexs_info"],
                 reward_fn="daily_return"):
        """
        investment: 初始资金
        look_back_days: 向前取数据的天数
        """
        super(AverageEnv, self).__init__(market, investment, look_back_days,
                                         used_infos)
        self.avg_percent = 1.0 / self.n
        self.action_space = 2 * self.n
        self.start = market.start
        self.portfolio_info_size = 2 * self.n
        self.input_size = self.market_info_size + self.portfolio_info_size
        self.reward_fn = get_reward_func(name=reward_fn)
        self.reward_fn_name = reward_fn

    def get_init_portfolio_obs(self):
        # 初始持仓 状态
        one_day = np.array([0] * (self.n * 2))
        obs = np.array([one_day] * self.look_back_days)
        return obs

    def get_init_obs(self):
        """
        obs 由两部分组成: 市场信息, 帐户信息(收益率, 持仓量)
        """
        market_info = []
        for date in self.dates[: self.look_back_days]:
            market_info.append(self.get_market_info(date))
        market_info = np.array(market_info)
        portfolio_info = self.get_init_portfolio_obs()
        return np.concatenate((market_info, portfolio_info), axis=1)

    def get_action_price(self, action, code):
        pre_close = self.market.get_pre_close_price(
            code, self.current_date)
        logger.debug("%s %s pre_close: %.2f" %
                     (self.current_date, code, pre_close))
        [v_sell, v_buy] = action
        # scale [-1, 1] to [-0.1, 0.1]
        pct_sell, pct_buy = v_sell * 0.1, v_buy * 0.1
        sell_price = round(pre_close * (1 + pct_sell), 2)
        buy_price = round(pre_close * (1 + pct_buy), 2)
        return sell_price, buy_price

    def update_portfolio(self):
        pre_portfolio_value = self.portfolio_value
        self.market_value = 0
        self.daily_pnl = 0
        self.pnl = 0
        self.transaction_cost = 0
        self.all_transaction_cost = 0
        for p in self.portfolios:
            self.market_value += p.market_value
            self.daily_pnl += p.daily_pnl
            self.pnl += p.pnl
            self.transaction_cost += p.transaction_cost
            self.all_transaction_cost += p.all_transaction_cost
        self.total_pnl += self.pnl

        # 当日收益率 更新
        if pre_portfolio_value == 0:
            self.daily_return = 0
        else:
            self.daily_return = self.daily_pnl / pre_portfolio_value
        # update portfolio_value
        self.portfolio_value = self.market_value + self.cash
        self.portfolio_value_logs.append(self.portfolio_value)

    def get_hlc_prices(self):
        date = self.current_date
        highs, lows, closes = [], [], []
        for i in range(self.n):
            code = self.codes[i]
            if date in self.market.codes_history[code].index:
                highs.append(self.market.codes_history[code].loc[date, "high"])
                lows.append(self.market.codes_history[code].loc[date, "low"])
                closes.append(self.market.codes_history[code].loc[date, "close"])
            else:
                # 停牌时
                highs.appen(0)
                lows.appen(0)
                closes.appen(0)
        return highs, lows, closes

    def update_reward(self, sell_prices, buy_prices):
        # NOTE(wen): 如果今天盈利，则reward=1, 否则reward=-1
        # reward决定算法的搜索方向, 建议设置为一个连续可导函数
        if self.reward_fn_name in ["daily_return", "simple"]:
            self.reward = self.reward_fn(self.daily_return)
        else:
            highs, lows, closes = self.get_hlc_prices()
            self.reward = self.reward_fn(
                self.daily_return, highs, lows, closes,
                sell_prices, buy_prices)
        # 每一只股的reward
        for i in range(self.n):
            self.rewards[i] = self.reward

    def update_value_percent(self):
        if self.portfolio_value == 0:
            self.value_percent = 0.0
        else:
            self.value_percent = self.market_value / self.portfolio_value
        for i in range(self.n):
            self.portfolios[i].update_value_percent(self.portfolio_value)

    def do_action(self, action, pre_portfolio_value, only_update):
        cash_change = 0
        # 更新拆分信息
        for i in range(self.n):
            code = self.codes[i]
            divide_rate = self.market.get_divide_rate(code, self.current_date)
            self.portfolios[i].update_before_trade(divide_rate)
        sell_prices, buy_prices = [], []
        if not only_update:
            # 卖出
            for i in range(self.n):
                code = self.codes[i]
                act_i = action[2 * i: 2 * (i + 1)]
                sell_price, _ = self.get_action_price(act_i, code)
                sell_prices.append(sell_price)

                sell_cash_change, ok = self.sell(i, sell_price, 0)
                cash_change += sell_cash_change
            # 买进
            for i in range(self.n):
                code = self.codes[i]
                act_i = action[2 * i: 2 * (i + 1)]
                _, buy_price = self.get_action_price(act_i, code)
                buy_prices.append(buy_price)

                buy_cash_change, ok = self.buy(i, buy_price, self.avg_percent)
                cash_change += buy_cash_change

        logger.debug("do_action: time_id: %d, cash_change: %.1f" % (
            self.current_time_id, cash_change))

        # update
        for i in range(self.n):
            code = self.codes[i]
            close_price = self.market.get_close_price(code, self.current_date)
            self.portfolios[i].update_after_trade(
                close_price=close_price,
                cash_change=cash_change,
                pre_portfolio_value=pre_portfolio_value)
        return sell_prices, buy_prices

    def _next(self):
        market_info = self.get_market_info(self.current_date)
        portfolio_info = []
        for i in range(self.n):
            portfolio_info.append(self.portfolios[i].daily_return)
            portfolio_info.append(self.portfolios[i].value_percent)
        portfolio_info = np.array(portfolio_info)
        new_obs = np.concatenate((market_info, portfolio_info), axis=0)
        obs = np.concatenate((self.obs[1:, :],
                              np.array([new_obs])), axis=0)
        if not self.done:
            self.current_time_id += 1
            self.current_date = self.dates[self.current_time_id]
        self.pre_cash = self.cash
        return obs

    def step(self, action, only_update=False):
        """
        only_update为True时，表示buy_and_hold策略，可作为一种baseline策略
        """
        self.action = action
        self.info = {"orders": []}
        logger.debug("=" * 50 + "%s" % self.current_date + "=" * 50)
        logger.debug("current_time_id: %d, portfolio: %.1f" %
                     (self.current_time_id, self.portfolio_value))
        logger.debug("step action: %s" % str(action))

        # 到最后一天
        if self.current_date == self.dates[-1]:
            self.done = True

        pre_portfolio_value = self.portfolio_value
        sell_prices, buy_prices = self.do_action(action,
                                                 pre_portfolio_value,
                                                 only_update)
        self.update_portfolio()
        self.update_value_percent()
        self.update_reward(sell_prices, buy_prices)
        self.obs = self._next()
        self.info = {
            "orders": self.info["orders"],
            "current_date": self.current_date,
            "portfolio_value": round(self.portfolio_value, 1),
            "daily_pnl": round(self.daily_pnl, 1),
            "reward": self.reward}
        return self.obs, self.reward, self.done, self.info, self.rewards

    def get_random_action(self):
        return [random.uniform(-1, 1) for i in range(self.n * 2)]
