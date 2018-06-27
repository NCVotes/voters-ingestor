from urllib.parse import parse_qsl


def ordered_unique_fields(query_string):
    '''
        Returns an ordered list of unique field names
        based on the query string passed in
    '''
    all_request_fields = [x[0] for x in parse_qsl(query_string)]
    unique_fields = set(all_request_fields)
    request_fields = []
    for field in all_request_fields:
        if field in unique_fields:
            request_fields.append(field)
            unique_fields.remove(field)
    return request_fields
