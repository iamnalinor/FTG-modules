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

# meta developer: @nalinormods
# requires: aiohttp

import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

import aiohttp
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.custom import Message
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import UnblockRequest

from .. import loader, main, utils

logger = logging.getLogger(__name__)


class LavHostError(RuntimeError):
    """Basic class for all lavHost-related errors"""


class LavHostAPIError(LavHostError):
    """Raised when the API returns an error"""

    def __init__(self, method_name, text):
        super().__init__()
        self.method_name = method_name
        self.text = text

    def __str__(self):
        return f"API error in {self.method_name}: {self.text}"


class LavHostNotRegisteredError(LavHostError):
    """Raised when user is not registered on LavHost"""

    def __init__(self, *args):
        if not args:
            args = ("user is not registered on LavHost",)
        super().__init__(*args)


def error_handler(func) -> Callable:
    """Decorator to handle lavHost-related exceptions"""

    # noinspection PyCallingNonCallable
    @functools.wraps(func)
    async def wrapped(self: "LavHostMod", message: Message, *args, **kwargs):
        try:
            return await func(self, message, *args, **kwargs)
        except LavHostAPIError as e:  # pylint: disable=invalid-name
            logger.debug("Command failed due to", exc_info=True)
            await utils.answer(
                message,
                self.strings("api_error").format(
                    method_name=e.method_name, text=e.text
                ),
            )
        except LavHostNotRegisteredError:
            await utils.answer(
                message, self.strings("not_registered").format(bot_username=self.bot)
            )

    wrapped.__doc__ = func.__doc__
    wrapped.__module__ = func.__module__

    return wrapped


# noinspection PyCallingNonCallable,PyAttributeOutsideInit
# pylint: disable=not-callable,attribute-defined-outside-init,invalid-name
@loader.tds
class LavHostMod(loader.Module):
    """Simple @lavHost manager"""

    strings = {
        "name": "LavHost",
        "author": "@nalinormods",
        "not_registered": "🚫 <b>You don't have active subscription in {bot_username}</b>",
        "api_error": (
            "🚫 <b>API returned an error in </b>"
            "<code>{method_name}</code>: <code>{text}</code>"
        ),
        "loading": "🔍 <b>Loading...</b>",
        "days_one": "{x} days",
        "days_few": "{x} days",
        "days_many": "{x} days",
        "hours_one": "{x} hours",
        "hours_few": "{x} hours",
        "hours_many": "{x} hours",
        "mins_one": "{x} minutes",
        "mins_few": "{x} minutes",
        "mins_many": "{x} minutes",
        "expires": "📅 <b>Expires in: <u>{time1}, {time2}</u> (<code>{date}</code>)</b>",
        "lite_plan": "☺️ Lite (1.59$ / month)",
        "premium_plan": "😎 Premium (2.99$ / month)",
        "ultimate_plan": "😎 Ultimate",
        "location_f": "Frankfurt",
        "location_d": "Dubai",
        "location_n": "Netherlands",
        "location_a": "Amsterdam",
        "location_l": "London",
        "unknown": "Unknown ({text})",
        "ftg_userbot": "FTG 🤖🔹",
        "geektg_userbot": "GeekTG 🕶🔹",
        "hikka_userbot": "Hikka 🌘🔹",
        "sh1t_userbot": "Sh1t-UB 😎🔸",
        "dragon_userbot": "Dragon Userbot 🐉🔸",
        "information": (
            "📃 <b>Your lavHost information</b>\n\n"
            "🐶 <b>Username:</b> <code>{username}</code>\n"
            "💰 <b>Plan: {plan}</b>\n"
            "🌐 <b>Server: {server} №{number} [<code>{url}</code>]</b>\n"
            "🤖 <b>Userbot: {userbot}</b>\n"
            "{expires}"
        ),
        "support_chat": "✌️ Support chat",
        "no_target": "🧐 <b>Whom should I check?</b>",
        "check_True": "✅ <b>Yes, <code>{id}</code> has active lavHost subscription</b>",
        "check_False": "❌ <b>No, <code>{id}</code> doesn't have lavHost subscription</b>",
        "stopped": "✅ <b>Stopped</b>",
        "started": "✅ <b>Started</b>",
        "restarted": "✅ <b>Restarted</b>",
    }

    strings_ru = {
        "_cls_doc": "Простое управление юзерботом на lavHost",
        "_cmd_doc_lstart": "Запустить юзербот",
        "_cmd_doc_lrestart": "Перезагрузить юзербот",
        "_cmd_doc_lstop": "Остановить юзербот",
        "_cmd_doc_lweb": "Получить ссылку для входа в веб-панель",
        "_cmd_doc_linfo": "Показать твою информацию на lavHost",
        "_cmd_doc_lcheck": (
            "<reply/username/id> — "
            "Проверить, зарегистрирован ли пользователь на lavHost"
        ),
        "not_registered": "🚫 <b>У тебя нет активной подписки в {bot_username}</b>",
        "api_error": "🚫 <b>Ошибка API в </b><code>{method_name}</code>: <code>{text}</code>",
        "loading": "🔍 <b>Загрузка...</b>",
        "days_one": "{x} день",
        "days_few": "{x} дня",
        "days_many": "{x} дней",
        "hours_one": "{x} час",
        "hours_few": "{x} часа",
        "hours_many": "{x} часов",
        "mins_one": "{x} минута",
        "mins_few": "{x} минуты",
        "mins_many": "{x} минут",
        "expires": "📅 <b>Заканчивается через:</b> <u>{time1}, {time2}</u> (<code>{date}</code>)",
        "unknown": "Неизвестно ({letter})",
        "lite_plan": "☺️ Lite (100₽ / месяц)",
        "premium_plan": "😎 Premium (150₽ / месяц)",
        "location_f": "Франкфурт",
        "location_d": "Дубаи",
        "location_n": "Нидерланды",
        "location_a": "Амстердам",
        "location_l": "Лондон",
        "information": (
            "📃 <b>Твоя информация на lavHost</b>\n\n"
            "🐶 <b>Юзернейм:</b> <code>{username}</code>\n"
            "💰 <b>Тариф: {plan}</b>\n"
            "🌐 <b>Сервер: {server} №{number} [<code>{url}</code>]</b>\n"
            "🤖 <b>Юзербот: {userbot}</b>\n"
            "{expires}"
        ),
        "support_chat": "✌️ Чат поддержки",
        "no_target": "🧐 <b>Кого мне надо проверить?</b>",
        "check_True": "✅ <b>Да, <code>{id}</code> имеет активную подписку на lavHost</b>",
        "check_False": "❌ <b>Нет, <code>{id}</code> не имеет подписку на lavHost</b>",
        "stopped": "✅ <b>Юзербот остановлен</b>",
        "started": "✅ <b>Юзербот запущен</b>",
        "restarted": "✅ <b>Юзербот перезапущен</b>",
    }

    def __init__(self):
        self.bot = "@lavHostBot"
        self.session = aiohttp.ClientSession()

    def __del__(self):
        # noinspection PyProtectedMember
        self.session._connector._close()

    async def client_ready(self, client: TelegramClient, db):
        """client_ready hook"""
        self.client = client
        self.db = db

        await client(JoinChannelRequest(channel=self.strings("author")))

    def get_prefix(self) -> str:
        """Get command prefix"""
        return self.db.get(main.__name__, "command_prefix") or "."

    def get(self, key: str, default: Any = None):
        """Get value from database"""
        return self.db.get(self.strings("name"), key, default)

    def set(self, key: str, value: Any):
        """Set value in database"""
        return self.db.set(self.strings("name"), key, value)

    async def inline_click(self, index: int):
        """Click on inline result from `self.bot` at given index and delete message"""
        query = await self.client.inline_query(self.bot, "", entity="me")
        if len(query) == 1:
            raise LavHostNotRegisteredError

        await (await query[index].click()).delete()

    async def get_response(self, command: str) -> Message:
        """Get response from `self.bot` about command `command`"""
        async with self.client.conversation(self.bot, timeout=3) as conv:
            try:
                m = await conv.send_message(command)
            except YouBlockedUserError:
                # noinspection PyTypeChecker
                await self.client(UnblockRequest(self.bot))
                m = await conv.send_message(command)
            r = await conv.get_response()

            await m.delete()
            await r.delete()

        return r

    async def get_token(self):
        """Retrieve token for lavHost API"""
        if token := self.get("token"):
            return token

        r = await self.get_response("/token")
        if "\n" in r.raw_text:
            raise LavHostNotRegisteredError

        self.set("token", r.raw_text)
        return r.raw_text

    async def api_request(self, method_name: str, auth_required=True, **kwargs) -> dict:
        """Make request to lavHost API and return result"""
        token = await self.get_token() if auth_required else ""

        async with self.session.get(
            f"https://api.lavhost.su/{method_name}",
            params=kwargs,
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            if not resp.ok:
                if resp.status in [401, 403] and auth_required:
                    self.set("token", None)  # refetch token
                    return await self.api_request(method_name, auth_required, **kwargs)
                raise LavHostAPIError(method_name, await resp.text())

            return await resp.json()

    @staticmethod
    def plural_number(n: int) -> str:
        """Pluralize number `n`"""
        return (
            "one"
            if n % 10 == 1 and n % 100 != 11
            else "few"
            if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20)
            else "many"
        )

    @loader.owner
    @error_handler
    async def lstopcmd(self, message: Message):
        """Stop userbot"""
        await self.inline_click(0)
        await utils.answer(message, self.strings("stopped"))

    @loader.owner
    @error_handler
    async def lstartcmd(self, message: Message):
        """Start userbot"""
        await self.inline_click(1)
        await utils.answer(message, self.strings("started"))

    @loader.owner
    @error_handler
    async def lrestartcmd(self, message: Message):
        """Restart userbot"""
        await self.inline_click(2)
        await utils.answer(message, self.strings("restarted"))

    @error_handler
    async def linfocmd(self, message: Message):
        """Get your lavHost info"""
        m = await utils.answer(message, self.strings("loading"))

        info = await self.api_request("user/information")

        expires_date = datetime.fromisoformat(info["expires_date"]) - timedelta(
            hours=3
        )  # convert time to UTC format
        expires_ts = expires_date.timestamp() if expires_date.year != 9999 else 0

        if expires_date < datetime.utcnow():
            raise LavHostNotRegisteredError

        plan = (
            self.strings(info["type"].lower() + "_plan")
            if expires_ts != 0
            else self.strings("ultimate_plan")
        )

        letter, number = info["server"][:1], info["server"][1:]
        server = (
            self.strings(f"location_{letter}")
            if f"location_{letter}" in self.strings
            else self.strings("unknown").format(text=letter)
        )

        if expires_ts != 0:
            exp_delta = expires_date - datetime.utcnow()

            if exp_delta.days > 0:
                number1 = exp_delta.days
                time1 = self.strings(f"days_{self.plural_number(number1)}").format(
                    x=number1
                )
                number2 = exp_delta.seconds // 3600
                time2 = self.strings(f"hours_{self.plural_number(number2)}").format(
                    x=number2
                )
            else:
                number1 = exp_delta.seconds // 3600
                time1 = self.strings(f"hours_{self.plural_number(number1)}").format(
                    x=number1
                )
                number2 = exp_delta.seconds // 60
                time2 = self.strings(f"mins_{self.plural_number(number2)}").format(
                    x=number2
                )

            expires = self.strings("expires").format(
                time1=time1,
                time2=time2,
                date=(expires_date + timedelta(hours=3)).strftime(
                    "%d.%m.%Y %H:%M UTC+3"
                ),
            )
        else:
            expires = ""

        userbot = (
            self.strings(f"{info['userbot'].lower()}_userbot")
            if f"{info['userbot'].lower()}_userbot" in self.strings
            else info["userbot"]
        )

        text = self.strings("information").format(
            username=info["username"],
            plan=plan,
            server=server,
            number=number,
            url=f"{letter.lower()}{number}.lavhost.su",
            userbot=userbot,
            expires=expires,
        )

        if hasattr(self, "inline") and await self.inline.form(
            text,
            message=m,
            reply_markup={
                "text": self.strings("support_chat"),
                "url": "https://t.me/lavhostchat",
            },
            **({"silent": True} if hasattr(self, "hikka") else {}),
        ):
            return

        await utils.answer(m, text)

    @loader.unrestricted
    async def lcheckcmd(self, message: Message):
        """<reply/username/id> — Check if user is registered in lavHost or not"""
        reply = await message.get_reply_message()
        try:
            if reply and reply.sender_id > 0:
                user_id = reply.sender_id
            elif args := utils.get_args_raw(message):
                user_id = (
                    int(args)
                    if args.isdigit()
                    else (await self.client.get_input_entity(args)).user_id
                )
            else:
                raise AttributeError
        except AttributeError:
            return await utils.answer(message, self.strings("no_target"))

        resp = await self.api_request(
            "user/check", auth_required=False, user_id=user_id
        )
        await utils.answer(
            message, self.strings(f"check_{resp['active_user']}").format(id=user_id)
        )
