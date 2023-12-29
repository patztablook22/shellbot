import discord

class Complete:
    def __init__(self, bot, all_options=None, max_history=100):
        self._bot = bot
        self._all_options = all_options
        self._history = {}
        self._max_history = 100

    def update_history(self, ctx, item):
        if ctx.author.id not in self._history:
            self._history[ctx.author.id] = []

        history = self._history[ctx.author.id]
        history.append(item)
        if len(history) > self._max_history:
            history.pop(0)

    @property
    def autocomplete(self):
        def complete_inner(ctx: discord.AutocompleteContext):
            if not self._bot.permitted(ctx.interaction.user): return []

            history = self._history.get(ctx.interaction.user.id, [])
            if self._all_options is None:
                return history[::-1]

            def how_recent(item):
                if item in history:
                    return -history.index(item)
                return 1

            buff = self._all_options()
            return list(sorted(buff, key=how_recent))
        return discord.utils.basic_autocomplete(complete_inner)
