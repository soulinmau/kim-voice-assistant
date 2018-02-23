# -*- coding: utf-8-*-

from utils.logger import init as loggingConfiger
import logging
from src.conversation import Conversation
from config import profile
from config.path import APP_RESOURCES_DATA_PATH
import argparse
from utils.aliyun_iotx.iot_mqtt_client import IotClient
from threading import Thread
from src.device_init import main as device_init
import jieba
import io, sys, time
from src.mic_server import Mic as MicServer
from src.iot_report import save_shadow_kvs_for_settings


parser = argparse.ArgumentParser(description='')
parser.add_argument('--textmode', action='store_true', help='使用文本交互')
parser.add_argument('--init', action='store_true', help='初始化')
# 调试模式
parser.add_argument('--debug', action='store_true', help='Show debug messages')
parser.add_argument('--info', action='store_true', help='Show info messages')
args = parser.parse_args()
if args.textmode:
    from src.mic_text import Mic
else:
    from src.mic_voice import Mic


class App:
    def __init__(self):
        self.persona = 'abc'
        self.iot_client = IotClient.get_instance()
        Thread(target=self.iot_client.do_connect, daemon=True).start()   # 建立IoTHub监听进程
        # Initialize Mic
        self.mic = Mic(self.iot_client)
        self._logger = logging.getLogger()
        save_shadow_kvs_for_settings()
        time.sleep(1)
        self.iot_client.do_report_devstat(version_increase=True)

    def launch_server_listen_thread(self):
        self._logger.info('start server conversation listener...')
        conversation = Conversation(mic=MicServer(self.iot_client, peer_mic=self.mic), persona=self.persona, profile=profile,
                                    iot_client=self.iot_client)
        mic_server_thread = Thread(target=conversation.handle_forever, daemon=True)
        mic_server_thread.start()

    def run(self):
        """
        初始化对话
        :return:
        """
        conversation = Conversation(mic=self.mic, persona=self.persona, profile=profile, iot_client=self.iot_client)
        conversation.handle_forever()


if __name__ == "__main__":
    loggingConfiger(info=args.info, debug=args.debug)      # 配置logging
    logger = logging.getLogger()

    if args.init:
        print('initializing...')
        device_init()
    else:
        jieba.set_dictionary(APP_RESOURCES_DATA_PATH + 'jieba.small.dict')  # 设置中文分词库
        jieba.initialize()
        app = App()
        if profile.remote_control_service_enable:  # server messege listen
            app.launch_server_listen_thread()
        app.run()  # start service


