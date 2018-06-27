
def ordered_unique_fields(query_string):
    '''
        Returns an ordered list of unique field names
        based on the query string passed in
    '''
    all_request_fields = [x.split('=')[0] for x in query_string.split('&')]
    unique_fields = set(all_request_fields)
    request_fields = []
    for field in all_request_fields:
        if field in unique_fields:
            request_fields.append(field)
            unique_fields.remove(field)
    return request_fields
