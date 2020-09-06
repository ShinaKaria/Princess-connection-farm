import time

import numpy as np

from core.constant import FIGHT_BTN, MAIN_BTN, MAOXIAN_BTN
from core.cv import UIMatcher
from core.pcr_config import debug
from ._tools import ToolsMixin


class FightBaseMixin(ToolsMixin):
    """
    战斗基础插片
    包括与战斗相关的基本操作
    """

    def get_fight_middle_stars(self, screen=None):
        """
        获取战斗胜利后中间的星数
        :param screen: 设置为None时，不另外截屏
        :return: 0~3
        """
        if screen is None:
            screen = self.getscreen()
        fc = np.array([98, 228, 245])  # G B R:金色
        bc = np.array([212, 171, 139])  # G B R:灰色
        c = []
        us = {
            1: (424, 135),
            2: (478, 135),
            3: (533, 135)
        }
        for i in range(1, 4):
            x = us[i][0]
            y = us[i][1]
            c += [screen[y, x]]
        c = np.array(c)
        tf = np.sqrt(((c - fc) ** 2)).sum(axis=1)
        tb = np.sqrt(((c - bc) ** 2)).sum(axis=1)
        t = tf < tb
        return np.sum(t)

    def get_fight_state(self, screen=None, max_retry=10, delay=1,
                        check_hat=False, check_xd=True, go_xd=False,
                        check_jq=False, check_ghz=True, check_star=False) -> int:
        """
        获取战斗状态
        注：不适用竞技场的战斗！
        :param: screen 第一次检测用的截图
        :param max_retry: 最大重试次数
        以下变量针对具体场景使用
        :param check_hat: 在地下城中使用，地下城的胜利以对帽子的检测判定。
        :param check_xd: 刷图中使用，会增加对限定商店的判断。出现限定商店表示成功
        :param go_xd: 刷图中使用，如果限定商店出现了，是否选择进入。
            若设置为True，则会进入限定商店，并返回1；否则，停留在胜利页面，返回1。
        :param check_jq: 推图中使用，有些boss关卡会有大段前后剧情
            若设置为True，则会检测是否有人说话的框，有的话则大力跳过
            实际情况中，该选项开启很容易导致漏点对话框，买体力会失效。
        Lparam check_ghz: 检查是否跳出公会战对话框
        :param check_star: 推图中使用，Win界面出来后统计星数并存在self.last_star
        :return:
            -1：未知状态
            0： 战斗进行中
            1： 战斗胜利
            2： 战斗失败
            3:  战斗胜利，并且出现了限定商店，并且进入了限定商店
        """
        retry = 0
        while retry < max_retry:
            retry += 1
            if screen is None:
                sc = self.getscreen()
            else:
                sc = screen
                screen = None
            if self.is_exists(FIGHT_BTN["shbg"], screen=sc):
                # 出现伤害报告，战斗结束 （地下城）
                if self.is_exists(FIGHT_BTN["qwjsyl"], screen=sc):
                    # 前往角色一览：失败
                    return 2
                elif check_hat and self.is_exists(FIGHT_BTN["win"], screen=sc):
                    # 找到帽子：成功
                    return 1
                elif self.is_exists(FIGHT_BTN["xiayibu"], screen=sc):
                    # 右下角有长的下一步，但是没找到帽子：点掉它
                    if check_star:
                        stars = self.get_fight_middle_stars(sc)
                        if stars > 0:
                            self.last_star = stars
                        else:
                            self.log.write_log("warning", "战斗结束星数检测失败，默认三星")
                            self.last_star = 3
                    self.click_btn(FIGHT_BTN["xiayibu"])
                    return 1
                else:
                    time.sleep(1)
                    continue
            elif self.is_exists(FIGHT_BTN["menu"], screen=sc, threshold=0.95):
                # 右上角有菜单，说明战斗还未结束
                return 0
            elif self.is_exists(FIGHT_BTN["xiayibu2"], screen=sc):
                # 右下角短的下一步：说明战斗胜利
                return 1
            elif self.is_exists(MAIN_BTN["tiaoguo"], screen=sc):
                # 检测到右上角跳过：点击 （羁绊剧情）
                self.click(MAIN_BTN["tiaoguo"])
                retry = 0
            elif check_xd and self.is_exists(MAOXIAN_BTN["xianding"]):
                if go_xd:
                    self.click_btn(MAOXIAN_BTN["xianding"])
                    return 3
                else:
                    self.click_btn(MAOXIAN_BTN["xianding_quxiao"])
                    return 1
            elif check_jq and self.is_exists(MAIN_BTN["speaker_box"], screen=sc, method="sq"):
                for _ in range(5):
                    self.click(471, 5, post_delay=0.1)
                retry = 0
                continue
            elif check_ghz and self.is_exists(MAOXIAN_BTN["tuanduizhan"]):
                self.click_btn(MAOXIAN_BTN["tuanduizhan_quxiao"])
                retry = 0
                continue
            else:
                time.sleep(delay)
                self.click(471, 5, post_delay=0.5)  # 避免奇怪的对话框
                continue
        return -1

    def get_fight_speed(self, screen=None, max_retry=3) -> int:
        """
        获取速度等级
        :param: screen 第一次检测用的截图
        :param max_retry: 最大重试次数
        :return:
            -1：检测失败
            0，1，2：原速、两倍速、三倍速
        """
        retry = 0
        while retry <= max_retry:
            retry += 1
            if screen is None:
                sc = self.getscreen()
            else:
                sc = screen
                screen = None
            state = self.get_fight_state(sc, max_retry=1)
            if state == -1:
                continue
            elif state in [1, 2]:
                return -1

            p0 = self.img_prob(FIGHT_BTN["speed_0"], screen=sc)
            p1 = self.img_prob(FIGHT_BTN["speed_1"], screen=sc)
            p2 = self.img_prob(FIGHT_BTN["speed_2"], screen=sc)
            probs = np.array([p0, p1, p2])
            if probs.max() < 0.84:
                continue
            else:
                return probs.argmax()
        return -1

    def set_fight_speed(self, level, max_level=1, screen=None, max_retry=3) -> bool:
        """
        调节速度等级
        :param level: 0,1,2。0：正常速，1：两倍速，2：三倍速
        :param max_level: 最大可以调节的速度,默认1（两倍速）
        :param: screen 第一次检测用的截图
        :param max_retry: 最大重试次数
        :return:
            True 设置成功
            False 可能未设置成功
        """
        retry = 0
        while retry <= max_retry:
            retry += 1
            if screen is None:
                sc = self.getscreen()
            else:
                sc = screen
                screen = None
            speed = self.get_fight_speed(sc)
            if speed == -1:
                return False
            else:
                # 获取速度成功
                if speed != level:
                    while speed != level:
                        speed = (speed + 1) % (max_level + 1)
                        self.click(FIGHT_BTN["speed_0"])
                    # 检查设置情况
                    time.sleep(0.2)
                    speed = self.get_fight_speed()
                    if speed == -1:
                        return False
                    elif speed == level:
                        # 设置成功
                        return True
                    else:
                        continue
                else:
                    return True
        # 超过最大尝试次数
        return False

    def get_fight_auto(self, screen=None, max_retry=3) -> int:
        """
        获取当前是否开着自动
        :param: screen 第一次检测用的截图
        :param max_retry: 最大重试次数
        :return:
            -1：识别失败
            0：未开
            1：开了
        """
        retry = 0
        while retry <= max_retry:
            retry += 1
            if screen is None:
                sc = self.getscreen()
            else:
                sc = screen
                screen = None
            state = self.get_fight_state(sc, max_retry=1)
            if state == -1:
                continue
            elif state in [1, 2]:
                return -1
            p0 = self.img_prob(FIGHT_BTN["auto_off"], screen=sc)
            p1 = self.img_prob(FIGHT_BTN["auto_on"], screen=sc)
            probs = np.array([p0, p1])
            if probs.max() < 0.84:
                continue
            else:
                return probs.argmax()
        return -1

    def set_fight_auto(self, auto, screen=None, max_retry=3) -> bool:
        """
        调节auto开关
        :param auto: 0：关闭 1：开启
        :param: screen 第一次检测用的截图
        :param max_retry: 最大重试次数
        :return:
            True 设置成功
            False 可能未设置成功
        """
        retry = 0
        while retry <= max_retry:
            retry += 1
            if screen is None:
                sc = self.getscreen()
            else:
                sc = screen
                screen = None
            cur = self.get_fight_auto(sc)
            if cur == -1:
                return False
            else:
                if cur != auto:
                    self.click(FIGHT_BTN["auto_off"])
                    # 检查设置情况
                    time.sleep(0.2)
                    cur = self.get_fight_auto()
                    if cur == -1:
                        return False
                    elif cur == auto:
                        # 设置成功
                        return True
                    else:
                        continue
                else:
                    return True
        # 超过最大尝试次数
        return False

    def set_fight_team(self, bianzu, duiwu):
        """
        设置战斗队伍
        要求场景：处于”队伍编组“情况下。
        :param bianzu: 编组编号1~5
        :param duiwu: 队伍编号1~3
        """
        assert bianzu in [1, 2, 3, 4, 5]
        assert duiwu in [1, 2, 3]
        self.click_btn(FIGHT_BTN["my_team"], until_disappear=FIGHT_BTN["zhandoukaishi"])
        self.click(FIGHT_BTN["team_h"][bianzu], pre_delay=1, post_delay=1)
        self.click(FIGHT_BTN["team_v"][duiwu], pre_delay=1, post_delay=1)

    def get_fight_current_member_count(self, screen=None):
        """
        获取”当前的成员"的数量
        要求场景：处于”队伍编组“情况下。
        :return: int 0~5
        """
        count_live = 5
        if screen is None:
            sc = self.getscreen()
        else:
            sc = screen
        for i in range(1, 6):
            cur = UIMatcher.img_cut(sc, FIGHT_BTN["empty"][i].at)
            if debug:
                print("std: ", i, cur.std())
            if cur.std() <= 15:
                count_live -= 1
        return count_live

    def set_fight_team_order(self, order="zhanli", change=2):
        """
        按照战力顺序设置战斗队伍
        order in ["zhanli","dengji","xingshu"]
        change:0-不换人 1-人全部换下不上 2-默认：全部换人
        要求场景：处于”队伍编组“情况下。
        """
        sc = self.getscreen()
        p0 = self.img_prob(FIGHT_BTN["sort_up"], screen=sc)
        p1 = self.img_prob(FIGHT_BTN["sort_down"], screen=sc)
        if p0 > p1:
            # 升序改降序
            self.click(FIGHT_BTN["sort_up"], pre_delay=0.5, post_delay=1)
        if order == "zhanli":
            if not self.is_exists(FIGHT_BTN["sort_power"]):
                self.click_btn(FIGHT_BTN["sort_power"], until_appear=FIGHT_BTN["cat_ok"])
                self.click(FIGHT_BTN["cat_zhanli"], pre_delay=0.5, post_delay=1)
                self.click_btn(FIGHT_BTN["cat_ok"])
        elif order == "dengji":
            if not self.is_exists(FIGHT_BTN["sort_level"]):
                self.click_btn(FIGHT_BTN["sort_level"], until_appear=FIGHT_BTN["cat_ok"])
                self.click(FIGHT_BTN["cat_dengji"], pre_delay=0.5, post_delay=1)
                self.click_btn(FIGHT_BTN["cat_ok"])
        elif order == "xingshu":
            if not self.is_exists(FIGHT_BTN["sort_star"]):
                self.click_btn(FIGHT_BTN["sort_star"], until_appear=FIGHT_BTN["cat_ok"])
                self.click(FIGHT_BTN["cat_star"], pre_delay=0.5, post_delay=1)
                self.click_btn(FIGHT_BTN["cat_ok"])
        # 换人3
        if change >= 1:
            for _ in range(5):
                self.click(FIGHT_BTN["empty"][1], post_delay=0.5)
        if change >= 2:
            for i in range(5):
                self.click(FIGHT_BTN["first_five"][i + 1], post_delay=0.5)

    def get_upperright_stars(self, screen=None):
        """
        获取右上角当前关卡的星星数
        :param screen: 设置为None时，不另外截屏
        :return: 0~3
        """
        if screen is None:
            screen = self.getscreen()
        fc = np.array([98, 228, 245])  # G B R:金色
        bc = np.array([212, 171, 139])  # G B R:灰色
        c = []
        us = FIGHT_BTN["upperright_stars"]
        for i in range(1, 4):
            x = us[i].x
            y = us[i].y
            c += [screen[y, x]]
        c = np.array(c)
        tf = np.sqrt(((c - fc) ** 2)).sum(axis=1)
        tb = np.sqrt(((c - bc) ** 2)).sum(axis=1)
        t = tf < tb
        return np.sum(t)
