from .guildsetup import Guild_Setup
from .mod import Mod
from .owner import Owner
from .misc import Misc
from .tags import Tags
from .reminders import Reminders
from .events import Events
from .logging import Logging
from .info import Info
from .todo import Todo
from .help import HelpCommand
from .errorhandler import ErrorHandler
from .notes import Notes
from .support import Support
from .music import Music
from .protectedtags import ProtectedTags


def setup(bot):
    bot.add_cog(Guild_Setup(bot))
    bot.add_cog(Mod(bot))
    bot.add_cog(Owner(bot))
    bot.add_cog(Misc(bot))
    bot.add_cog(Tags(bot))
    bot.add_cog(Reminders(bot))
    bot.add_cog(Events(bot))
    bot.add_cog(Logging(bot))
    bot.add_cog(Info(bot))
    bot.add_cog(Todo(bot))
    bot.add_cog(HelpCommand(bot))
    # bot.add_cog(ErrorHandler(bot))
    bot.add_cog(Notes(bot))
    bot.add_cog(Support(bot))
    # I'll add this back when I figure out how to install pynacl
    # bot.add_cog(Music(bot))
    bot.add_cog(ProtectedTags(bot))
