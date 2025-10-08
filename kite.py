import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
import math
import re # noqa
from datetime import datetime # noqa
from datetime import timedelta

from DrissionPage._elements.none_element import NoneElement

from fun_glm import gene_by_llm

from fun_utils import ding_msg
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import format_ts

from fun_okx import OkxUtils
from fun_dp import DpUtils

from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_NUM_TRY
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_DATA_STATUS

from conf import TZ_OFFSET
from conf import DEL_PROFILE_DIR

from conf import FILENAME_LOG
from conf import logger

# gm Check-in use UTC Time
# TZ_OFFSET = 0

DEF_SUCCESS = 'Success'
DEF_FAIL = 'Fail'

"""
2025.10.02
"""


class ClsKiteAi():
    def __init__(self) -> None:
        self.args = None

        self.file_status = None

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}
        self.dic_account = {}

        self.inst_okx = OkxUtils()
        self.inst_dp = DpUtils()

        self.inst_dp.plugin_yescapcha = True
        self.inst_dp.plugin_capmonster = True
        self.inst_dp.plugin_okx = True

        # output
        self.DEF_HEADER_STATUS = 'account,xp,balance,quiz_date,claim_kite,badge,update_time' # noqa
        self.IDX_XP = 1
        self.IDX_BALANCE = 2
        self.IDX_QUIZ_DATE = 3
        self.IDX_CLAIM_KITE = 4
        self.IDX_BADGE = 5
        self.IDX_UPDATE = 6
        self.FIELD_NUM = self.IDX_UPDATE + 1

    def set_args(self, args):
        self.args = args
        self.is_update = False

    def __del__(self):
        pass
        # self.status_save()

    def get_status_file(self):
        if not self.args.url:
            logger.info('Invalid self.args.url')
            sys.exit(-1)
        filename = 'kite_ai'
        self.file_status = f'{DEF_PATH_DATA_STATUS}/kite_ai/{filename}.csv'

    def status_load(self):
        if self.file_status is None:
            self.get_status_file()

        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=self.DEF_HEADER_STATUS
        )

    def status_save(self):
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=self.DEF_HEADER_STATUS
        )

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.browser:
                try:
                    self.browser.quit()
                except Exception as e: # noqa
                    # logger.info(f'[Close] Error: {e}')
                    pass

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def save_screenshot(self, name):
        tab = self.browser.latest_tab
        # 对整页截图并保存
        # tab.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        tab.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def update_status(self, idx_status, s_value):
        update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        def init_status():
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
            ]
            for i in range(1, self.FIELD_NUM):
                self.dic_status[self.args.s_profile].append('')

        if self.args.s_profile not in self.dic_status:
            init_status()
        if len(self.dic_status[self.args.s_profile]) != self.FIELD_NUM:
            init_status()
        if self.dic_status[self.args.s_profile][idx_status] == s_value:
            return

        self.dic_status[self.args.s_profile][idx_status] = s_value
        self.dic_status[self.args.s_profile][self.IDX_UPDATE] = update_time

        self.status_save()
        self.is_update = True

    def get_status_by_idx(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        s_val = ''
        lst_pre = self.dic_status.get(s_profile, [])
        if len(lst_pre) == self.FIELD_NUM:
            try:
                # s_val = int(lst_pre[idx_status])
                s_val = lst_pre[idx_status]
            except: # noqa
                pass

        return s_val

    def update_date(self, idx_status, update_ts=None):
        if not update_ts:
            update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        claim_date = update_time[:10]

        self.update_status(idx_status, claim_date)

    def connect_wallet(self):
        n_tab = self.browser.tabs_count
        for i in range(1, DEF_NUM_TRY+1):
            tab = self.browser.latest_tab

            ele_btn = tab.ele('.dropdown dropdown-end', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, f'Wallet is connected before') # noqa
                return True

            ele_btn = tab.ele('.btn btn-outline w-40 btn-sm rounded-box mt-10', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                s_info = ele_btn.text
                self.logit(None, f'Connect Wallet Button Text: {s_info}') # noqa
                ele_btn.wait.enabled(timeout=5)
                ele_btn.wait.clickable(timeout=5)
                ele_btn.click(by_js=True)
                tab.wait(5)

                ele_btn = tab.ele('@@tag()=div@@class=sc-itBLYH deySMR@@text():OKX Wallet', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    if ele_btn.wait.clickable(timeout=5):
                        ele_btn.click()

                if self.inst_okx.wait_popup(n_tab+1, 10):
                    tab.wait(2)
                    self.inst_okx.okx_connect()
                    if self.inst_okx.wait_popup(n_tab, 5):
                        return True

            self.logit('connect_wallet', f'trying ... {i}/{DEF_NUM_TRY}')
            tab.wait(2)

        return False

    def click_verification(self):
        tab = self.browser.latest_tab
        for i in range(1, DEF_NUM_TRY+1):
            self.logit('click_verification', f'trying ... {i}/{DEF_NUM_TRY}')
            tab.wait(2)

            try:
                iframe = tab.get_frame('t:iframe')

                ele_btn = iframe.ele('@@tag()=span@@class:recaptcha-checkbox goog-inline-block', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    s_checked = ele_btn.attr('aria-checked')
                    if s_checked == 'false':
                        ele_btn = iframe('.rc-anchor-center-item rc-anchor-checkbox-holder', timeout=2) # noqa
                        ele_btn.click()
                    else:
                        return True
            except: # noqa
                pass

        return False

    def click_continue(self):
        tab = self.browser.latest_tab
        ele_blk = tab.ele('@@tag()=div@@class:flex flex-col md:flex-row justify-center', timeout=2) # noqa
        if not isinstance(ele_blk, NoneElement):
            ele_btn = ele_blk.ele('@@tag()=button@@text()=Continue', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                if ele_btn.wait.clickable(timeout=2):
                    ele_btn.click(by_js=True)
            tab.wait(2)

    def task_quiz(self, n_step, lst_answer=None):
        tab = self.browser.latest_tab
        lst_path = [
            '.flex-1 flex flex-col gap-4 min-w-[300px] md:min-w-[500px]',
            '@@tag()=div@@class:absolute w-full z-20 flex flex-col gap-4'
        ]
        ele_blk = self.inst_dp.get_ele_btn(tab, lst_path)
        if ele_blk is not NoneElement:
            lst_answer_ids = []
            for i in range(len(lst_answer)):
                s_answer = lst_answer[i]
                ascii_value = ord(s_answer)
                idx = ascii_value - ord('A')
                lst_answer_ids.append(f'radio-{n_step-1}-{s_answer}-{idx}')

            for i in range(len(lst_answer)):
                ele_info = ele_blk.ele(f'@@tag()=label@@for={lst_answer_ids[i]}', timeout=2) # noqa
                if not isinstance(ele_info, NoneElement):
                    s_info = ele_info.text
                    self.logit(None, f'Question info: {s_info}')
                    ele_info.click()

                ele_btn = ele_blk.ele('@@tag()=button@@type=submit', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    if ele_btn.wait.clickable(timeout=2):
                        ele_btn.click(by_js=True)
                    tab.wait(2)

            return True
        return False

    def get_answer_by_llm(self, s_question, lst_answer_options):
        lst_options = []
        lst_abc = ['A', 'B', 'C', 'D']
        for i in range(len(lst_abc)):
            s_option = lst_abc[i]
            s_answer_option = f'{s_option}: {lst_answer_options[i]}'
            lst_options.append(s_answer_option)
        s_options = '\n'.join(lst_options)

        s_prompt = (
            "# 【功能】\n"
            "选择题，根据题目和选项，选择正确的答案\n"
            "# 【要求】\n"
            "答案只能是 A、B、C、D 中的一个，不要输出分析过程，直接输出答案\n"
            "# 【题目如下】\n"
            f"{s_question}\n"
            "# 【选项如下】\n"
            f"{s_options}"
        )
        try:
            s_reply = gene_by_llm(s_prompt)
            s_reply = s_reply.strip()
            if not s_reply:
                self.logit(None, 's_reply from llm is empty, skip ...')
                return False
        except Exception as e:
            self.logit(None, f'Error calling gene_by_llm: {e}')
            return False

        # <|begin_of_box|>
        # <|end_of_box|>
        s_reply = s_reply.replace('<|begin_of_box|>', '').replace('<|end_of_box|>', '') # noqa
        self.logit('get_answer_by_llm', f's_reply from llm: {s_reply}')

        return s_reply

    def do_daily_quiz(self):
        tab = self.browser.latest_tab
        lst_path = [
            '.flex-1 flex flex-col gap-4 min-w-[300px] md:min-w-[500px]',
            '@@tag()=div@@class:absolute w-full z-20 flex flex-col gap-4'
        ]
        ele_blk = self.inst_dp.get_ele_btn(tab, lst_path)
        if ele_blk is not NoneElement:
            # 获取题目和选项，调用大模型获取答案

            ele_info = ele_blk.ele('@@tag()=h2', timeout=2) # noqa
            if not isinstance(ele_info, NoneElement):
                s_question = ele_info.text
                self.logit(None, f'Question info: {s_question}')
            else:
                self.logit(None, 'Question info is not found')
                return False
            lst_answer_options = []
            ele_labels = ele_blk.eles('@@tag()=label', timeout=2) # noqa
            for ele_label in ele_labels:
                s_info = ele_label.text
                self.logit(None, f'answer option info: {s_info}')
                lst_answer_options.append(s_info)

            # s_answer = 'B'
            lst_options = ['A', 'B', 'C', 'D']
            for i in range(15):
                s_answer = self.get_answer_by_llm(s_question, lst_answer_options) # noqa
                # 如果 s_answer 不是 A、B、C、D 中的一个，则继续获取
                if s_answer in lst_options:
                    break
                self.logit(None, f's_answer is not A、B、C、D, try again ... {i+1}/15') # noqa
                time.sleep(1)
            if s_answer not in lst_options:
                self.logit(None, 's_answer is not A、B、C、D [FAILED]')
                return False

            # 获取 s_answer 的 ASCII 值
            ascii_value = ord(s_answer)
            self.logit(None, f's_answer: {s_answer}, ASCII value: {ascii_value}') # noqa
            idx = ascii_value - ord('A')

            # A -> radio-A-0
            # B -> radio-B-1
            s_label_answer = f'radio-{s_answer}-{idx}'

            ele_info = ele_blk.ele(f'@@tag()=label@@for={s_label_answer}', timeout=2) # noqa
            if not isinstance(ele_info, NoneElement):
                s_info = ele_info.text
                self.logit(None, f'Question info: {s_info}')
                ele_info.click()

            ele_btn = ele_blk.ele('@@tag()=button@@type=submit', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                if ele_btn.wait.clickable(timeout=2):
                    if ele_btn.click(by_js=True):
                        return True
        return False

    def get_step_num(self):
        s_num = -1
        tab = self.browser.latest_tab
        ele_btn = tab.ele('@@tag()=div@@class:flex gap-2 items-center', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            s_text = ele_btn.text
            self.logit('get_step_num', f'Step Text: {s_text}')
            # Step1OF6, 提取 Step 和 OF 之间的数字
            try:
                s_num = re.search(r'Step(\d+)OF6', s_text).group(1)
                s_num = int(s_num)
            except: # noqa
                pass
        return s_num

    def finish_6_steps(self):
        tab = self.browser.latest_tab
        max_try = 90
        n_pre_step = -1
        for i in range(1, max_try+1):
            if i % 30 == 0:
                tab.refresh()
                tab.wait(3)
            self.logit('finish_6_steps', f'trying ... {i}/{max_try}')

            n_step = self.get_step_num()
            if n_step == -1:
                # 如果 Kite 图标加载完成，则返回 True
                tab.wait.doc_loaded()
                tab.wait(3)
                ele_info = tab.ele('@@tag()=img@@alt=KAA@@class:20dvh', timeout=2) # noqa
                if not isinstance(ele_info, NoneElement):
                    self.logit('finish_6_steps', 'Finished loading')
                    return True
                continue
            n_pre_step = n_step

            self.logit('finish_6_steps', f'Step {n_step}')
            if n_step in [1, 2]:
                self.click_continue()
            elif n_step == 3:
                self.task_quiz(n_step, lst_answer=['D'])
            elif n_step == 4:
                self.task_quiz(n_step, lst_answer=['B'])
            elif n_step == 5:
                self.task_quiz(n_step, lst_answer=['C'])
            elif n_step == 6:
                if self.task_quiz(n_step, lst_answer=['B']):
                    return True

            n_step = self.get_step_num()
            if n_step == n_pre_step:
                self.logit('finish_6_steps', 'Step is not changed, wait ...')
                tab.wait(2)
        return True

    def claim_badge(self):
        tab = self.browser.latest_tab
        ele_btn = tab.ele('@@tag()=span@@class:text@@text():BADGES', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            if ele_btn.wait.clickable(timeout=5):
                ele_btn.click()
                tab.wait(3)

        is_claimed = False
        s_val_badge = ''
        ele_btns = tab.eles('@@tag()=div@@class=flex justify-center mb-4', timeout=2) # noqa
        if len(ele_btns) > 0:
            for ele_btn in ele_btns:
                if ele_btn.wait.clickable(timeout=5):
                    ele_h3 = ele_btn.next()
                    ele_p = ele_h3.next()
                    s_h3 = ele_h3.text
                    s_p = ele_p.text
                    self.logit('badges', f'{s_h3}: {s_p}')
                    if 'Sorry' in s_p:
                        continue
                    # You’re eligible for this badge.
                    if ele_btn.wait.clickable(timeout=5):
                        ele_btn.click()
                        tab.wait(2)
                        ele_btn.click()
                        tab.wait(2)
                        ele_claim_btn = tab.ele('@@tag()=button@@class:btn bg-gradient-to-r@@text()=CLAIM BADGE', timeout=2) # noqa
                        if not isinstance(ele_claim_btn, NoneElement):
                            if ele_claim_btn.wait.clickable(timeout=5):
                                ele_claim_btn.click()
                                n_wait = 15
                                i = 0
                                while i < n_wait:
                                    i += 1
                                    self.logit('badges', f'Waiting for CLAIM BADGE ... {i}/{n_wait}') # noqa
                                    time.sleep(1)
                                    is_tag, s_text = self.inst_dp.get_tag_info_v2('p', 'YOU CLAIMED THIS ON') # noqa
                                    if is_tag:
                                        is_claimed = True
                                        break
                                tab.wait(2)

                is_tag, s_text = self.inst_dp.get_tag_info_v2('p', 'YOU CLAIMED THIS ON') # noqa
                if is_tag:
                    s_val_badge += f'{s_h3}[{s_text}];'

                ele_back_btn = tab.ele('@@tag()=button@@class=btn btn-outline@@text()=BACK', timeout=2) # noqa
                if not isinstance(ele_back_btn, NoneElement):
                    if ele_back_btn.wait.clickable(timeout=5):
                        ele_back_btn.click()

        s_val_badge = s_val_badge.strip(';')
        s_val_badge_pre = self.get_status_by_idx(self.IDX_BADGE)
        if is_claimed or s_val_badge_pre == '':
            self.update_status(self.IDX_BADGE, s_val_badge)
        return True

    def kite_ai_process(self):
        tab = self.browser.latest_tab
        # tab.set.window.max()
        # Connect wallet
        if self.connect_wallet() is False:
            return False

        # 首次登录，6 个 Step
        self.finish_6_steps()

        ele_btn = tab.ele('.dropdown dropdown-end', timeout=2)
        if not isinstance(ele_btn, NoneElement):
            if ele_btn.wait.clickable(timeout=5):
                ele_btn.click()

                ele_btn = tab.ele('.btn btn-block btn-outline', timeout=2)
                if not isinstance(ele_btn, NoneElement):
                    if ele_btn.wait.clickable(timeout=5):
                        ele_btn.click()
                    else:
                        self.logit('kite_ai_process', 'Button CLAIM TESTNET TOKENS is not clickable') # noqa
                        return False

                ele_btn = tab.ele('.rc-anchor-center-item rc-anchor-checkbox-holder', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    if ele_btn.wait.clickable(timeout=5):
                        ele_btn.click()

                max_wait_sec = 20
                i = 0
                while i < max_wait_sec:
                    i += 1
                    self.logit(None, f'Wait to click verification ... {i}/{max_wait_sec}') # noqa

                    if self.click_verification():
                        ele_btn = tab.ele('@@tag()=button@@class:btn btn-block bg-gradient-to-r', timeout=2) # noqa
                        if ele_btn.wait.clickable(timeout=5):
                            if ele_btn.click():
                                max_wait_sec = 20
                                i = 0
                                while i < max_wait_sec:
                                    i += 1
                                    self.logit('kite_ai_process', f'Waiting for CLAIM Status ... {i}/{max_wait_sec}') # noqa
                                    time.sleep(1)
                                    if self.get_tag_info('div', 'successfully'): # noqa
                                        self.update_status(self.IDX_CLAIM_KITE, format_ts(time.time(), style=2, tz_offset=TZ_OFFSET)) # noqa
                                        return True
                                    elif self.get_tag_info('div', 'Already'):
                                        return True

                                break

                    else:
                        tab.wait(1)
        else:
            self.logit('kite_ai_process', 'dropdown menu is not found') # noqa
            return False

        return True

    def get_tag_info(self, s_tag, s_text):
        """
        s_tag:
            span
            div
        """
        tab = self.browser.latest_tab
        s_path = f'@@tag()={s_tag}@@text():{s_text}'
        ele_info = tab.ele(s_path, timeout=1)
        if not isinstance(ele_info, NoneElement):
            # self.logit(None, f'[html] {s_text}: {ele_info.html}')
            s_info = ele_info.text.replace('\n', ' ')
            self.logit(None, f'[info][{s_tag}] {s_text}: {s_info}')
            return True
        return False

    def get_notification(self):
        tab = self.browser.latest_tab
        ele_info = tab.ele('@@tag()=section@@aria-label:Notifications', timeout=2) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.text
            self.logit('get_notification', f'Notification: {s_info}')
            return s_info
        return ''

    def get_xp_balance(self):
        tab = self.browser.latest_tab

        ele_info = tab.ele('@@tag()=div@@class=join border rounded-box bg-accent', timeout=2) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.text
            s_xp, s_balance = s_info.split('XP\n')
            s_xp = s_xp.strip()
            s_balance = s_balance.strip()
            self.logit('get_xp', f'XP: {s_info}')
            return (s_xp, s_balance)
        return ('', '')

    def daily_quiz(self):
        s_quiz_date = self.get_status_by_idx(self.IDX_QUIZ_DATE)[:10]
        s_current_date = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET)
        if s_quiz_date == s_current_date:
            return True

        b_to_submit = False
        tab = self.browser.latest_tab
        ele_btn = tab.ele('@@tag()=span@@class:text@@text():QUIZ', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            if ele_btn.wait.clickable(timeout=5):
                ele_btn.click()

                max_wait_sec = 10
                i = 0
                while i < max_wait_sec:
                    i += 1
                    self.logit('daily_quiz', f'Waiting for button submit ... {i}/{max_wait_sec}') # noqa
                    ele_btn = tab.ele('@@tag()=button@@type=submit', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        if ele_btn.wait.clickable(timeout=2):
                            b_to_submit = True
                            break
                    time.sleep(1)

                ele_selected = tab.ele('@@tag()=input@@checked@@name=radio', timeout=2) # noqa
                if not isinstance(ele_selected, NoneElement):
                    b_to_submit = False

                if b_to_submit is False:
                    self.logit('daily_quiz', 'QUIZ is done before') # noqa
                    return True

                if self.do_daily_quiz():
                    n_wait = 30
                    for i in range(1, n_wait+1):
                        self.logit('daily_quiz', f'Waiting for notification ... {i}/{n_wait}') # noqa
                        is_tag = self.inst_dp.get_tag_info('div', 'Congratulations') # noqa
                        is_tag = is_tag or self.inst_dp.get_tag_info('div', 'answer') # noqa
                        if is_tag:
                            self.update_status(self.IDX_QUIZ_DATE, format_ts(time.time(), style=2, tz_offset=TZ_OFFSET)) # noqa
                            time.sleep(2)
                            return True
        return False

    def kite_ai_run(self):
        self.browser = self.inst_dp.get_browser(self.args.s_profile)

        self.inst_okx.set_browser(self.browser)

        if self.inst_dp.init_capmonster() is False:
            return False

        if self.inst_dp.init_yescaptcha() is False:
            return False

        if self.inst_okx.init_okx(is_bulk=True) is False:
            return False

        tab = self.browser.new_tab(self.args.url)
        tab.wait.doc_loaded()
        tab.wait(5)
        self.inst_dp.init_window_size()

        max_try = 5
        for i in range(1, max_try+1):
            self.logit('kite_ai_run', f'trying ... {i}/{max_try}')
            if self.kite_ai_process():
                break
            else:
                time.sleep(2)

        self.daily_quiz()

        # generate a random number
        random_num = random.randint(1, 9)
        if random_num % 2 == 0:
            self.logit('kite_ai_run', f'random_num is {random_num}, Claim badge') # noqa
            self.claim_badge()
        else:
            self.logit('kite_ai_run', f'random_num is {random_num}, Not claim badge') # noqa

        self.update_status(self.IDX_XP, self.get_xp_balance()[0])
        self.update_status(self.IDX_BALANCE, self.get_xp_balance()[1])

        if self.args.manual_exit:
            s_msg = 'Manual Exit. Press any key to exit! ⚠️' # noqa
            input(s_msg)

        self.logit('kite_ai_run', 'Finished!')

        return True


def send_msg(inst_kite_ai, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            lst_status = None
            if s_profile in inst_kite_ai.dic_status:
                lst_status = inst_kite_ai.dic_status[s_profile]

            if lst_status is None:
                lst_status = [s_profile, -1]

            s_info += '- {},{}\n'.format(
                s_profile,
                lst_status[inst_kite_ai.IDX_UPDATE],
            )
        d_cont = {
            'title': 'kite_ai Task Finished! [kite_ai]',
            'text': (
                'kite_ai Task\n'
                '- account,task_status\n'
                '{}\n'
                .format(s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def show_msg(args):
    current_directory = os.getcwd()
    FILE_LOG = f'{current_directory}/{FILENAME_LOG}'
    FILE_STATUS = f'{current_directory}/{DEF_PATH_DATA_STATUS}/status.csv'

    print('########################################')
    print('The program is running')
    print(f'headless={args.headless}')
    print('Location of the running result file:')
    print(f'{FILE_STATUS}')
    print('The running process is in the log file:')
    print(f'{FILE_LOG}')
    print('########################################')


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    inst_kite_ai = ClsKiteAi()
    inst_kite_ai.set_args(args)

    args.s_profile = 'ALL'
    inst_kite_ai.inst_okx.set_args(args)
    inst_kite_ai.inst_okx.purse_load(args.decrypt_pwd)

    # 检查 profile 参数冲突
    if args.profile and (args.profile_begin is not None or args.profile_end is not None): # noqa
        logger.info('参数 --profile 与 --profile_begin/--profile_end 不能同时使用！')
        sys.exit(1)

    if len(args.profile) > 0:
        items = args.profile.split(',')
    elif args.profile_begin is not None and args.profile_end is not None:
        # 生成 profile_begin 到 profile_end 的 profile 列表
        prefix = re.match(r'^[a-zA-Z]+', args.profile_begin).group()
        start_num = int(re.search(r'\d+', args.profile_begin).group())
        end_num = int(re.search(r'\d+', args.profile_end).group())
        num_width = len(re.search(r'\d+', args.profile_begin).group())
        items = [f"{prefix}{str(i).zfill(num_width)}" for i in range(start_num, end_num + 1)] # noqa
        logger.info(f'Profile list: {items}')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(inst_kite_ai.inst_okx.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    def is_complete(lst_status):
        if args.force:
            return False

        b_ret = True
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET)

        if lst_status:
            lst_idx = [inst_kite_ai.IDX_QUIZ_DATE, inst_kite_ai.IDX_UPDATE]
            # lst_idx = [inst_kite_ai.IDX_UPDATE]
            for idx_status in lst_idx:
                s_date = lst_status[idx_status][:10]
                if date_now != s_date:
                    b_ret = b_ret and False
        else:
            b_ret = False

        return b_ret

    # 将已完成的剔除掉
    inst_kite_ai.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in inst_kite_ai.dic_status:
            lst_status = inst_kite_ai.dic_status[s_profile]

            if is_complete(lst_status):
                n += 1
                profiles.pop(i)

        else:
            continue
    logger.info('#'*40)

    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa

        if percent > args.max_percent:
            logger.info(f'Progress is more than threshold {percent}% > {args.max_percent}% [{n}/{total}] [{s_profile}]') # noqa
            break

        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in inst_kite_ai.inst_okx.dic_purse:
            logger.info(f'{s_profile} is not in okx account conf [ERROR]')
            sys.exit(0)

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                if j > 1:
                    logger.info(f'⚠️ 正在重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                inst_kite_ai.set_args(args)
                inst_kite_ai.inst_dp.set_args(args)
                inst_kite_ai.inst_okx.set_args(args)

                if s_profile in inst_kite_ai.dic_status:
                    lst_status = inst_kite_ai.dic_status[s_profile]
                else:
                    lst_status = None

                if is_complete(lst_status):
                    logger.info(f'[{s_profile}] Last update at {lst_status[inst_kite_ai.IDX_UPDATE]}') # noqa
                    break
                else:
                    b_ret = inst_kite_ai.kite_ai_run()
                    inst_kite_ai.close()
                    if b_ret:
                        lst_success.append(s_profile)
                        break

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                inst_kite_ai.close()
                if j < max_try_except:
                    time.sleep(5)

        if inst_kite_ai.is_update is False:
            continue

        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile} Finish]')
        if percent > args.max_percent:
            continue

        if len(profiles) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))

            # 输出下次执行时间，格式为 YYYY-MM-DD HH:MM:SS
            next_exec_time = datetime.now() + timedelta(seconds=sleep_time)
            logger.info(f'next_exec_time: {next_exec_time.strftime("%Y-%m-%d %H:%M:%S")}') # noqa
            time.sleep(sleep_time)

    send_msg(inst_kite_ai, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    parser.add_argument(
        '--profile_begin', required=False, default=None,
        help='按指定的 profile 开始后缀(包含) eg: g01'
    )
    parser.add_argument(
        '--profile_end', required=False, default=None,
        help='按指定的 profile 结束后缀(包含) eg: g05'
    )

    parser.add_argument(
        '--decrypt_pwd', required=False, default='',
        help='decrypt password'
    )
    # 不使用 X
    parser.add_argument(
        '--no_x', required=False, action='store_true',
        help='Not use X account'
    )
    parser.add_argument(
        '--auto_like', required=False, action='store_true',
        help='Like a post after login automatically'
    )
    parser.add_argument(
        '--auto_appeal', required=False, action='store_true',
        help='Auto appeal when account is suspended'
    )
    parser.add_argument(
        '--force', required=False, action='store_true',
        help='Run ignore status'
    )
    parser.add_argument(
        '--manual_exit', required=False, action='store_true',
        help='Close chrome manual'
    )
    # 添加 --headless 参数
    parser.add_argument(
        '--headless',
        action='store_true',   # 默认为 False，传入时为 True
        default=False,         # 设置默认值
        help='Enable headless mode'
    )
    # 添加 --no-headless 参数
    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',  # 指定与 --headless 参数共享同一个变量
        help='Disable headless mode'
    )
    parser.add_argument(
        '--url', required=False, default='',
        help='kite_ai url'
    )
    parser.add_argument(
        '--get_task_status', required=False, action='store_true',
        help='Check task result'
    )
    # 添加 --max_percent 参数
    parser.add_argument(
        '--max_percent', required=False, default=100, type=int,
        help='[默认为 100] 执行的百分比'
    )
    parser.add_argument(
        '--only_gm', required=False, action='store_true',
        help='Only do gm checkin'
    )
    parser.add_argument(
        '--set_window_size', required=False, default='max',
        help='[默认为 normal] 窗口大小，normal 为正常，max 为最大化'
    )
    # 清除 X Cookie
    parser.add_argument(
        '--clear_x_cookie', required=False, action='store_true',
        help='Clear X Cookie'
    )

    args = parser.parse_args()
    show_msg(args)

    if args.only_gm:
        args.no_x = True
        logger.info('-'*40)
        logger.info('Only do gm checkin, set no_x=True')

    if args.loop_interval <= 0:
        main(args)
    elif len(args.profile) > 0:
        main(args)
    else:
        while True:
            main(args)

            if args.get_task_status:
                break

            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
# noqa
python kite.py --url=https://testnet.gokite.ai/ --manual_exit --profile=g01

"""
