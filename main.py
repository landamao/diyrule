from astrbot.api.all import Star, EventMessageType, event_message_type, logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core import AstrBotConfig
from astrbot.core.message.components import At, Plain, Reply, Poke
from astrbot.core.star import Context
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.star.filter.command_group import CommandGroupFilter
from astrbot.core.star.star_handler import star_handlers_registry
import random

class 群自定义规则(Star):

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config
        self.l指令前缀 = config['指令前缀']  #不需要用get，因为是配置的项
        self.l所有指令 = self.f获取所有指令() + config['额外指令']
        logger.warning(f"\n\n所有指令：\n{self.l所有指令}\n")
        self.规则列表 = config['自定义规则']
        # 由于群号是列表，我们需要扁平化处理
        self.l启用群号 = []
        for 规则 in self.规则列表:
            if 规则['开关']:
                for 群号 in 规则['群号']:
                    self.l启用群号.append(群号.strip())

        self.系统指令 = (
            "llm",
            "t2i",
            "tts",
            "sid",
            "op",
            "wl",
            "dashboard_update",
            "alter_cmd",
            "provider",
            "model",
            "plugin",
            "plugin ls",
            "new",
            "switch",
            "rename",
            "del",
            "reset",
            "history",
            "persona",
            "tool ls",
            "key",
            "websearch",
            "help"
        )

    @event_message_type(EventMessageType.GROUP_MESSAGE, priority=999)
    async def 主函数(self, event: AstrMessageEvent):
        群号 = event.get_group_id()
        if 群号 in self.l启用群号:  #先快速判断是否在设定的规则群号里
            唤醒 = False
            消息链 = event.get_messages()
            消息文本 = " ".join([seg.text for seg in 消息链 if isinstance(seg, Plain)]).strip()

            for 规则 in self.规则列表:
                for j in  规则['群号']:
                    if 群号 == j.strip(): #找到该群号的规则
                        # 处理指令
                        for 前缀 in self.l指令前缀:
                            if 消息文本.startswith(前缀):
                                if event.is_admin(): return  #管理员不受影响
                                指令文本 = 消息文本[len(前缀):].split()[0]
                                if 规则['禁用系统指令'] and 指令文本 in self.系统指令: event.stop_event(); return
                                if 规则['禁用的指令']:
                                    if 规则['禁用的指令'][0].strip() == '0所有':
                                        event.stop_event(); return
                                    elif any( 指令 == 指令文本 for 指令 in 规则['禁用的指令']):
                                        logger.info(f'指令{指令文本}已被禁用')
                                        event.stop_event(); return
                                if 规则['启用的指令']:
                                    if 规则['启用的指令'][0].strip() == '0所有': return
                                    elif not any(指令 == 指令文本 for 指令 in 规则['启用的指令']):
                                        logger.info(f'已配置启用指令列表，但指令「{指令文本}」未在启用列表')
                                        event.stop_event(); return
                                if 规则['禁前唤醒'] and 指令文本 not in self.l所有指令: event.stop_event(); return
                                else: return

                        if 规则['概率唤醒'] and random.random() < 规则['概率唤醒']:
                            logger.info('触发了概率唤醒')
                            唤醒 = True

                        elif any( _.strip() in 消息文本 for _ in 规则['昵称唤醒']):
                            logger.info('昵称唤醒')
                            唤醒 = True

                        elif any( 消息文本.startswith(_) for _ in 规则['其他前缀跳过']):
                            return

                        elif any( _ in 消息文本 for _ in 规则['含有跳过']):
                            return

                        else:
                            for seg in 消息链:
                                if 规则['艾特唤醒'] and isinstance(seg, At) and str(seg.qq) == event.get_self_id():
                                    logger.info('触发了艾特唤醒')
                                    唤醒 = True
                                    break
                                elif 规则['引用唤醒'] and isinstance(seg, Reply) and str(seg.sender_id) == event.get_self_id():
                                    logger.info('触发了引用唤醒')
                                    唤醒 = True
                                    break
                                elif 规则['放行戳一戳事件'] and isinstance(seg, Poke):
                                    return

                                elif 规则['概率跳过'] and random.random() < 规则['概率跳过']:
                                    return


                        #应用唤醒
                        if 唤醒:
                            logger.info('此次唤醒')
                            event.is_at_or_wake_command = True
                        else: event.stop_event()
                        return

    @staticmethod
    def f获取所有指令() -> list:
        # 遍历所有注册的处理器获取所有命令，包括别名
        l指令 = []
        for handler in star_handlers_registry:
            for i in handler.event_filters:
                if isinstance(i, CommandFilter):
                    l指令.append(i.command_name)
                    # 获取别名 - 注意属性名是 alias，类型是 set
                    if hasattr(i, 'alias') and i.alias:  l指令.extend(list(i.alias))
                elif isinstance(i, CommandGroupFilter):
                    l指令.append(i.group_name)

        return list(set(l指令))
