def log(*args):
    if not args:
        print("[[LOG]]", flush=True)
        return

    ellipsis = args[-1] == ...
    if ellipsis: args = args[:-1]
    txt = ' '.join(map(str, args))
    print(f"[[LOG]][{ellipsis=}] {txt}", flush=True)

def error(*args):
    if not args:
        print("[[ERR]]", flush=True)
        return

    txt = ' '.join(map(str, args))
    print(f"[[ERR]] {txt}", flush=True)

def success(*args):
    if not args:
        print("[[SUC]]", flush=True)
        return

    txt = ' '.join(map(str, args))
    print(f"[[SUC]] {txt}", flush=True)
