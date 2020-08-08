from .automod import AutoMod
from .errorhandler import ErrorHandler
from .events import Events
from .giveaway import Giveaway
from .guildsetup import Guild_Setup
from .help import HelpCommand
from .infractions import Infractions
from .info import Info
from .logging import Logging
from .misc import Misc
from .mod import Mod
from .music import Music
from .notes import Notes
from .owner import Owner
from .protectedtags import ProtectedTags
from .reminders import Reminders
from .tags import Tags
from .todo import Todo
from .trivia import Trivia
from .spreadsheet import SpreadSheets
from .support import Support


def setup(bot):
    bot.add_cog(AutoMod(bot))
    bot.add_cog(ErrorHandler(bot))
    bot.add_cog(Events(bot))
    bot.add_cog(Giveaway(bot))
    bot.add_cog(Guild_Setup(bot))
    bot.add_cog(HelpCommand(bot))
    bot.add_cog(Infractions(bot))
    bot.add_cog(Info(bot))
    bot.add_cog(Logging(bot))
    bot.add_cog(Misc(bot))
    bot.add_cog(Mod(bot))
    # I'll add this back when I figure out how to install pynacl
    # bot.add_cog(Music(bot))
    bot.add_cog(Notes(bot))
    bot.add_cog(Owner(bot))
    bot.add_cog(ProtectedTags(bot))
    bot.add_cog(Reminders(bot))
    bot.add_cog(Tags(bot))
    bot.add_cog(Todo(bot))
    bot.add_cog(Trivia(bot))
    bot.add_cog(SpreadSheets(bot))
    bot.add_cog(Support(bot))
