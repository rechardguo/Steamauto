import datetime
import os
import time

import pyjson5 as json
import requests
from apprise.AppriseAsset import AppriseAsset
from requests.exceptions import ProxyError
from steampy.exceptions import InvalidCredentials

from utils.logger import handle_caught_exception
from utils.static import APPRISE_ASSET_FOLDER, BUFF_ACCOUNT_DEV_FILE_PATH, BUFF_COOKIES_FILE_PATH, SUPPORT_GAME_TYPES
from utils.tools import get_encoding

class BuffAutoBuy:
    buff_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.27",
    }
    def __init__(self, logger, steam_client, config):
        self.logger = logger
        self.steam_client = steam_client
        self.config = config
        self.development_mode = self.config["development_mode"]
        AppriseAsset(plugin_paths=[os.path.join(os.path.dirname(__file__), "..", APPRISE_ASSET_FOLDER)])
        self.session = requests.session()
        self.lowest_price_cache = {}

    def init(self) -> bool:
        if not os.path.exists(BUFF_COOKIES_FILE_PATH):
            with open(BUFF_COOKIES_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("session=")
            return True
        return False

    def search_buy_price_higher_than_sale(self, game: str):
        items=[]
        for i in range(1, 50):
            self.logger.info("[BuffAutoBuy] 检查饰品市场第{pagenum}页".format(pagenum=i))
            url = "https://buff.163.com/api/market/goods/buying?game={game}&page_num={pagenum}&min_price=1&max_price=100".format(
                game=game,
                pagenum=i,
            )
            self.logger.info("[BuffAutoBuy] 请求URL: {url}".format(url=url))
            response_json = self.session.get(url, headers=self.buff_headers).json()
            if response_json["code"] == "OK":
                found = False
                for item in response_json["data"]["items"]:
                    if float(item["buy_max_price"]) > float(item["sell_min_price"]):
                        self.logger.info("[BuffAutoBuy] 发现价格异常饰品: {item_name}, ID:{item_id}, 售价: {sell_min_price}, 求购价: {buy_max_price} ".format(
                            item_id=item["id"],
                            item_name=item["market_hash_name"],
                            sell_min_price=item["sell_min_price"],
                            buy_max_price=item["buy_max_price"],
                        ))
                        items.append(item)
                        found = True
                if not found:
                    self.logger.info("[BuffAutoBuy] 未发现价格异常饰品")
            else:
                self.logger.error("[BuffAutoBuy] 检查饰品市场第{pagenum}页失败: {code}, {message}".format(
                    pagenum=i,
                    code=response_json["code"],
                    message=response_json["error"],
                ))
                break
            self.logger.info("[BuffAutoBuy] 休眠5秒, 防止请求过快被封IP")
            time.sleep(5)
        return items

    def check_buff_account_state(self, dev=False):
        if dev and os.path.exists(BUFF_ACCOUNT_DEV_FILE_PATH):
            self.logger.info("[BuffAutoBuy] 开发模式, 使用本地账号")
            with open(BUFF_ACCOUNT_DEV_FILE_PATH, "r", encoding=get_encoding(BUFF_ACCOUNT_DEV_FILE_PATH)) as f:
                buff_account_data = json.load(f)
            return buff_account_data["data"]["nickname"]
        else:
            response_json = self.session.get("https://buff.163.com/account/api/user/info", headers=self.buff_headers).json()
            if dev:
                self.logger.info("开发者模式, 保存账户信息到本地")
                with open(BUFF_ACCOUNT_DEV_FILE_PATH, "w", encoding=get_encoding(BUFF_ACCOUNT_DEV_FILE_PATH)) as f:
                    json.dump(response_json, f, indent=4)
            if response_json["code"] == "OK":
                if "data" in response_json:
                    if "nickname" in response_json["data"]:
                        return response_json["data"]["nickname"]
            self.logger.error("[BuffAutoBuy] BUFF账户登录状态失效, 请检查buff_cookies.txt或稍后再试! ")

    def exec(self):
        self.logger.info("[BuffAutoBuy] BUFF自动购买插件已启动")
        try:
            self.logger.info("[BuffAutoBuy] 正在准备登录至BUFF...")
            with open(BUFF_COOKIES_FILE_PATH, "r", encoding=get_encoding(BUFF_COOKIES_FILE_PATH)) as f:
                self.session.cookies["session"] = f.read().replace("session=", "").replace("\n", "").split(";")[0]
            self.logger.info("[BuffAutoBuy] 已检测到cookies, 尝试登录")
            self.logger.info("[BuffAutoBuy] 已经登录至BUFF 用户名: " + self.check_buff_account_state(dev=self.development_mode))
        except TypeError as e:
            handle_caught_exception(e)
            self.logger.error("[BuffAutoBuy] BUFF账户登录检查失败, 请检查buff_cookies.txt或稍后再试! ")
            return
        sleep_interval = int(self.config["buff_auto_buy"]["interval"])
        while True:
            try:
                while True:
                    items_count_this_loop = 0
                    for game in SUPPORT_GAME_TYPES:
                        self.logger.info("[BuffAutoBuy] 正在检查 " + game["game"] + " 是否有饰品捡漏")
                        items = self.search_buy_price_higher_than_sale(game=game["game"])
                        if len(items) != 0:
                            self.logger.info(
                                "[BuffAutoBuy] 检查到 " + game["game"] + " 有 " + str(len(items)) + " 件商品存在捡漏机会"
                            )
                            # for item in items:
                            #    print(item)
                        else:
                            self.logger.info("[BuffAutoBuy] 检查到 " + game["game"] + " 没有捡漏机会, 跳过")
                        self.logger.info("[BuffAutoBuy] 休眠30秒, 防止请求过快被封IP")
                        time.sleep(30)
                    if items_count_this_loop == 0:
                        self.logger.info("[BuffAutoBuy] 库存为空, 本批次上架结束!")
                        break
            except ProxyError:
                self.logger.error('代理异常, 本软件可不需要代理或任何VPN')
                self.logger.error('可以尝试关闭代理或VPN后重启软件')
            except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
                self.logger.error('网络异常, 请检查网络连接')
                self.logger.error('这个错误可能是由于代理或VPN引起的, 本软件可无需代理或任何VPN')
                self.logger.error('如果你正在使用代理或VPN, 请尝试关闭后重启软件')
                self.logger.error('如果你没有使用代理或VPN, 请检查网络连接')
            except InvalidCredentials as e:
                self.logger.error('mafile有问题, 请检查mafile是否正确(尤其是identity_secret)')
                self.logger.error(str(e))
            except Exception as e:
                self.logger.error("[BuffAutoBuy] BUFF商品扫描失败, 错误信息: " + str(e), exc_info=True)
            self.logger.info("[BuffAutoBuy] 休眠" + str(sleep_interval) + "秒")
            time.sleep(sleep_interval)
