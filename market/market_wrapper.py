__author__ = 'tao zhang'
__email__ = 'uncczhangtao@gmail.com'

import pandas as pd
import numpy as np
from datetime import datetime as dt
def create_k_data(ticker='BTC'):
    df = pd.read_csv(f'../data/{ticker}-USD.csv')
    df = df.reset_index()
    df = df.rename(columns={'index': 'key'})
    df.columns = df.columns.str.lower()
    K_DEFAULT_DT_FMT = "%Y-%m-%d"

    def week_of_date(date_str, fmt=K_DEFAULT_DT_FMT):
        """
        输入'2016-01-01' 转换为星期几，返回int 0-6分别代表周一到周日
        :param date_str: 式时间日期str对象
        :param fmt: 如date_str不是%Y-%m-%d形式，对应的格式str对象
        :param fix: 是否修复日期不规范的写法，eg. 2016-1-1 fix 2016-01-01
        :return: 返回int 0-6分别代表周一到周日
        """
        return dt.strptime(date_str, fmt).weekday()

    df['date_week'] = df['date'].apply(lambda x: dt.strptime(str(x), '%Y-%m-%d').weekday())
    df['date'] = df['date'].apply(lambda x: dt.strptime(str(x), '%Y-%m-%d'))
    df['p_change'] = np.log(df.close / df.close.shift(1)) * 100

    df = df.set_index('date')
    return df

df = create_k_data()
