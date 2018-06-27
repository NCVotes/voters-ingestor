import logging
from collections import OrderedDict
from copy import copy
from typing import Tuple, Dict, List, Optional

from django.http import HttpRequest
from django.template.loader import get_template

from voter.models import NCVoter


logger = logging.getLogger(__name__)


class Filter:
    """
    Abstract class that represents a filter.

    Subclasses provide different types of filters (e.g. ChoiceFilter).

    Instances of subclasses provide the filters we're showing to the users,
    e.g. filter by political party.  Those are generally managed as a list
    that can be passed to filters_from_request (below).

    Copies of those instances represent the selections a user has made
    on the current page, and are returned by filters_from_request.
    """

    # Default template for rendering a filter's current values in a form.
    values_template = "drilldown/filter_values.html"

    # No default editing template
    editing_template = None

    def __init__(self, display_name: str, field_name: str):
        """
        display_name: str, e.g. "Party" or "County"
        field_name: name of the db field from NCVoterQueryView. Also used as the HTML input field name.
        """
        self.display_name = display_name
        self.field_name = field_name
        self.values = None
        self.errors = None

    def set_values(self, values: List[str]):
        """
        Set the user's selections for this filter on this filter object.

        Override to do data validation, type conversion, etc.

        Result should be that self.values is a list of values.
        """
        self.values = values

    def get_filter_params(self) -> Dict:
        """
        Return a dictionary with kwargs for filter() or Q() to narrow
        a queryset using this filter.
        """
        raise NotImplementedError  # pragma: nocover

    def render_values(self) -> str:
        """
        Return HTML for hidden input field(s) with the filter's current values.
        """
        return get_template(self.values_template).render({'filter': self})

    def render_for_editing(self) -> str:
        """
        Return HTML to set the value(s) of the current filter.
        """
        return get_template(self.editing_template).render({'filter': self})


class ChoiceFilter(Filter):
    """
    choices: iterable of (value, label, description) tuples
    value: the actual value in the DB
    label: short string to be used in the dropdown when selecting this choice
    description: shown after a filter has been chosen, should able to be
           inserted in the phrase "Showing voters who <Description>".
           E.g. "are <em>female</em>", "live in <em>Orange</em> county",
           "have an <em>active</em> registration".
           By convention we put ``em`` around the part that can change.
    """
    editing_template = "drilldown/edit_choice_filter.html"

    def __init__(self, display_name: str, field_name: str, choices: List[Tuple]):
        super().__init__(display_name, field_name)
        self.choices = choices
        if not choices:
            raise ValueError("Choices must not be empty")

        for choice in choices:
            if len(choice) != 3:
                raise ValueError("""Each choice should be a 3-tuple: (<value>, <label>, <description>).
                    value: the actual value in the DB
                    label: short string to be used in the dropdown when selecting this choice
                    description: shown after a filter has been chosen, should able to be
                       inserted in the phrase "Showing voters who <Description>".
                       E.g. "are <em>female</em>", "live in <em>Orange</em> county".""")

    def get_filter_params(self) -> Dict:
        return {self.field_name: self.values[0]}

    def description(self) -> Optional[str]:
        """
        Return the appropriate description for the currently selected choice.
        Or None.
        """
        selected_value = self.values[0]
        for value, label, description in self.choices:
            if value == selected_value:
                return description


class FreeTextFilter(Filter):
    """
    a simple input without any dropdown options.  prefix is used in the despcription of
    the filter on the front-end. e.g 'live within' for zipcodes.
    """
    editing_template = "drilldown/edit_free_text_filter.html"

    def __init__(self, display_name: str, field_name: str, prefix: str):
        super().__init__(display_name, field_name)
        self.prefix = prefix

    def get_filter_params(self) -> Dict:
        return {self.field_name: self.values[0]}

    def description(self) -> Optional[str]:
        """
        Return the appropriate description for the currently selected choice.
        Or None.
        """
        return '%s %s' % (self.prefix, self.values[0])


class AgeFilter(Filter):
    """
    Min and max ages.  values = [min, max] (integers)
    """
    editing_template = "drilldown/edit_age_filter.html"

    def __init__(self):
        super().__init__(display_name='Age', field_name='age')

    def set_values(self, values: List[str]):
        # Input values are strs because they come from the request parameters
        if not hasattr(values, '__iter__') or isinstance(values, str):
            raise ValueError("Values must be iterable")
        if len(values) != 2:
            raise ValueError("Values for age should be a minimum and maximum")
        self.values = [int(v) if v else None for v in values]
        # Make sure values are lowest first
        if None not in self.values:
            if self.values[1] < self.values[0]:
                self.values = [self.values[1], self.values[0]]
        if self.values == [None, None]:
            self.errors = ["Must enter min age, max age, or both."]

    def get_filter_params(self) -> Dict:
        age_filter = {}
        if self.values[0]:
            age_filter["age__gte"] = self.values[0]
        if self.values[1]:
            age_filter["age__lte"] = self.values[1]
        return age_filter

    def description(self) -> str:
        """
        Return the appropriate description for the currently selected choice.
        """
        values = self.values
        if values[0] is None:
            return "have age less than or equal to %d" % (values[1],)
        elif values[1] is None:
            return "have age greater than or equal to %d" % (values[0],)
        else:
            return "have age between %d and %d" % (values[0], values[1])


class MultiChoiceFilter(ChoiceFilter):
    """
    This is a filter that allows multiple selections which are joined by 'OR' when querying the
    database. It renders (by default) as a multi-select widget.
    """

    editing_template = "drilldown/edit_multichoice_filter.html"

    def get_filter_params(self) -> Dict:
        # convert a filter like {'race_code': ['B', 'W']} to {'race_code__in': ['B', 'W']}
        return {self.field_name + "__in": self.values}

    def get_label(self, chosen_code):
        """
        Return the label for a chosen code, or None if not present.
        """
        for (code, label, description) in self.choices:
            if code == chosen_code:
                return label

    def description(self) -> str:
        """
        Return the appropriate description for the currently selected choice.
        """
        values = self.values
        desc = ""
        for v in values:
            label = self.get_label(v)
            if label:
                if desc:
                    desc += " or "
                desc += label
        return "have %s of <em>%s</em>" % (self.display_name, desc,)


def get_filter_by_name(filter_list, field_name):
    for filter in filter_list:
        if filter.field_name == field_name:
            return filter


def filters_from_request(declared_filters: List[Filter], request: HttpRequest) -> Tuple[OrderedDict, Dict]:
    """
    Given a list of Filter objects, and an HTTP request:
    Using the GET parameters from the request, in order, create a new
    OrderedDict containing copies of the Filter objects corresponding
    to the query parameter keys, with the values from the query string
    set in them.
    Set '.filter_params' on each new filter to be the cumulative filter parameters.
    Set '.count' on each new filter to be the count after applying those filters.

    Returns a tuple containing:
     - an ordered dict with the applied filter objects keyed by field name.
     - a dict with the final set of filter parameters.
    """
    applied_filters = OrderedDict()
    filter_params = {}

    # constructing 'request_fields' in lieu of request.GET to assure the query string be read in order
    all_request_fields = [x.split('=')[0] for x in request.META['QUERY_STRING'].split('&')]
    unique_fields = set(all_request_fields)
    request_fields = []
    for field in all_request_fields:
        if field in unique_fields:
            request_fields.append(field)
            unique_fields.remove(field)

    for field_name in request_fields:
        filter_inst = copy(get_filter_by_name(declared_filters, field_name))
        if filter_inst:
            filter_inst.set_values(request.GET.getlist(field_name))
        else:
            # This is either a ProgrammingError (need to add field_name to declared_filters), or a
            # user adding a parameter to the GET request. Log it and ignore.
            logger.warning('URL had a filter that is not in declared_filters: %s', field_name)
            continue
        filter_params.update(filter_inst.get_filter_params())
        filter_inst.count = NCVoter.get_count(filter_params)
        filter_inst.filter_params = filter_params

        applied_filters[field_name] = filter_inst

    return applied_filters, filter_params
