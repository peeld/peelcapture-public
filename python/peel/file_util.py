import os.path


def fix_name(name):
    """ fix a take or file name prior to string compare functions """
    return name.lower().replace('-', '_').replace(' ', '_')


def take_compare(file, take):
    """ compare a file name with a take name as a match """
    if '/' in file or '\\' in file:
        file = os.path.split(file)[1]

    file = fix_name(os.path.splitext(file)[0])
    take = fix_name(take)

    return file.startswith(take)


def find_take(file, take_list):

    for take in take_list:
        if take_compare(file, take):
            return take
    return None


def pretty_bytes(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"