# Bypass all Hikka limitations
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

import logging

from telethon import TelegramClient
from telethon.tl.custom import Message
from telethon.tl.functions.channels import JoinChannelRequest

from .. import loader, utils

logger = logging.getLogger(__name__)


class NoCoreModsList(list):
    """
    List w/o objects with x.__origin__ == "<core>"
    """
    def __init__(self, sequence=None):
        super().__init__()
        self += sequence or []

    def __iadd__(self, sequence):
        for x in sequence:
            if getattr(x, "__origin__", "") == "<core>":
                x.__origin__ = "<file>"
        return super().__iadd__(sequence)


# noinspection PyCallingNonCallable,PyAttributeOutsideInit
# pylint: disable=not-callable,attribute-defined-outside-init,invalid-name
@loader.tds
class HikkaBypassMod(loader.Module):
    """Bypass all Hikka limitations"""

    strings = {
        "name": "HikkaBypass",
        "author": "@nalinormods",
    }

    async def on_dlmod(self, client: TelegramClient, _):
        """on_dlmod hook"""
        await client(JoinChannelRequest(channel=self.strings("author")))

    async def client_ready(self, client: TelegramClient, db):
        """client_ready hook"""
        if not hasattr(self, "hikka"):
            raise loader.LoadError("Hikka only")

        self.client: TelegramClient = client
        self.db = db

        client.loader._core_commands = type(
            "AlwaysEmptyList",
            (list,),
            {"__iadd__": lambda self, x: self},
        )()
        client.loader.modules = NoCoreModsList()
        client.bypass_completed = True
        logger.info("Bypas completed")
