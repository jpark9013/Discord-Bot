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
