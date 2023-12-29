import shellbot
import sys
import json
import watchdog.events, watchdog.observers


shellbot.Shellbot()

def config(path):
    kwargs = json.load(open(path))
    token = kwargs['token']
    del kwargs['token']
    return kwargs, token

def main(argv):
    config_path = argv[1]
    kwargs, token = config(config_path)

    bot = shellbot.Shellbot(**kwargs)
    observer = watchdog.observers.Observer()

    class Handler(watchdog.events.FileSystemEventHandler):
        def on_modified(self, event):
            print("Reloading changes...")
            kwargs, _ = config(config_path)
            bot.set(**kwargs)

    handler = Handler()
    observer.schedule(handler, config_path)

    #observer.start()
    bot.run(token)
    #observer.join()

if __name__ == '__main__':
    main(sys.argv)
