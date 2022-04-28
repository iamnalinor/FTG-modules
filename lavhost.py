# Simple lavHost manager
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

import re
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Callable, Union

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.custom import Message
from telethon.tl.functions.contacts import UnblockRequest

from .. import loader, main, utils

with suppress(ImportError):
    from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup


@loader.tds
class LavhostManagerMod(loader.Module):
    """Simple @lavHost manager"""

    strings: Callable[[str], str] = {
        "name": "lavHost",
        "not_registered": "🚫 <b>You haven't registered in {bot_username}</b>",
        "loading": "🔍 <b>Loading...</b>",
        "web_link_warning": (
            "⚠️ <b>Warning: web-auth link contains your lavHost <u>username and password</u>. "
            "Type <code>{prefix}lweb force_insecure</code> to confirm</b>"
        ),
        "web_link_warning_inline": (
            "⚠️ <b>Warning: web-auth link contains "
            "your lavHost <u>username and password</u>, be careful</b>"
        ),
        "web_link_message": (
            "🔑 <b><a href='{link}'>Click this text</a> to login into your userbot web-panel. "
            "<u>Don't give that link to anyone!</u></b>"
        ),
        "web_link_inline_message": (
            "📌 <b>Click button to login into your userbot webpanel. "
            "<u>Don't give that link to anyone!</u></b>"
        ),
        "web_link_inline_button": "🔑 Login",
        "confirm": "📤 Send anyway",
        "cancel": "🚫 Cancel",
        "expires": "📅 <b>Your lavHost subscription expires in <u>{time1}, {time2}</u> (<code>{date}</code>)</b>",
        "days_one": "{x} days",
        "days_few": "{x} days",
        "days_many": "{x} days",
        "hours_one": "{x} hours",
        "hours_few": "{x} hours",
        "hours_many": "{x} hours",
        "mins_one": "{x} minutes",
        "mins_few": "{x} minutes",
        "mins_many": "{x} minutes",
        "unknown": "Unknown",
        "not_on_lavhost": "🚫 <b>You aren't on lavHost</b>",
        "lite_plan": "☺️ Lite (75/30₽ per month)",
        "medium_plan": "😋 Medium (150/75₽ per month)",
        "premium_plan": "😎 Premium (300/150₽ per month)",
        "location_F": "Frankfurt",
        "location_D": "Dubai",
        "location_N": "Netherlands",
        "information": (
            "📃 <b>Your lavHost information</b>\n\n"
            "🐶 <b>Username:</b> <code>{username}</code>\n"
            "💰 <b>Plan: {plan}</b>\n"
            "🌐 <b>Server: {server} №{number} [<code>{url}</code>]</b>\n"
            "📅 <b>Expires in:</b> <code>{prefix}lexpires</code>"
        ),
        "support_chat": "✌️ Support chat",
    }

    strings_ru = {
        "_cls_doc": "Простое управление юзерботом на lavHost",
        "_cmd_doc_lstart": "Запустить юзербот",
        "_cmd_doc_lrestart": "Перезагрузить юзербот",
        "_cmd_doc_lstop": "Остановить юзербот",
        "_cmd_doc_lweb": "Получить ссылку для входа в веб-панель",
        "_cmd_doc_lexpires": "Получить дату окончания подписки",
        "_cmd_doc_linfo": "Показать твою информацию на lavHost",
        "not_registered": "🚫 <b>Ты не зарегистрирован в {bot_username}</b>",
        "loading": "🔍 <b>Загрузка...</b>",
        "web_link_warning": (
            "⚠️ <b>Предупреждение: ссылка для авторизации содержит твой <u>логин и пароль</u> на lavHost. "
            "Введи <code>{prefix}lweb force_insecure</code> для подтверждения</b>"
        ),
        "web_link_warning_inline": (
            "⚠️ <b>Предупреждение: ссылка для авторизации содержит "
            "твой <u>логин и пароль</u> на lavHost, будь осторожен</b>"
        ),
        "web_link_message": (
            "🔑 <b><a href='{link}'>Нажми на этот текст</a>, чтобы войти в веб-панель "
            "твоего юзербота. <u>Никому не давай эту ссылку!<u></b>"
        ),
        "web_link_inline_message": (
            "📌 <b>Нажми на кнопку, чтобы войти в веб-панель твоего юзербота. "
            "<u>Никому не давай эту ссылку!</u></b>"
        ),
        "web_link_inline_button": "🔑 Войти",
        "confirm": "📤 Да, показать",
        "cancel": "🚫 Отмена",
        "expires": "📅 <b>Твоя подписка на lavHost истекает через <u>{time1}, {time2}</u> (<code>{date}</code>)</b>",
        "days_one": "{x} день",
        "days_few": "{x} дня",
        "days_many": "{x} дней",
        "hours_one": "{x} час",
        "hours_few": "{x} часа",
        "hours_many": "{x} часов",
        "mins_one": "{x} минута",
        "mins_few": "{x} минуты",
        "mins_many": "{x} минут",
        "unknown": "Неизвестно",
        "not_on_lavhost": "🚫 <b>Ты не на lavHost</b>",
        "lite_plan": "☺️ Lite (75/30₽ за месяц)",
        "medium_plan": "😋 Medium (150/75₽ за месяц)",
        "premium_plan": "😎 Premium (300/150₽ за месяц)",
        "location_F": "Франкфурт",
        "location_D": "Дубаи",
        "location_N": "Нидерланды",
        "information": (
            "📃 <b>Твоя информация на lavHost</b>\n\n"
            "🐶 <b>Юзернейм:</b> <code>{username}</code>\n"
            "💰 <b>Тариф: {plan}</b>\n"
            "🌐 <b>Сервер: {server} №{number} [<code>{url}</code>]</b>\n"
            "📅 <b>Заканчивается через:</b> <code>{prefix}lexpires</code>"
        ),
        "support_chat": "✌️ Чат поддержки",
    }

    def __init__(self):
        self._bot = "@lavHostBot"

    async def client_ready(self, client, db):
        self._client: TelegramClient = client
        self.prefix = lambda: db.get(main.__name__, "command_prefix", ".")

    async def _inline_click(self, message: Message, index: int) -> None:
        """Get inline results, send result at index `index` and answer with inline result text"""
        q = await message.client.inline_query(self._bot, "", entity="me")
        if len(q) == 1:
            return await utils.answer(
                message, self.strings("not_registered").format(bot_username=self._bot)
            )

        m = await q[index].click()
        await m.delete()
        await utils.answer(message, m.raw_text, formatting_entities=m.entities)

    async def _get_response(self, command: str) -> Message:
        """Get response from `self._bot` about command `command`"""
        async with self._client.conversation(self._bot, timeout=3) as conv:
            try:
                m = await conv.send_message(command)
            except YouBlockedUserError:
                await self._client(
                    UnblockRequest(id=await self._client.get_input_entity(self._bot))
                )
                m = await conv.send_message(command)
            r = await conv.get_response()

            await m.delete()
            await r.delete()

        return r

    @loader.owner
    async def lstopcmd(self, message: Message):
        """Stop userbot"""
        await self._inline_click(message, 0)

    @loader.owner
    async def lstartcmd(self, message: Message):
        """Start userbot"""
        await self._inline_click(message, 1)

    @loader.owner
    async def lrestartcmd(self, message: Message):
        """Restart userbot"""
        await self._inline_click(message, 2)

    @loader.owner
    async def lwebcmd(
        self,
        message: Union[Message, "CallbackQuery"],
        close: bool = False,
    ):
        """Get web-panel authorization link"""
        if close:
            await message.delete()
            return

        if hasattr(
            message, "inline_message_id"
        ) or "force_insecure" in utils.get_args_raw(message):
            r = await self._get_response("/web")

            try:
                username, password = re.search(
                    r"Username: (\S*)\s*Password: (.*)", r.raw_text
                ).groups()
                server_id = re.search(
                    r"\.([a-z]\d+)\.lavhost\.ml", r.reply_markup.rows[0].buttons[0].url
                )[1]
            except TypeError:
                return await utils.answer(
                    message,
                    self.strings("not_registered").format(bot_username=self._bot),
                )

            link = f"https://{username}:{password}@{username}.{server_id}.lavhost.ml"

            if hasattr(message, "inline_message_id"):
                await self.inline._bot.edit_message_text(
                    inline_message_id=message.inline_message_id,
                    text=self.strings("web_link_inline_message"),
                    reply_markup=InlineKeyboardMarkup().row(
                        InlineKeyboardButton(
                            self.strings("web_link_inline_button"), url=link
                        )
                    ),
                    parse_mode="html",
                )
            else:
                await utils.answer(
                    message, self.strings("web_link_message").format(link=link)
                )
            return

        if hasattr(self, "inline") and await self.inline.form(
            text=self.strings("web_link_warning_inline"),
            message=message,
            reply_markup=[
                {"text": self.strings("confirm"), "callback": self.lwebcmd},
                {
                    "text": self.strings("cancel"),
                    "callback": self.lwebcmd,
                    "args": (True,),
                },
            ],
            ttl=60 * 5,
        ):
            return

        await utils.answer(
            message,
            self.strings("web_link_warning").format(
                prefix=self.prefix(),
            ),
        )

    async def lexpirescmd(self, message: Message):
        """Get subscription expiration date"""
        m = await utils.answer(message, self.strings("loading"))

        r = await self._get_response("/expires")
        try:
            exp_date = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", r.raw_text)[0]
        except TypeError:
            return await utils.answer(
                m, self.strings("not_registered").format(bot_username=self._bot)
            )

        exp_delta = datetime.strptime(
            exp_date,
            "%Y-%m-%d %H:%M",
        ) - (datetime.utcnow() + timedelta(hours=3))

        def plural_number(n):
            return (
                "one"
                if n % 10 == 1 and n % 100 != 11
                else "few"
                if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20)
                else "many"
            )

        if exp_delta.days > 0:
            number1 = exp_delta.days
            time1 = self.strings(f"days_{plural_number(number1)}").format(x=number1)
            number2 = exp_delta.seconds // 3600
            time2 = self.strings(f"hours_{plural_number(number2)}").format(x=number2)
        else:
            number1 = exp_delta.seconds // 3600
            time1 = self.strings(f"hours_{plural_number(number1)}").format(x=number1)
            number2 = exp_delta.seconds // 60
            time2 = self.strings(f"seconds_{plural_number(number2)}").format(x=number2)

        await utils.answer(
            m,
            self.strings("expires").format(
                time1=time1, time2=time2, date=f"{exp_date} UTC+3"
            ),
        )

    async def linfocmd(self, message: Message):
        """Get your lavHost info"""
        try:
            info = (await message.client.inline_query(self._bot, "", entity="me"))[
                3
            ].message.message
        except TypeError:
            return await utils.answer(
                message, self.strings("not_registered").format(bot_username=self._bot)
            )

        plan = self.strings(
            re.search(r"Тип - (\S+)", info)[1].lower() + "_plan"
        ).replace("Unknown strings", self.strings("unknown"))

        letter, number = re.search(r"Сервер - ([A-Z])(\d+)", info).groups()
        server = self.strings(f"location_{letter}").replace(
            "Unknown strings", self.strings("unknown")
        )

        username = re.search(r"Пользователь - (\S+)", info)[1]

        text = self.strings("information").format(
            plan=plan,
            server=server,
            number=number,
            url=f"{letter.lower()}{number}.lavhost.ml",
            username=username,
            prefix=self.prefix(),
        )

        if hasattr(self, "inline") and await self.inline.form(
            text,
            message=message,
            reply_markup={
                "text": self.strings("support_chat"),
                "url": "https://t.me/lavhostchat",
            },
        ):
            return

        await utils.answer(message, text)
