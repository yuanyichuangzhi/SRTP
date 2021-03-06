```
期货数据是每秒两次的快照，且仅有买一、卖一数据，故订单簿动态的一些细节可能会遗失。
期货的成交差、成交量、持仓差、持仓量均计算双边，在数据处理中仅考虑单边。
发现一些交易的价格在上个记录的买一价和卖一价之间，且交易前后的买一价、量与卖一价、量均不变，原因不明。
由于数据的限制以及期货交易频率较低，论文P16的一些特征无法实现，一些可以实现的我进行了一定的处理（主要是衰减，使数据平滑）。
数据进行了一些检验，但在特殊位置或由于特殊情况可能出现错误。
函数data_processing的输入是待处理期货数据的存储位置和处理后数据的存储位置（均为csc格式），返回值是运行时间
期货数据最多有21：00——02：30（夜盘）、9：00——10：15、（休息15分钟）、10：30——11：30、1：30——3：30四个交易时间段
对每个时间段独立地进行数据处理
look_back函数用来计算限价订单的4个到达率（买、卖、撤销买、撤销卖），计算方法是往前回溯，识别到相应限价订单时按其数量及到当前记录的时间来计算到达率
market_order函数计算市价买/卖单到达率，计算方法时往前回溯，找到两个买/卖单，然后以第一个市价单的量及第二个市价单到当前记录的时间来计算到达率
由于期货数据不是分笔数据，故买单、买单与撤销单及其相应的数量的判定可能会存在错误
section_data函数计算某一时间段的买一价、量与卖一价、量的变化率
classify函数计算t个event后期货价格的涨、跌、平，这里使用t=5、10、15进行计算

```
def data_processing(load_path, save_path):
    import pandas as pd
    import numpy as np
    import math
    import time
    t1 = time.time()
    data = pd.read_csv(load_path, encoding='gbk')
    n = len(data.日期)
    data['价差'] = data.卖1价 - data.买1价
    data['中间价'] = (data.卖1价 + data.买1价) / 2
    Time = []
    for column in data.时间:
        temp = int(column[0:2]) * 3600 + int(column[3:5]) * 60 + int(column[6:8])
        if temp < 10800:
            temp = temp + 86400
        Time.append(temp)
    Time = Time + data.毫秒 * 0.001
    Time = pd.Series(Time)
    division = [0]
    for i in range(0, n - 1):
        if abs(Time[i + 1] - Time[i]) > 840:
            division.append(i)
            division.append(i + 1)
    division.append(n - 1)
    section_num = len(division) / 2
    if section_num == 5:
        del division[1:3]
        section_num = 4
    index = np.nonzero(list(data.成交差))[0]
    dP_buy = np.zeros(n)
    dP_sell = np.zeros(n)
    dV_buy = np.zeros(n)
    dV_sell = np.zeros(n)
    rate_MB = np.zeros(n)
    rate_MS = np.zeros(n)
    rate_LB = np.zeros(n)
    rate_LS = np.zeros(n)
    rate_LBC = np.zeros(n)
    rate_LSC = np.zeros(n)
    classfy_result = np.zeros(n)

    def look_back(start, end, buy_or_sell):
        if buy_or_sell == 'buy':
            flag = np.zeros(2)
            for k in range(start, end, -1):
                if data.成交差[k] == 0 and (data.买1价[k] != data.买1价[k - 1] or data.买1量[k] != data.买1量[k - 1]):
                    if Time[start] == Time[k - 1]:
                        rate_LB[start] = rate_LB[start - 1]
                        rate_LBC[start] = rate_LBC[start - 1]
                        break
                    if data.买1价[k] == data.买1价[k - 1]:
                        if data.买1量[k] > data.买1量[k - 1] and flag[0] == 0:
                            rate_LB[start] = (data.买1量[k] - data.买1量[k - 1]) / (Time[start] - Time[k - 1])
                            flag[0] = 1
                        elif data.买1量[k] < data.买1量[k - 1] and flag[1] == 0:
                            rate_LBC[start] = (data.买1量[k - 1] - data.买1量[k]) / (Time[start] - Time[k - 1])
                            flag[1] = 1
                    elif data.买1价[k] > data.买1价[k - 1] and flag[0] == 0:
                        rate_LB[start] = data.买1量[k] / (Time[start] - Time[k - 1])
                        flag[0] = 1
                    elif data.买1价[k] < data.买1价[k - 1] and flag[1] == 0:
                        rate_LBC[start] = data.买1量[k - 1] / (Time[start] - Time[k - 1])
                        flag[1] = 1
                if flag[0] * flag[1] == 1:
                    break
        elif buy_or_sell == 'sell':
            flag = np.zeros(2)
            for k in range(start, end, -1):
                if data.成交差[k] == 0 and (data.卖1价[k] != data.卖1价[k - 1] or data.卖1量[k] != data.卖1量[k - 1]):
                    if Time[start] == Time[k - 1]:
                        rate_LS[start] = rate_LS[start - 1]
                        rate_LSC[start] = rate_LSC[start - 1]
                        break
                    if data.卖1价[k] == data.卖1价[k - 1]:
                        if data.卖1量[k] > data.卖1量[k - 1] and flag[0] == 0:
                            rate_LS[start] = (data.卖1量[k] - data.卖1量[k - 1]) / (Time[start] - Time[k - 1])
                            flag[0] = 1
                        elif data.卖1量[k] < data.卖1量[k - 1] and flag[1] == 0:
                            rate_LSC[start] = (data.卖1量[k - 1] - data.卖1量[k]) / (Time[start] - Time[k - 1])
                            flag[1] = 1
                    elif data.卖1价[k] < data.卖1价[k - 1] and flag[0] == 0:
                        rate_LS[start] = data.卖1量[k] / (Time[start] - Time[k - 1])
                        flag[0] = 1
                    elif data.卖1价[k] > data.卖1价[k - 1] and flag[1] == 0:
                        rate_LSC[start] = data.卖1量[k - 1] / (Time[start] - Time[k - 1])
                        flag[1] = 1
                if flag[0] * flag[1] == 1:
                    break

    def market_order(start, end):
        flag = np.zeros(2)
        temp1 = 0
        temp2 = len(index) - 2
        temp4 = 1
        if end <= index[0]:
            place1 = 0
            temp4 = 0
        while temp4:
            if index[temp1] < end <= index[temp1 + 1]:
                place1 = temp1 + 1
                break
            temp3 = math.floor((temp1 + temp2) / 2)
            if end > index[temp3]:
                temp1 = temp3
            elif end <= index[temp3]:
                temp2 = temp3
        if start < index[place1 + 1]:
            return
        temp4 = 1
        if start >= index[len(index) - 1]:
            place2 = len(index) - 1
            temp4 = 0
        temp1 = place1 + 1
        temp2 = len(index) - 1
        while temp4:
            if index[temp1] <= start < index[temp1 + 1]:
                place2 = temp1
                break
            temp3 = math.floor((temp1 + temp2) / 2)
            if start >= index[temp3]:
                temp1 = temp3
            elif start < index[temp3]:
                temp2 = temp3
        for k in range(place2, place1, -1):
            for j in range(k - 1, place1 - 1, -1):
                if Time[start] == Time[index[j]]:
                    rate_MB[start] = rate_MB[start - 1]
                    rate_MS[start] = rate_MS[start - 1]
                    flag[0] = 1
                    flag[1] = 1
                    break
                if data.最新价[index[k]] >= data.卖1价[index[k] - 1] and data.最新价[index[j]] > data.买1价[index[j] - 1] and \
                        flag[0] == 0:
                    rate_MB[start] = data.成交差[index[k]] / (Time[start] - Time[index[j]]) / 2
                    flag[0] = 1
                elif data.最新价[index[k]] <= data.买1价[index[k] - 1] and data.最新价[index[j]] < data.卖1价[index[j] - 1] and \
                        flag[1] == 0:
                    rate_MS[start] = data.成交差[index[k]] / (Time[start] - Time[index[j]]) / 2
                    flag[1] = 1
                elif data.买1价[index[k] - 1] < data.最新价[index[k]] < data.卖1价[index[k] - 1]:
                    if flag[0] == 0:
                        rate_MB[start] = data.成交差[index[k]] / (Time[start] - Time[index[j]]) / 4
                        flag[0] = 1
                    if flag[1] == 0:
                        rate_MS[start] = data.成交差[index[k]] / (Time[start] - Time[index[j]]) / 4
                        flag[1] = 1
                if flag[0] * flag[1] == 1:
                    break
            if flag[0] * flag[1] == 1:
                break

    def section_data(start, end):
        for k in range(start + 1, end + 1):
            flag = np.zeros(4)
            for j in range(k - 1, start - 1, -1):
                if data.买1价[k] != data.买1价[j] and flag[0] == 0 and Time[k] != Time[j]:
                    dP_buy[k] = (data.买1价[k] - data.买1价[j]) / (Time[k] - Time[j])
                    flag[0] = 1
                if data.卖1价[k] != data.卖1价[j] and flag[1] == 0 and Time[k] != Time[j]:
                    dP_sell[k] = (data.卖1价[k] - data.卖1价[j]) / (Time[k] - Time[j])
                    flag[1] = 1
                if data.买1量[k] != data.买1量[j] and flag[2] == 0 and Time[k] != Time[j]:
                    dV_buy[k] = (data.买1量[k] - data.买1量[j]) / (Time[k] - Time[j])
                    flag[2] = 1
                if data.卖1量[k] != data.卖1量[j] and flag[3] == 0 and Time[k] != Time[j]:
                    dV_sell[k] = (data.卖1量[k] - data.卖1量[j]) / (Time[k] - Time[j])
                    flag[3] = 1
                if flag[0] * flag[1] * flag[2] * flag[3] == 1:
                    break
            look_back(k, start, 'buy')
            look_back(k, start, 'sell')
            market_order(k, start)

    def classify(t):
        for k in range(0, int(section_num)):
            for j in range(division[2 * k], division[2 * k + 1] + 1 - t):
                if data.卖1价[j] < data.买1价[j + t]:
                    classfy_result[j] = 1
                elif data.买1价[j] > data.卖1价[j + t]:
                    classfy_result[j] = -1

    for i in range(0, int(section_num)):
        section_data(division[2 * i], division[2 * i + 1])
    data['dP_buy'] = dP_buy
    data['dP_sell'] = dP_sell
    data['dV_buy'] = dV_buy
    data['dV_sell'] = dV_sell
    data['市价买单到达率'] = rate_MB
    data['市价卖单到达率'] = rate_MS
    data['限价买单到达率'] = rate_LB
    data['限价卖单到达率'] = rate_LS
    data['限价买单撤单到达率'] = rate_LBC
    data['限价卖单撤单到达率'] = rate_LSC
    for t in [5, 10, 15]:
        classify(t)
        data[str(t) + '个event后'] = classfy_result
    t2 = time.time()
    run_time = t2 - t1
    data.to_csv(save_path, encoding='gbk')
    return run_time
