from urllib.parse import parse_qsl


def ordered_unique_keys(query_string):
    '''
        Returns an ordered list of unique key names based on the query
        string passed in.  The values, in this case, are igonored.
    '''
    all_request_fields = [x[0] for x in parse_qsl(query_string)]
    unique_fields = []
    for field in all_request_fields:
        if field not in unique_fields:
            unique_fields.append(field)
    return unique_fields
