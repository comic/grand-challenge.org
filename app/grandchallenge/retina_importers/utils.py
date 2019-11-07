def upperize(val):
    """
    Converts string to uppercase if it exists
    :param val: string to be converted
    :return: converted string
    """
    if val is not None:
        return str(val).upper()
    else:
        return None


def exclude_val_from_dict(dictionary, key):
    """
    Remove a certain key/value pair from a dictionary and return the new one without changing the original one
    :param dictionary: original dictionary
    :param key: key of the value to be removed
    :return: new dictionary
    """
    dict_copy = dictionary.copy()
    del dict_copy[key]
    return dict_copy
