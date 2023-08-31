class Event:
    def __init__(self, data):
        if data.startswith('[[LOG]]'):
            self.type = 'LOG'
            self.misc, self.text = Event.parseLog(data)

        elif data.startswith('[[SUC]]'):
            self.type = 'SUC'
            self.misc = {}
            self.text = data[7:]

        elif data.startswith('[[ERR]]'):
            self.type = 'ERR'
            self.misc = {}
            self.text = data[7:]

        else:
            self.type = None
            self.misc = None
            self.text = data

    @classmethod
    def parseLog(cls, data):
        data = data[7:].lstrip()
        if data[0] != '[': return {}, data
        inside = data[1:].split(']')[0]
        outside = data[len(inside) + 2:]
        if '[' in inside or ']' in inside: return {}, outside
        assignments = inside.split(',')
        misc = dict([(a.split('=')[0].strip(), a.split('=')[1].strip()) 
                     for a in assignments])
        misc['ellipsis'] = misc.get('ellipsis', 'false').lower() == 'true'
        return misc, outside

class Window:
    BLANK = '‎ '

    def __init__(self, ctx):
        self._ctx = ctx
        self._interaction = None
        self._events = []
        self._update = True
        self.min_height = 5
        self.max_height = 20

    def _build(self):
        if not self._events: return f"```diff\n{Window.BLANK}\n```"
        line_width = 1_000_000_000_000

        buff = "```diff\n"

        status = None
        lines = []
        for i in reversed(range(len(self._events))):
            ante = self._events[i - 1] if i > 0 else None
            post = self._events[i + 1] if i < len(self._events) - 1 else None
            curr = self._events[i]
            prefix = ""
            text = curr.text

            if curr.type == 'LOG' and curr.misc.get('ellipsis', False):
                if i == len(self._events) - 1:
                    text += '...'
                if status == 'ERR':
                    prefix = '- '
                elif status == 'SUC':
                    prefix = '+ '
                elif i == len(self._events) - 1:
                    prefix = '> '
                status = None

            elif curr.type == 'LOG':
                prefix = '> '
                status = None

            elif curr.type == 'ERR':
                prefix = '- '
                status = curr.type

            elif curr.type == 'SUC':
                prefix = '+ '
                status = curr.type

            else:
                prefix = " "
                if ante is not None and ante.type is not None:
                    text = text + f'{Window.BLANK}\n' * 3
                if post is not None and post.type is not None:
                    text = f'{Window.BLANK}\n' * 3 + text

            text_width = line_width - len(prefix)
            for text1 in text.splitlines():
                for begin in range(0, len(text1), text_width):
                    chunk = text1[begin : begin + text_width]
                    chunk = prefix + chunk
                    lines.append(chunk)

            if len(lines) >= self.max_height:
                break

        buff += '\n'.join(reversed(lines[:self.max_height]))
        buff += "```"
        return buff

    async def render(self):
        if not self._interaction:
            self._interaction = await self._ctx.respond(Window.BLANK)

        if not self._update: return
        if self._interaction:
            buff = self._build()
            await self._interaction.edit_original_response(content=buff)

        self._update = False

    async def init(self):
        await self.render()

    def open(self):
        pass

    def close(self):
        pass

    def update(self, data):
        self._events.append(Event(data))
        self._update = True
