"""
児童手当の実装
"""

import numpy as np
from openfisca_core.periods import MONTH, DAY
from openfisca_core.variables import Variable
from openfisca_japan.entities import 世帯


class 児童手当(Variable):
    value_type = float
    entity = 世帯
    definition_period = DAY
    label = "保護者への児童手当"
    reference = "https://www8.cao.go.jp/shoushi/jidouteate/annai.html"
    documentation = """
    児童手当制度
    """

    def formula(対象世帯, 対象期間, parameters):
        児童手当 = parameters(対象期間).福祉.育児.児童手当

        # 世帯で最も高い所得の人が基準となる
        世帯高所得 = 対象世帯("控除後世帯高所得", 対象期間)
        扶養人数 = 対象世帯("扶養人数", 対象期間)[0]
        所得制限限度額 = 児童手当.所得制限限度額[扶養人数]
        所得上限限度額 = 児童手当.所得上限限度額[扶養人数]
        児童手当所得条件 = 世帯高所得 < 所得制限限度額
        特例給付所得条件 = (世帯高所得 >= 所得制限限度額) * (世帯高所得 < 所得上限限度額)

        年齢 = 対象世帯.members("年齢", 対象期間)
        学年 = 対象世帯.members("学年", 対象期間)
        三歳未満の人数 = 対象世帯.sum(年齢 < 3)
        学年の降順インデックス = np.argsort(学年)[::-1]
        高校生修了後の人数 = int(対象世帯.sum(学年 > 12)[0])
        高校生以下で数えた第三子以降である = np.full(len(年齢), False)
        if 高校生修了後の人数+2 < len(年齢):
            高校生以下で数えた第三子以降である[学年の降順インデックス[高校生修了後の人数+2:]] = True

        三歳から小学校修了前かつ第二子以前の人数 = 対象世帯.sum((年齢 >= 3) * (学年 <= 6) * np.logical_not(高校生以下で数えた第三子以降である))
        三歳から小学校修了前かつ第三子以降の人数 = 対象世帯.sum((年齢 >= 3) * (学年 <= 6) * 高校生以下で数えた第三子以降である)
        中学生の人数 = 対象世帯.sum((学年 >= 7) * (学年 <= 9))

        児童手当金額 = \
            np.sum(
                + (児童手当.金額.三歳未満 * 三歳未満の人数)
                + (児童手当.金額.三歳から小学校修了前かつ第二子以前 * 三歳から小学校修了前かつ第二子以前の人数)
                + (児童手当.金額.三歳から小学校修了前かつ第三子以降 * 三歳から小学校修了前かつ第三子以降の人数)
                + (児童手当.金額.中学生 * 中学生の人数),
                )

        # 世帯高所得が所得制限金額以上かつ所得上限未満の場合に支給される特例給付
        # 特例給付も対象となる児童は中学生以下
        中学生以下の人数 = 対象世帯.sum((学年 <= 9))
        特例給付金額 = 児童手当.金額.特例給付 * 中学生以下の人数

        return 児童手当所得条件 * 児童手当金額 + 特例給付所得条件 * 特例給付金額
