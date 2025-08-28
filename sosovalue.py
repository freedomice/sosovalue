from dotenv import load_dotenv
from basefunc.item_json import load_json
from basefunc.item_human_behavior import human_click, human_typing, human_delay
from morelogin.morelogin_env_control import startEnv, stopEnv
from morelogin.morelogin_okxwallet_load import login_okx_wallet
from cf_turnstile.Solvium_API import get_token
import asyncio
import os
import sys
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException,StaleElementReferenceException
from selenium.webdriver.common.by import By
import base64
import time
from PIL import Image
from io import BytesIO
import pytesseract
import json
import random
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from basefunc.item_logger_util import get_logger
from selenium.webdriver.common.action_chains import ActionChains

# 这里是你原本的logger初始化
logger = get_logger(__name__)

SITE_URL = "https://sosovalue.com/"
SITE_KEY = "0x4AAAAAAA4PZrjDa5PcluqN"

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 载入.env中的环境变量
load_dotenv()

# 确保是相对于当前脚本所在目录，不是 cwd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

appid = os.getenv("APPID")
secretkey = os.getenv("SECRETKEY")
encryptkey = os.getenv("ENCRYPTKEY")
baseurl = os.getenv("BASEURL")

load_dotenv()  # 默认读取根目录 .env 文件

# 多语言按钮字典
BUTTON_TEXTS = {
    "listen": ["Listen Now", "立即收听", "立即收聽"],
    "like": ["Like", "点赞", "點贊"],
    "share": ["Share", "分享", "分享"],
    "verify": ["Verify", "验证", "驗證"],
    "done": ["done", "完成", "Done"],
    "watch":["Watch", "观看", "觀看"],
    "quote": ["Quote", "引用", "引用"],
    "reply": ["Reply", "回复", "回答"],
    "visit": ["Visit", "访问", "訪問"],
    "follow": ["Follow", "关注", "關注"],
    "listen1": ["Listen", "听一听", "聽一聽"],
    "daily_task": ["每日任务", "每日任務", "Daily Task"], # 新增每日任务按钮文本
    "starter_pack": ["新手礼包", "新手禮包", "Starter Pack"] # 新增新手礼包按钮文本
    #"buy": ["Buy", "购买", "購買"]
}

# 选中状态的 CSS 类名
ACTIVE_TAB_CLASS = "text-[#FF7637]"

class SosoValueAutomation:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.short_wait = WebDriverWait(driver, 3)
        self.original_window = None
        self.target_window = None

    def sosovalue_exp_login(self, url):
        """
        1. 打开目标网页
        """
        try:
            # 保存原始窗口句柄
            self.original_window = self.driver.current_window_handle
            
            # 打开新标签页
            self.driver.execute_script("window.open('');")
            
            # 切换到新标签页并记录为目标窗口
            self.target_window = self.driver.window_handles[-1]
            self.driver.switch_to.window(self.target_window)
            
            # 访问 sosovalue 网站
            self.driver.get(url)
            logger.info(f"成功打开网页: {url}")
            logger.info(f"目标窗口句柄: {self.target_window}")
            
            # 等待页面加载
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"打开网页失败: {e}")
            return False

    def find_exp_button(self):
        """
        2. 搜索exp按钮，使用更精确的选择器
        """
        try:
            # 多种选择器策略来查找EXP按钮
            exp_selectors = [
                # 原始选择器
                "span[class*='text-base'][class*='mr-2'][class*='font-bold']",
                # 更具体的选择器
                "span[class*='text-transparent'][class*='bg-clip-text']",
                # 包含Exp文本的span
                "span:contains('Exp')",
                # 通过父元素查找
                "div[class*='flex'] span[class*='font-bold']"
            ]
            
            for selector in exp_selectors:
                try:
                    if ":contains" in selector:
                        # 使用XPath来查找包含文本的元素
                        elements = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'Exp')]")
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        element_text = element.text.strip()
                        if "Exp" in element_text and any(char.isdigit() for char in element_text):
                            logger.info(f"找到EXP按钮: {element_text}")
                            return element
                            
                except Exception as e:
                    logger.debug(f"选择器 {selector} 查找失败: {e}")
                    continue
            
            # 最后使用XPath通过文本内容查找
            try:
                xpath_selector = "//span[contains(text(), 'Exp') or contains(text(), 'EXP')]"
                elements = self.driver.find_elements(By.XPATH, xpath_selector)
                for element in elements:
                    if element.text.strip():
                        logger.info(f"通过XPath找到EXP按钮: {element.text}")
                        return element
            except Exception as e:
                logger.debug(f"XPath查找EXP按钮失败: {e}")
            
            logger.info("未找到EXP按钮")
            return None
            
        except Exception as e:
            logger.error(f"查找EXP按钮失败: {e}")
            return None

    def get_container_buttons(self):
        """
        获取所有容器按钮 - 改进的查找逻辑
        """
        try:
            container_buttons = []
            
            # 等待页面稳定
            time.sleep(1)
            
            # 多种策略查找按钮
            button_selectors = [
                "button",  # 所有button元素
                "[role='button']",  # 具有button角色的元素
                "div[class*='MuiButton']",  # MUI按钮
                "a[class*='button']"  # 链接按钮
            ]
            
            all_buttons = []
            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_buttons.extend(buttons)
                except:
                    continue
            
            # 去重
            unique_buttons = []
            seen_elements = set()
            for button in all_buttons:
                try:
                    # 使用元素的位置和大小作为唯一标识
                    element_id = (button.location['x'], button.location['y'], 
                                button.size['width'], button.size['height'])
                    if element_id not in seen_elements:
                        seen_elements.add(element_id)
                        unique_buttons.append(button)
                except:
                    continue
            
            # 分析按钮文本
            for button in unique_buttons:
                try:
                    # 跳过不可见的按钮
                    if not button.is_displayed():
                        continue
                        
                    button_text = button.text.strip()
                    if not button_text:
                        continue
                    
                    # 检查按钮文本是否匹配预定义的类型
                    for button_type, texts in BUTTON_TEXTS.items():
                        if button_text in texts:
                            # 检查按钮状态
                            is_disabled = button.get_attribute("disabled") == "true"
                            is_clickable = button.is_enabled() and button.is_displayed()
                            
                            container_buttons.append({
                                'element': button,
                                'text': button_text,
                                'type': button_type,
                                'is_disabled': is_disabled,
                                'is_clickable': is_clickable
                            })
                            logger.info(f"找到按钮: {button_text} (类型: {button_type}, 可点击: {is_clickable})")
                            break
                            
                except StaleElementReferenceException:
                    logger.debug("按钮元素已过期，跳过")
                    continue
                except Exception as e:
                    logger.debug(f"分析按钮失败: {e}")
                    continue
            
            logger.info(f"总共找到 {len(container_buttons)} 个有效容器按钮")
            return container_buttons
            
        except Exception as e:
            logger.error(f"获取容器按钮失败: {e}")
            return []
    
    def find_task_tabs(self):
        """
        新增函数：检查页面上是否存在每日任务或新手礼包标签页
        """
        try:
            # 结合每日任务和新手礼包的文本
            tab_texts = BUTTON_TEXTS["daily_task"] + BUTTON_TEXTS["starter_pack"]
            
            # 使用XPath来寻找包含特定文本的div元素
            xpath_selector = " | ".join([f"//div[contains(text(), '{text}')]" for text in tab_texts])
            
            tab_elements = self.driver.find_elements(By.XPATH, xpath_selector)
            
            # 过滤掉不可见的元素
            visible_tabs = [tab for tab in tab_elements if tab.is_displayed()]
            
            if visible_tabs:
                logger.info("检测到每日任务或新手礼包标签页。")
                return True
            
            logger.info("未检测到每日任务或新手礼包标签页。")
            return False
        except Exception as e:
            logger.error(f"查找任务标签页失败: {e}")
            return False

    def should_click_exp_button(self, exp_element):
        """
        判断是否应该点击EXP按钮 - 改进的逻辑
        """
        try:
            if not exp_element:
                return False
            
            # 检查页面上是否存在每日任务或新手礼包标签页
            task_tabs_found = self.find_task_tabs()
            
            if task_tabs_found:
                # 同时有EXP按钮和任务标签，说明已在目标页面
                logger.info("页面同时有EXP按钮和任务标签页，说明已在目标页面")
                return False
            else:
                # 没有任务标签页，需要点击EXP按钮进入
                logger.info("未找到任务标签页，需要点击EXP按钮进入目标页面")
                return True
                
        except Exception as e:
            logger.error(f"判断是否点击EXP按钮失败: {e}")
            return False

    def click_exp_button(self, exp_element):
        """
        点击EXP按钮 - 改进的点击逻辑
        """
        try:
            logger.info("准备点击EXP按钮")
            
            # 尝试滚动到元素可见位置
            self.driver.execute_script("arguments[0].scrollIntoView(true);", exp_element)
            time.sleep(1)
            
            # 多种点击方式
            click_methods = [
                lambda: exp_element.click(),  # 直接点击
                lambda: self.driver.execute_script("arguments[0].click();", exp_element),  # JS点击
                lambda: self.wait.until(EC.element_to_be_clickable(exp_element)).click()  # 等待可点击后点击
            ]
            
            for i, click_method in enumerate(click_methods):
                try:
                    logger.info(f"尝试第 {i+1} 种点击方式")
                    click_method()
                    logger.info("EXP按钮点击成功")
                    time.sleep(3)  # 等待页面加载
                    return True
                except Exception as e:
                    logger.warning(f"第 {i+1} 种点击方式失败: {e}")
                    if i < len(click_methods) - 1:
                        time.sleep(1)
                        continue
                    else:
                        raise e
                        
        except Exception as e:
            logger.error(f"点击EXP按钮失败: {e}")
            return False

    def find_and_click_tab(self, tab_type):
        """
        根据类型查找并点击标签页（每日任务/新手礼包）
        """
        try:
            # 寻找所有可能的标签页元素
            tab_texts = BUTTON_TEXTS.get(tab_type, [])
            if not tab_texts:
                logger.error(f"未找到类型 {tab_type} 的按钮文本配置")
                return False
            
            # 使用XPath来寻找包含特定文本的div元素
            xpath_selector = " | ".join([f"//div[contains(text(), '{text}')]" for text in tab_texts])
            
            tab_elements = self.driver.find_elements(By.XPATH, xpath_selector)
            
            if not tab_elements:
                logger.warning(f"未找到 {tab_texts} 标签页")
                return False
            
            for tab in tab_elements:
                if tab.is_displayed() and tab.is_enabled():
                    # 再次通过文本内容进行精确匹配
                    if tab.text.strip() in tab_texts:
                        logger.info(f"找到并准备点击 {tab.text.strip()} 标签页")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", tab)
                        logger.info(f"成功点击 {tab.text.strip()} 标签页")
                        time.sleep(3) # 等待页面内容加载
                        return True
            
            logger.warning(f"找到的 {tab_texts} 标签页不可点击或不可见")
            return False
            
        except Exception as e:
            logger.error(f"点击 {tab_type} 标签页失败: {e}")
            return False

    def check_and_close_popup(self):
        """
        新增函数：检查并关闭可能拦截点击的弹窗或透明遮罩层
        """
        try:
            # 查找可能包含弹窗或遮罩层的元素
            # 策略1: 查找已知的弹窗容器类
            popup_containers = self.driver.find_elements(By.CSS_SELECTOR, ".MuiDialog-container")
            # 策略2: 查找具有高z-index和绝对定位的透明遮罩层
            overlay_selectors = [
                "div.absolute.w-full.bg-\\[transparent\\][style*='z-index']", # 针对你提供的具体遮罩层
                "div.absolute.top-0.left-0.w-full.h-full"  # 另一种可能的通用遮罩层
            ]
            for selector in overlay_selectors:
                popup_containers.extend(self.driver.find_elements(By.CSS_SELECTOR, selector))

            if not popup_containers:
                logger.info("未检测到弹窗或遮罩层，继续。")
                return True

            for element in popup_containers:
                if element.is_displayed():
                    logger.info("检测到弹窗或遮罩层，尝试使用JS强制隐藏。")
                    try:
                        self.driver.execute_script("arguments[0].style.display = 'none';", element)
                        logger.info("成功隐藏弹窗/遮罩层。")
                        time.sleep(1) # 等待页面反应
                        return True
                    except Exception as e:
                        logger.error(f"强制隐藏元素失败: {e}")
                        # 如果强制隐藏失败，尝试之前的点击空白处方法作为备用
                        try:
                            logger.info("强制隐藏失败，尝试点击空白处。")
                            ActionChains(self.driver).move_by_offset(1, 1).click().perform()
                            logger.info("成功模拟点击空白处，弹窗应已关闭。")
                            time.sleep(1)
                            return True
                        except Exception as e:
                            logger.error(f"模拟点击空白处失败: {e}")
                            return False

            return True
            
        except Exception as e:
            logger.error(f"处理弹窗时发生错误: {e}")
            return False

    def click_button_and_handle_result(self, button_info):
        """
        点击按钮并处理结果 - 改进的错误处理
        """
        try:
            # 在尝试点击按钮前，先检查并关闭任何弹窗
            if not self.check_and_close_popup():
                logger.warning("因弹窗未能关闭，跳过当前按钮点击。")
                return False, False
                
            button = button_info['element']
            button_type = button_info['type']
            button_text = button_info['text']
            
            logger.info(f"准备点击按钮: {button_text} (类型: {button_type})")
            
            # 检查按钮是否仍然有效
            try:
                if not button.is_displayed() or not button.is_enabled():
                    logger.warning(f"按钮 {button_text} 不可点击")
                    return False, False
            except StaleElementReferenceException:
                logger.warning(f"按钮 {button_text} 元素已过期")
                return False, False
            
            # 保存点击前的窗口句柄
            original_handles = self.driver.window_handles.copy()
            
            # 滚动到按钮位置
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(0.5)
            except:
                pass
            
            # 尝试多种点击方式
            click_success = False
            for attempt in range(3):
                try:
                    if attempt == 0:
                        # 普通点击
                        button.click()
                    elif attempt == 1:
                        # JavaScript点击
                        self.driver.execute_script("arguments[0].click();", button)
                    else:
                        # 等待可点击后点击
                        clickable_button = self.wait.until(EC.element_to_be_clickable(button))
                        clickable_button.click()
                    
                    click_success = True
                    logger.info(f"按钮 {button_text} 点击成功 (方式 {attempt + 1})")
                    break
                    
                except Exception as e:
                    logger.warning(f"点击方式 {attempt + 1} 失败: {e}")
                    if attempt < 2:
                        time.sleep(1)
                    else:
                        raise e
            
            if not click_success:
                return False, False
            
            # 等待页面反应
            time.sleep(2)
            
            # 检查是否打开了新标签页
            new_handles = self.driver.window_handles
            new_tab_opened = len(new_handles) > len(original_handles)
            
            if new_tab_opened:
                logger.info("检测到新标签页被打开，关闭新标签页并返回目标窗口")
                if self.close_new_tabs_and_return_to_target(original_handles):
                    return True, True
                else:
                    logger.error("处理新标签页失败")
                    return False, True
            else:
                logger.info("未检测到新标签页，页面可能已刷新或出现验证")
                # 确保仍在目标窗口
                self.switch_back_to_target_window()
                # 检查是否出现验证相关元素
                self.handle_verification()
                return True, False
                
        except Exception as e:
            logger.error(f"点击按钮失败: {e}")
            # 确保在出错时也能返回目标窗口
            try:
                self.switch_back_to_target_window()
            except:
                pass
            return False, False

    def handle_verification(self):
        """
        处理验证流程 - 改进的验证检测
        """
        try:
            # 等待页面稳定
            time.sleep(2)
            
            # 查找验证按钮 - 使用多种策略
            verification_found = False
            
            # 策略1: 通过按钮文本查找
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in all_buttons:
                try:
                    button_text = button.text.strip()
                    if button_text in BUTTON_TEXTS["verify"]:
                        logger.info(f"找到验证按钮: {button_text}")
                        if button.is_displayed() and button.is_enabled():
                            self.driver.execute_script("arguments[0].click();", button)
                            logger.info("验证按钮点击成功")
                            verification_found = True
                            time.sleep(2)  # 等待验证结果
                            break
                except:
                    continue
            
            # 策略2: 通过CSS类名查找验证相关元素
            if not verification_found:
                verify_selectors = [
                    "button[class*='verify']",
                    "div[class*='verify'] button",
                    "*[class*='verification'] button"
                ]
                
                for selector in verify_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"通过选择器找到验证按钮: {selector}")
                                self.driver.execute_script("arguments[0].click();", element)
                                verification_found = True
                                time.sleep(2)
                                break
                    except:
                        continue
                    
                    if verification_found:
                        break
            
            # 检查验证结果
            if verification_found:
                self.check_verification_result()
            
        except Exception as e:
            logger.error(f"处理验证失败: {e}")

    def check_verification_result(self):
        """
        检查验证结果 - 改进的结果检测
        """
        try:
            # 等待验证结果
            time.sleep(2)
            
            # 检查验证失败的多种可能标识
            failure_indicators = [
                "验证失败",
                "verification failed",
                "验證失敗",
                "failed",
                "error"
            ]
            
            # 查找可能包含验证结果的元素
            result_selectors = [
                "h1",
                "div[class*='text-2xl']",
                "div[class*='font-bold']",
                "*[class*='modal']",
                "*[class*='dialog']",
                "*[class*='popup']"
            ]
            
            verification_failed = False
            
            for selector in result_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        element_text = element.text.strip().lower()
                        for indicator in failure_indicators:
                            if indicator.lower() in element_text:
                                logger.warning(f"检测到验证失败: {element.text}")
                                verification_failed = True
                                break
                        if verification_failed:
                            break
                except:
                    continue
                    
                if verification_failed:
                    break
            
            # 如果验证失败，尝试关闭弹窗
            if verification_failed:
                close_selectors = [
                    "div[class*='cursor-pointer'] svg",
                    "button[class*='close']",
                    "*[class*='close']",
                    "svg[class*='close']"
                ]
                
                for selector in close_selectors:
                    try:
                        close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if close_buttons:
                            for close_btn in close_buttons:
                                if close_btn.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", close_btn)
                                    logger.info("关闭验证失败弹窗")
                                    time.sleep(1)
                                    return False
                    except:
                        continue
                
                return False
            
            logger.info("验证处理完成")
            return True
            
        except Exception as e:
            logger.error(f"检查验证结果失败: {e}")
            return False
            
    def switch_back_to_target_window(self):
        """
        切换回目标操作窗口 - 改进的窗口管理
        """
        try:
            current_handles = self.driver.window_handles
            
            # 检查目标窗口是否仍然存在
            if self.target_window and self.target_window in current_handles:
                self.driver.switch_to.window(self.target_window)
                logger.debug("成功切换回目标操作窗口")
                return True
            else:
                # 目标窗口不存在，尝试重新确定目标窗口
                logger.warning("目标窗口句柄无效，尝试重新确定目标窗口")
                
                # 如果只有一个窗口，就使用它
                if len(current_handles) == 1:
                    self.target_window = current_handles[0]
                    self.driver.switch_to.window(self.target_window)
                    logger.info("重新设置目标窗口")
                    return True
                    
                # 如果有多个窗口，选择非原始窗口
                for handle in current_handles:
                    if handle != self.original_window:
                        self.target_window = handle
                        self.driver.switch_to.window(self.target_window)
                        logger.info("重新设置目标窗口")
                        return True
                
                logger.error("无法确定有效的目标窗口")
                return False
                
        except Exception as e:
            logger.error(f"切换回目标窗口失败: {e}")
            return False

    def close_new_tabs_and_return_to_target(self, original_handles):
        """
        关闭所有新打开的标签页，并返回目标窗口
        """
        try:
            current_handles = self.driver.window_handles
            new_tabs_closed = 0
            
            # 关闭所有新打开的标签页
            for handle in current_handles:
                if handle not in original_handles:
                    try:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                        new_tabs_closed += 1
                        logger.info(f"关闭新标签页: {handle}")
                    except Exception as e:
                        logger.warning(f"关闭标签页失败: {e}")
            
            # 切换回目标窗口
            if self.switch_back_to_target_window():
                logger.info(f"成功关闭 {new_tabs_closed} 个新标签页并返回目标窗口")
                return True
            else:
                logger.error("无法返回目标窗口")
                return False
                
        except Exception as e:
            logger.error(f"关闭新标签页并返回失败: {e}")
            return False

    def close_current_tab_and_return(self):
        """
        关闭当前标签页并返回原窗口
        """
        try:
            if self.target_window and self.target_window in self.driver.window_handles:
                self.driver.switch_to.window(self.target_window)
                self.driver.close()
                logger.info("关闭目标窗口")
            
            # 切换到原始窗口
            if self.original_window and self.original_window in self.driver.window_handles:
                self.driver.switch_to.window(self.original_window)
                logger.info("成功返回原始窗口")
            else:
                # 如果原窗口不存在，切换到第一个可用窗口
                if self.driver.window_handles:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    logger.info("原窗口不存在，切换到第一个可用窗口")
                    
        except Exception as e:
            logger.error(f"关闭标签页失败: {e}")
            
    def process_panel(self, panel_type):
        """
        处理指定任务面板（每日任务或新手礼包）
        """
        logger.info(f"开始处理 {panel_type} 面板")
        
        # 确保进入正确的任务面板
        if not self.find_and_click_tab(panel_type):
            logger.error(f"无法进入 {panel_type} 面板，跳过此任务")
            return False
            
        processed_task_ids = set()
        max_button_attempts = 20
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        for attempt in range(max_button_attempts):
            try:
                # 检查当前是否仍在目标面板
                if not self.is_task_tab_active():
                    logger.warning(f"当前页面不在 {panel_type} 面板，尝试重新进入...")
                    self.driver.get(SITE_URL)
                    time.sleep(2)
                    exp_element = self.find_exp_button()
                    if exp_element and self.should_click_exp_button(exp_element):
                        self.click_exp_button(exp_element)
                    self.find_and_click_tab(panel_type)
                    time.sleep(2)
                    
                # 获取当前容器按钮
                container_buttons = self.get_container_buttons()
                
                # 特殊完成判断逻辑
                # 对于每日任务，判断是否所有按钮都已完成
                if panel_type == "daily_task":
                    if self.check_all_completed(container_buttons):
                        logger.info("所有每日任务已完成。")
                        return True
                # 对于新手礼包，判断是否没有任何可点击的按钮
                elif panel_type == "starter_pack":
                    clickable_buttons = [btn for btn in container_buttons if btn['is_clickable']]
                    if not clickable_buttons:
                        logger.info("新手礼包面板已无任何可点击按钮，任务已完成。")
                        return True
                
                # 如果没有可处理的按钮，但是任务未完成，则等待
                if not container_buttons:
                    logger.warning("面板上未找到任何按钮，但任务未判定完成，等待...")
                    time.sleep(2)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error("连续未找到按钮，且未判定完成，可能出现异常，退出")
                        return False
                    continue
                
                consecutive_failures = 0 # 成功找到按钮，重置失败计数
                
                # ----------------------------------------------------
                # 按钮处理逻辑：优先处理验证，然后处理其他任务
                # ----------------------------------------------------
                
                # 步骤1: 优先寻找并处理“验证”按钮
                verify_button = next((btn for btn in container_buttons if btn['type'] == 'verify' and btn['is_clickable']), None)
                if verify_button:
                    logger.info("优先处理验证按钮")
                    self.click_button_and_handle_result(verify_button)
                    time.sleep(2)
                    continue # 再次循环，重新扫描页面以处理下一个任务

                # 步骤2: 如果没有验证按钮，寻找未处理过的其他任务按钮
                # 排除 'verify' 和 'done' 类型
                task_buttons = [
                    btn for btn in container_buttons 
                    if btn['type'] not in ['verify', 'done'] and btn['is_clickable']
                ]
                
                target_button = None
                for button_info in task_buttons:
                    button_id = f"{button_info['type']}_{button_info['text']}_{button_info['element'].location['x']}"
                    if button_id not in processed_task_ids:
                        target_button = button_info
                        processed_task_ids.add(button_id)
                        break
                
                if not target_button:
                    logger.warning("没有找到可处理的任务按钮。")
                    time.sleep(2)
                    # 如果所有任务都处理过了但未完成，清空记录重新开始
                    if len(processed_task_ids) > 0:
                        logger.info("所有任务都处理过，但未完成，清空记录重新尝试")
                        processed_task_ids.clear()
                    continue
                
                # 步骤3: 点击任务按钮并处理后续流程
                logger.info(f"处理任务按钮: {target_button['text']}")
                success, new_tab_opened = self.click_button_and_handle_result(target_button)

                if not success:
                    logger.warning(f"任务按钮点击失败: {target_button['text']}")
                    time.sleep(1)
                    continue

                if new_tab_opened:
                    logger.info("处理了新标签页，等待验证按钮出现...")
                else:
                    logger.info("页面已跳转，重新进入任务面板")
                    self.driver.get(SITE_URL)
                    time.sleep(2)
                    exp_element = self.find_exp_button()
                    if exp_element and self.should_click_exp_button(exp_element):
                        self.click_exp_button(exp_element)
                    self.find_and_click_tab(panel_type)
                
            except Exception as e:
                logger.error(f"处理 {panel_type} 容器按钮时出错: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("连续错误次数过多，退出")
                    return False
                time.sleep(1)
                continue
        
        logger.warning(f"达到最大按钮处理次数 {max_button_attempts}")
        return False
        
    def check_all_completed(self, container_buttons):
        """
        检查是否所有容器都显示完成
        """
        try:
            if not container_buttons:
                # 每日任务面板应该始终有按钮，如果没找到可能是异常情况
                return False 
            
            completed_count = 0
            total_buttons = len(container_buttons)
            
            for button_info in container_buttons:
                if button_info['type'] == 'done' or button_info['is_disabled']:
                    completed_count += 1
            
            logger.info(f"完成状态: {completed_count}/{total_buttons}")
            
            # 如果所有按钮都显示完成，则返回True
            return completed_count == total_buttons
            
        except Exception as e:
            logger.error(f"检查完成状态失败: {e}")
            return False

    def is_task_tab_active(self):
        """
        新增函数: 检查每日任务或新手礼包标签页是否处于选中状态
        """
        try:
            # 结合每日任务和新手礼包的文本
            tab_texts = BUTTON_TEXTS["daily_task"] + BUTTON_TEXTS["starter_pack"]
            
            # 寻找同时包含特定文本和选中状态CSS类的元素
            for text in tab_texts:
                xpath_selector = f"//div[contains(text(), '{text}') and contains(@class, '{ACTIVE_TAB_CLASS}')]"
                try:
                    element = self.driver.find_element(By.XPATH, xpath_selector)
                    if element and element.is_displayed():
                        logger.info(f"检测到活动标签页: {text}")
                        return True
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"检查标签页 {text} 失败: {e}")
            
            logger.info("未检测到每日任务或新手礼包活动标签页")
            return False
            
        except Exception as e:
            logger.error(f"检查标签页活动状态失败: {e}")
            return False

    def run_automation_with_window_management(self, url, max_attempts=5):
        """
        使用窗口句柄管理的自动化流程，依次处理每日任务和新手礼包
        """
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"开始第 {attempt} 次尝试")
                
                if not self.switch_back_to_target_window():
                    logger.error("无法切换到目标窗口，重新打开")
                    if not self.sosovalue_exp_login(url):
                        logger.error("重新打开页面失败")
                        continue
                
                exp_element = self.find_exp_button()
                if not exp_element:
                    logger.error("未找到EXP按钮，直接退出")
                    self.close_current_tab_and_return()
                    return False
                
                if self.should_click_exp_button(exp_element):
                    logger.info("页面只有EXP按钮，点击进入目标页面")
                    if not self.click_exp_button(exp_element):
                        logger.error("EXP按钮点击失败，重新尝试")
                        continue

                # =========================================================
                # 依次处理每日任务和新手礼包
                # =========================================================
                
                daily_tasks_completed = self.process_panel("daily_task")
                
                starter_pack_completed = self.process_panel("starter_pack")
                
                # =========================================================

                if daily_tasks_completed and starter_pack_completed:
                    logger.info("所有任务已完成！")
                    self.close_current_tab_and_return()
                    return True
                else:
                    logger.warning(f"第 {attempt} 次尝试任务处理未完成")
                    if attempt < max_attempts:
                        logger.info("等待后重新尝试")
                        time.sleep(2)
                
            except Exception as e:
                logger.error(f"第 {attempt} 次尝试失败: {e}")
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
        
        logger.warning(f"所有 {max_attempts} 次尝试都未成功完成")
        self.close_current_tab_and_return()
        return False

    def run_automation(self, url, max_attempts=5):
        """
        运行完整的自动化流程 - 入口函数
        """
        try:
            # 1. 首次打开网页
            if not self.sosovalue_exp_login(url):
                logger.error("初始打开网页失败")
                return False
            
            # 2. 使用窗口句柄管理方式处理自动化流程
            result = self.run_automation_with_window_management(url, max_attempts)
            
            if result:
                logger.info("自动化任务完成成功！")
                print("自动化任务完成！")
            else:
                logger.warning("自动化任务未完全完成")
                print("自动化任务未完全完成")
            
            return result
            
        except Exception as e:
            logger.error(f"自动化流程失败: {e}")
            # 确保出错时也能正确关闭标签页
            try:
                self.close_current_tab_and_return()
            except:
                pass
            return False


# 使用示例
def sosovalue_main(driver, url):
    """
    主函数 - 创建自动化实例并运行
    """
    try:
        # 创建自动化实例
        automation = SosoValueAutomation(driver)
        
        # 运行自动化流程
        success = automation.run_automation(url)
        
        if success:
            logger.info("自动化任务完成！")
            print("自动化任务完成！")
        else:
            logger.warning("自动化任务未完全完成")
            print("自动化任务未完全完成")
        
        return success
        
    except Exception as e:
        logger.error(f"主程序运行失败: {e}")
        print(f"主程序运行失败: {e}")
        return False



def selenium_connect_env(debug_port, webdriver_path):
    chrome_options = Options()
    # 指定要接管的浏览器地址
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    # 指定 MoreLogin 返回的 chromedriver 路径
    service = Service(executable_path=webdriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def sosovalue_signal_task(env):
    env_name = env['env_name']
    env_id = env['env_id']
    url = env['url']
    try:
        try:
            result = asyncio.run(startEnv(appid, secretkey, baseurl, encryptkey, env_id))        
            if result is None:
                logger.info(f"❌ 环境 {env_name} 启动失败，跳过")
                return
            debug_port, webdriver_path = result
        except Exception as e:
            logger.error(f"❌ 环境 {env_name} ({env_id}) 启动失败: {e}")


        driver = selenium_connect_env(debug_port, webdriver_path)

        try:
            handles = driver.window_handles
            first_handle = handles[0]

            # 关闭除第一个以外的所有标签页
            for handle in handles[1:]:
                driver.switch_to.window(handle)
                driver.close()

            # 切回第一个标签页
            driver.switch_to.window(first_handle)
            print("✅ 关闭了其他标签页，切回第一个标签页")
        except Exception as e:
            print(f"❌ 关闭其他标签页失败: {e}")

        #okx_handle = login_okx_wallet(driver)
        ssvalue_true = sosovalue_main(driver, url)
        if ssvalue_true:
            print("SosoValue任务执行成功，准备关闭环境...")
            asyncio.run(stopEnv(appid, secretkey, baseurl, env_id))  # 成功时关闭环境
            print(f"{env_name}环境已关闭")
        else:
            print("SosoValue任务执行失败，不关闭环境")


    except Exception as e:
        logger.error(f"❌ 环境 {env_name} ({env_id}) 启动失败: {e}")

async def sosovalue_tasks(thread_count):
    env_list = load_json(r"D:\VSCODE\chromes\morelogin\morelogin_env.json")
    #env_list = random.choice(env_list)
    #env_list =[env_list]
    # 打乱顺序
    random.shuffle(env_list)
    # 限制线程并发数
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(executor, partial(sosovalue_signal_task, env))
            for env in env_list
        ]
        await asyncio.gather(*tasks)

def main():
    thread_count = 5  # 可修改为你想要的并发数量
    asyncio.run(sosovalue_tasks(thread_count))

if __name__ == "__main__":
    main()