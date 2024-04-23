# Finds an intersection between users in different groups
# Copyright © 2024 https://t.me/nalinor

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

# Even taking into account the fact I double-checked every math expression,
# you, as a reader, have to remember that I'm a programmer, not a math expert.
# Some complicated operations (like symmetric difference on the complement of a set) may go wrong.
# I'd be glad to see your pull requests here if you find an error.

# Reminder: In the code below I use "negated" and "negatable" sets as a definition for "the complement of a set".
# It's easier for me to say that a set is "negated" rather than a set is "complement", "completion", "completed", ...

import ast
import io
import logging
import time
from typing import cast

from telethon import TelegramClient, errors
from telethon.errors import ChatAdminRequiredError
from telethon.hints import Entity
from telethon.tl import types
from telethon.tl.custom import Message
from telethon.tl.functions.channels import JoinChannelRequest

from .. import loader, utils

logger = logging.getLogger(__name__)


class InvalidChatID(Exception):
    def __init__(self, chat_id: "int | str", reason: str):
        self.chat_id = chat_id
        self.reason = reason

    def __str__(self):
        return f"Invalid chat ID {self.chat_id}: {self.reason}"


class NegatableSet(set):
    """
    Set that can be negated.
    Negated set A is a set of all elements that are not in A (a complement of set A).

    https://en.wikipedia.org/wiki/Complement_(set_theory)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.negated = False

    def __invert__(self):
        """Creates a copy of set and marks it as negated"""
        return NegatableSet(self).negate()

    def negate(self) -> "NegatableSet":
        """Marks that the set is negated in-place"""
        self.negated = not self.negated
        return self

    def __and__(self, other: "NegatableSet") -> "NegatableSet":
        if self.negated and other.negated:
            return NegatableSet(self.union(other)).negate()

        if other.negated:
            return NegatableSet(self.difference(other))

        if self.negated:
            return NegatableSet(other.difference(self))

        return NegatableSet(self.intersection(other))

    def __or__(self, other: "NegatableSet") -> "NegatableSet":
        if self.negated and other.negated:
            return NegatableSet(self.intersection(other)).negate()

        if other.negated:
            return NegatableSet(other.difference(self)).negate()

        if self.negated:
            return NegatableSet(self.difference(other)).negate()

        return NegatableSet(self.union(other))

    def __sub__(self, other: "NegatableSet") -> "NegatableSet":
        if self.negated and other.negated:
            return NegatableSet(self.difference(other))

        if other.negated:
            return NegatableSet(self.intersection(other))

        if self.negated:
            return NegatableSet(self.union(other)).negate()

        return NegatableSet(self.difference(other))

    def __xor__(self, other: "NegatableSet") -> "NegatableSet":
        if self.negated and other.negated:
            # (A - B) | (B - A)
            return NegatableSet(self.difference(other).union(other.difference(self)))

        if self.negated or other.negated:
            # (A & B) | ~(A | B)
            # => ~((A - B) | (B - A))
            return NegatableSet(
                self.difference(other).union(other.difference(self))
            ).negate()

        return NegatableSet(self.symmetric_difference(other))

    def __ior__(self, other):
        raise NotImplementedError("use __or__ instead")

    def __iand__(self, other):
        raise NotImplementedError("use __and__ instead")


class QueryExecutor:
    async def fetch_set(self, key: "int | str") -> NegatableSet:
        """Fetches a set to be used in a query"""

        raise NotImplementedError

    async def execute(self, query: str) -> NegatableSet:
        """Executes a query"""

        query = query.replace("&&", "&").replace("||", "|").replace("@", "")

        body = ast.parse(query).body

        if not body:
            raise SyntaxError("empty body")
        if len(body) > 1:
            raise SyntaxError("more than one statement in the body")
        if not isinstance(body[0], ast.Expr):
            raise SyntaxError(
                f"expected expression, {body[0].__class__.__name__} found"
            )

        expr = cast(ast.Expr, body[0])
        result = await self.query(expr.value)

        return result

    async def execute_simplified(self, params: "list[str]") -> NegatableSet:
        first = await self.fetch_set(params[0])
        for param in params[1:]:
            first = first & await self.fetch_set(param)
        return first

    async def query(self, expr: ast.expr) -> NegatableSet:
        """Recursively iterates over the expression tree and evaluates it"""
        if isinstance(expr, ast.Name):
            return await self.fetch_set(expr.id)

        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, (str, int)):
                return await self.fetch_set(expr.value)

            raise SyntaxError(f"invalid constant value: {expr.value}")

        if (
            isinstance(expr, ast.UnaryOp)
            and isinstance(expr.op, ast.USub)
            and isinstance(expr.operand, ast.Constant)
        ):
            if isinstance(expr.operand.value, int):
                return await self.fetch_set(-expr.operand.value)

            raise SyntaxError(f"invalid constant value: {expr.operand.value}")

        if isinstance(expr, ast.BoolOp):
            first = await self.query(expr.values[0])

            for value in expr.values[1:]:
                if isinstance(expr.op, ast.And):
                    first = first & await self.query(value)
                else:
                    first = first | await self.query(value)

            return first

        if isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.BitAnd):
                return await self.query(expr.left) & await self.query(expr.right)

            if isinstance(expr.op, (ast.BitOr, ast.Add)):
                return await self.query(expr.left) | await self.query(expr.right)

            if isinstance(expr.op, ast.Sub):
                return await self.query(expr.left) - await self.query(expr.right)

            if isinstance(expr.op, ast.BitXor):
                return await self.query(expr.left) ^ await self.query(expr.right)

        if isinstance(expr, ast.UnaryOp) and isinstance(
            expr.op,
            (
                ast.Not,
                ast.Invert,
                ast.USub,
            ),
        ):
            return (await self.query(expr.operand)).negate()

        logger.debug("remaining expression: %s", ast.dump(expr))
        raise SyntaxError(f"operator {expr.__class__.__name__} is not supported")


members_cache: "dict[int | str, tuple[dict[int], float]]" = {}


class UsersQueryExecutor(QueryExecutor):
    def __init__(self, client: TelegramClient):
        super().__init__()

        self.users: "dict[int]" = {}
        self.client = client

    async def fetch_set(self, key: "int | str") -> NegatableSet:
        if key in ["me", "self"]:
            me = await self.client.get_me()
            self.users[me.id] = me

            return NegatableSet([me.id])

        try:
            key = int(key)
        except ValueError:
            pass

        try:
            chat = await self.client.get_entity(await self.client.get_input_entity(key))
        except (ValueError, errors.BadRequestError) as e:
            raise InvalidChatID(key, str(e))

        if isinstance(chat, types.User):
            raise InvalidChatID(key, "chat ID belongs to a user")

        if key in members_cache and members_cache[key][1] > time.perf_counter():
            logger.debug("Using cached participants for %s", key)
            members = members_cache[key][0]
        else:
            logger.debug("Fetching participants for %s", key)
            try:
                members = {
                    member.id: member
                    async for member in self.client.iter_participants(chat.id)
                }
            except ChatAdminRequiredError:
                raise InvalidChatID(
                    key, "insufficient privileges to view users in chat"
                )

            members_cache[key] = (members, time.perf_counter() + 600)

        self.users.update(members)

        return NegatableSet(members.keys())


def format_user(user: Entity, tags: bool = True) -> str:
    """Formats a user to be displayed in the results"""
    if user.username:
        link, username = f"https://t.me/{user.username}", f"@{user.username}"
    elif user.usernames:
        username = user.usernames[0].username
        link, username = f"https://t.me/{username}", f"@{username}"
    else:
        link, username = f"tg://user?id={user.id}", ""

    name = (
        f"{user.first_name} {user.last_name}"
        if user.last_name
        else user.first_name
        if user.first_name
        else "Deleted Account"
    )

    if tags:
        name = utils.escape_html(name)
        return f"<a href='{link}'>{name}</a> (<code>{user.id}</code>)"

    return f"{user.id} {name} {username}"


# noinspection PyCallingNonCallable,PyAttributeOutsideInit
# pylint: disable=not-callable,attribute-defined-outside-init,invalid-name
@loader.tds
class MembersQueryMod(loader.Module):
    """Finds an intersection between members of different groups"""

    strings = {
        "name": "MembersQuery",
        "author": "@nalinormods",
        "usage": """
📝 <b>MembersQuery module syntax</b>

A brief of Python syntax is used for queries.

Specify groups as a username (with or without @) or chat ID.
Channels are also accepted in case you are an admin. You can't fetch more than 200 members from a channel, so results may be incomplete.
Specify yourself as <code>me</code> or <code>self</code>.

Each group is represented by a set of its members (see set theory). You can use these operations:
<code>&</code>, <code>and</code> — intersection (members that are in both groups <b>at same time</b>)
<code>|</code>, <code>or</code>, <code>+</code> — union (members of A, B or both groups)
<code>-</code> — difference (members of A group that are not in B group)
<code>^</code> — symmetric difference (members of A or B group, but not both)
<code>~</code>, <code>not</code>, unary <code>-</code> — negation (specifies a group that anybody joined except members of the group)

<b>Examples</b>:
<code>@mymusicgroup and @mychessgroup</code> — members of both groups at same time
<code>@nalinormods & ~@nalinormodschat</code> — subscribers of a channel that didn't join a group yet
<code>hikka_ub | hikka_talks | hikka_offtop</code> — members of any of these groups
<code>-1001234567890 - me</code> — members of a private group except yourself

ℹ️ In order to increase performance, the module caches the list of members for 10 minutes. Reload the module or restart the userbot to clear the cache.
""",
        "no_args": "❌ <b>Specify at least one group</b>",
        "syntax_error": (
            "❌ <b>You have an syntax error in query"
            " <code>{query}</code>:</b>\n<code>{error}</code>"
        ),
        "invalid_chat_id": "❌ <b>Invalid chat ID {chat_id}:</b>\n<code>{error}</code>",
        "running": "🕑 <b>Executing query <code>{query}</code>...</b>",
        "no_results": "🚫 <b>No results found</b> for query <code>{query}</code>",
        "results": "🔍 <b>{n} users found</b> for query <code>{query}</code>",
        "results_file": "📤 <b>The list is too long, so it's sent in file.</b>",
        "result_is_negated": (
            "⚠️ <b>The final set is negated, so result may be incomplete. "
            "Rewrite your query to get accurate results</b>"
        ),
    }

    strings_ru = {
        "_cls_doc": (
            "Поиск пересечения групп на предмет наличия одних и тех же пользователей"
        ),
        "_cmd_doc_mjoin": (
            "<юзернейм/ID группы> ... — Найти пользователей, которые находятся во всех"
            " заданных группах одновременно"
        ),
        "_cmd_doc_mquery": (
            "<запрос?> — Найти пользователей из групп по заданному запросу. Вызови без"
            " аргументов для получения справки для справки."
        ),
        "usage": """
📝 <b>Синтаксис модуля MembersQuery</b>

Для запросов используется часть синтаксиса Python.

Чтобы указать группы, используй их юзернейм (с или без @) или ID чата.
Также можно указать канал, в котором ты являешься админом. В канале есть лимит на получение макс. 200 пользователей, поэтому результаты могут быть неполными.
Чтобы указать себя, используй <code>me</code> или <code>self</code>.

Каждая группа представлена в виде множества её участников (см. теоримю множеств). Доступны следующие операции:
<code>&</code>, <code>and</code> — пересечение (участники и первой, и второй группы <b>одновременно</b>)
<code>|</code>, <code>or</code>, <code>+</code> — объединение (участники первой, второй или обеих групп)
<code>-</code> — разность (участники первой группы, которые не находятся во второй)
<code>^</code> — симметрическая разность (участники первой или второй группы, но не обеих)
<code>~</code>, <code>not</code>, <code>-</code> — отрицание (обозначает условную группу, в котором находятся все, кроме участников группы)

<b>Примеры использования</b>:
<code>@mymusicgroup and @mychessgroup</code> — участники обеих групп одновременно
<code>@nalinormods & ~@nalinormodschat</code> — подписчики канала, которые ещё не вступили в группу
<code>hikka_ub | hikka_talks | hikka_offtop</code> — участники любой из этих групп
<code>-1001234567890 - me</code> — участники приватной группы, кроме тебя

ℹ️ В целях производительности, модуль кэширует список участников на 10 минут. Перезагрузите модуль или весь юзербот, чтобы очистить кэш.
        """,
        "no_args": "❌ <b>Укажите хотя бы одну группу</b>",
        "syntax_error": (
            "❌ <b>В запросе <code>{query}</code> есть синтаксическая"
            " ошибка:</b>\n<code>{error}</code>"
        ),
        "invalid_chat_id": (
            "❌ <b>Неверный ID/юзернейм чата {chat_id}:</b>\n<code>{error}</code>"
        ),
        "running": "🕑 <b>Запрос <code>{query}</code> выполняется...</b>",
        "no_results": "🚫 <b>Результаты не найдены</b> по запросу <code>{query}</code>",
        "results": (
            "🔍 <b>Пользователей найдено: {n}</b> по запросу <code>{query}</code>"
        ),
        "results_file": (
            "📤 <b>Полученный список слишком большой, поэтому он отправлен в файле.</b>"
        ),
        "result_is_negated": (
            "⚠️ <b>Результат получен из отрицательного множества, поэтому он может быть"
            " неполным. Исправь запрос, чтобы получить точный результат</b>"
        ),
    }

    async def client_ready(self, client: TelegramClient, _):
        """client_ready hook"""
        self.client = client

        await client(JoinChannelRequest(channel=self.strings("author")))

    def format_results(
        self, query: str, results: NegatableSet, users: dict
    ) -> (str, "io.BytesIO | None"):
        """Formats results to be displayed in the message"""
        negated = results.negated
        if negated:
            results = set(users.keys()).difference(results)

        if not results:
            return self.strings("no_results").format(query=query), None

        text = self.strings("results").format(query=query, n=len(results)) + "\n\n"

        use_file = len(results) > 30
        formatted_results = (
            format_user(users[user_id], tags=not use_file) for user_id in results
        )

        if use_file:
            text += self.strings("results_file") + "\n\n"

            stream = io.BytesIO()
            stream.write("\n".join(formatted_results).encode("utf-8"))
            stream.seek(0)
            stream.name = "result.txt"
        else:
            text += "\n".join(formatted_results) + "\n\n"
            stream = None

        if negated:
            text += self.strings("result_is_negated")

        return text, stream

    async def mjoincmd(self, message: Message):
        """<username/chat ID> ... — Find users that are in all given chats at same time"""
        text = utils.get_args_raw(message)
        if not text:
            return await utils.answer(message, self.strings("no_args"))

        await self.mquerycmd(message, simplified=True)

    async def mquerycmd(self, message: Message, simplified: bool = False):
        """<query?> — Find users from given chats that match the query. Call without args for help."""
        text = utils.get_args_raw(message)
        if not text:
            return await utils.answer(message, self.strings("usage"))

        m = await utils.answer(message, self.strings("running").format(query=text))
        if isinstance(m, list):
            m = m[0]

        executor = UsersQueryExecutor(self.client)

        try:
            if simplified:
                result = await executor.execute_simplified(text.split())
            else:
                result = await executor.execute(text)
        except SyntaxError as e:
            await utils.answer(
                m, self.strings("syntax_error").format(error=e, query=text)
            )
            return
        except InvalidChatID as e:
            await utils.answer(
                m,
                self.strings("invalid_chat_id").format(
                    chat_id=e.chat_id, error=e.reason
                ),
            )
            return

        text, stream = self.format_results(text, result, executor.users)

        if stream:
            await self.client.send_file(
                message.chat_id,
                stream,
                caption=text,
                reply_to=message.reply_to_msg_id,
            )
            await m.delete()
        else:
            await utils.answer(m, text)
