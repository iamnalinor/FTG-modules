# Show chat activity statistics
# Copyright © 2022 https://t.me/nalinor

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# meta developer: </code>@nalinormods<code>
# requires: matplotlib

from contextlib import suppress
from io import BytesIO

import matplotlib.pyplot as plt
from telethon import TelegramClient
from telethon.tl.custom import Message
from telethon.tl.types import MessageEmpty, MessageService

from .. import loader, utils


@loader.tds
class MessagingRateMod(loader.Module):
    """Show chat activity, counted in MpH (messages per hour)"""

    strings = {
        "name": "MsgRate",
        "channels_only": "🚫 <b>This command can be executed only in groups and channels</b>",
        "unable_first_msg": "🚫 <b>Unable to retrieve first message</b>",
        "mph_for": "🔢 <b>MpH for {title}: {count}</b>",
        "chat_small": "🚫 <b>Messaging history of this chat is too small</b>",
        "calculating": "🕑 <b>Calculating, please wait..</b>",
        "messages_count": "Messages count",
        "mph": "MpH",
        "stats_for_chat": "MpH stats for chat {title}",
        "made_by": "<b>Made by {channel} with ❤️</b>",
    }

    strings_ru = {
        "_cls_doc": "Показывает активность чата в MpH (кол-во сообщений в час)",
        "_cmd_doc_msgrate": "<айди чата/юзернейм/текущий> — Показать MpH чата",
        "_cmd_doc_msgstat": "<r|g|b> <айди чата/юзернейм/текущий> — Показать статистику MpH чата",
        "channels_only": "🚫 <b>Эта команда может быть выполнена только в группах и каналах</b>",
        "unable_first_msg": "🚫 <b>Не удаётся получить первое сообщение чата</b>",
        "mph_for": "🔢 <b>MpH для {title}: {count}</b>",
        "chat_small": "🚫 <b>История сообщений этого чата слишком мала</b>",
        "calculating": "🕑 <b>Рассчитываем, пожалуйста, подождите..</b>",
        "messages_count": "Количество сообщений",
        "mph": "MpH",
        "stats_for_chat": "Статистика MpH для чата {title}",
        "made_by": "<b>Сделано {channel} с ❤️</b>",
    }

    @staticmethod
    def calc_mph(msg1: Message, msg2: Message) -> float:
        count = msg2.id - msg1.id
        hours = (msg2.date - msg1.date).total_seconds() / 3600

        return round(count / (hours or 1), 3)

    @staticmethod
    def get_chat_id(message: Message) -> int:
        args = utils.get_args(message)
        if args and len(args[-1]) > 3:
            chat_id = args[-1]
            with suppress(ValueError):
                chat_id = int(chat_id)
        else:
            chat_id = message.chat_id

        return chat_id

    @staticmethod
    async def get_last_msg(client: TelegramClient, chat_id: int) -> Message:
        async for message in client.iter_messages(chat_id, limit=1):
            return message

    async def msgratecmd(self, message: Message):
        """<chat id/username/current> — Show MpH for chat"""
        chat_id = self.get_chat_id(message)
        last_msg = await self.get_last_msg(message.client, chat_id)

        if not last_msg.is_channel:
            return await utils.answer(message, self.strings("channels_only"))

        if (reply := await message.get_reply_message()) and chat_id == message.chat_id:
            msg = reply
        else:
            msg = await message.client.get_messages(chat_id, ids=1)
            if not isinstance(msg, MessageService):
                return await utils.answer(message, self.strings("unable_first_msg"))

        await utils.answer(
            message,
            self.strings("mph_for").format(
                title=(await last_msg.get_chat()).title,
                count=self.calc_mph(msg, last_msg),
            ),
        )

    async def msgstatcmd(self, message: Message):
        """<r|g|b> <chat id/username/current> — Show chat MpH statistics"""
        chat_id = self.get_chat_id(message)
        last_msg = await self.get_last_msg(message.client, chat_id)

        args = utils.get_args(message)
        if args and len(args[0]) <= 3:
            colors = "".join([char for char in "rgb" if char in args[0]]) or "rgb"
        else:
            colors = "rgb"

        if not last_msg.is_channel:
            return await utils.answer(message, self.strings("channels_only"))

        if last_msg.id < 500:
            return await utils.answer(message, self.strings("chat_small"))

        m = await utils.answer(message, self.strings("calculating"))

        messages = list(
            filter(
                lambda m: m and not isinstance(m, MessageEmpty),
                await message.client.get_messages(
                    chat_id,
                    ids=[int(last_msg.id / 200) * count + 1 for count in range(200)],
                ),
            )
        )

        fig = plt.figure()
        plt.xlabel(self.strings("messages_count"))
        plt.ylabel(self.strings("mph"))

        x = [msg.id for msg in messages]

        y1 = [self.calc_mph(last_msg, msg) for msg in messages]
        if "r" in colors:
            plt.plot(x, y1, "r")

        y2 = [self.calc_mph(msg, messages[0]) for msg in messages[1:]]
        if "g" in colors:
            plt.plot(x[1:], y2, "g")

        y3 = [(y1[i + 1] + y2[i]) / 2 for i in range(len(x) - 1)]
        if "b" in colors:
            plt.plot(x[1:], y3, "b")

        plt.title(
            self.strings("stats_for_chat").format(
                title=(await last_msg.get_chat()).title
            )
        )

        stream = BytesIO()
        stream.name = "stats.png"
        plt.savefig(stream)
        stream.seek(0)
        plt.close(fig)

        await message.client.send_file(
            message.chat_id,
            stream,
            caption=self.strings("made_by").format(channel="@nalinormods"),
        )
        await m.delete()
