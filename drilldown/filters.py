from collections import OrderedDict
from copy import copy
from typing import Tuple, Dict, List, Optional

from django.http import HttpRequest
from django.template import Template, Context

from queryviews.models import get_count


class Filter:
    """
    Abstract class that represents a filter.

    Subclasses provide different types of filters (e.g. ChoiceFilter).

    Instances of subclasses provide the filters we're showing to the users,
    e.g. filter by political party.  Those are generally managed as a list
    that can be passed to filters_from_request (below).

    Copies of those instances represent the selections a user has made
    on the current page, and are returned by filters_from-request.
    """

    # Default template for rendering a filter's current values in a form.
    values_template = Template(
        """
            {% for value in filter.values %}
                <input name="{{ filter.field_name }}" type="hidden" value="{{ value }}"/>
            {% endfor %}
        """
    )

    def __init__(self, display_name: str, field_name: str):
        """
        display_name: str, e.g. "Party" or "County"
        field_name: name of the db field inside 'data'. Also used as the HTML input field name.
        """
        self.display_name = display_name
        self.field_name = field_name
        self.values = None

    def set_values(self, values: List[str]):
        """
        Set the user's selections for this filter on this filter object.

        Override to do data validation, type conversion, etc.

        Result should be that self.values is a list of values.
        """
        self.values = values

    def get_filter_parms(self) -> Dict:
        """
        Return a dictionary with kwargs for filter() or Q() to narrow
        a queryset using this filter.
        """
        if self.values is None:
            raise ValueError("Cannot get_query_filters on a filter whose values have not been set")
        raise NotImplementedError  # Must override this

    def render_values(self) -> str:
        """
        Return HTML for hidden input field(s) with the filter's current values.
        """
        return self.values_template.render(Context({'filter': self}))

    def render_for_editing(self) -> str:
        """
        Return HTML to set the value(s) of the current filter.
        """
        return self.editing_template.render(Context({'filter': self}))


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
    editing_template = Template("""
        <select name="{{ filter.field_name }}">
          <option>-</option>
          {% for value, label, foo in filter.choices %}
            <option value="{{ value }}" {% if value in filter.values %}selected{% endif %}>{{ label }}</option><br/>
          {% endfor %}
        </select>
    """)

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

    def get_filter_parms(self) -> Dict:
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


class AgeFilter(Filter):
    """
    Min and max ages.  values = [min, max] (integers)
    """
    editing_template = Template("""
        <input name="age" value="{{ filter.values.0 }}" type="number" placeholder="lowest age to include">
        &ndash;
        <input name="age" value="{{ filter.values.1 }}" type="number" placeholder="highest age to include">
    """)

    def __init__(self):
        super().__init__(display_name='Age', field_name='age')

    def set_values(self, values: List[str]):
        # Input values are strs because they come from the request parameters
        if not hasattr(values, '__iter__') or isinstance(values, str):
            raise ValueError("Values must be iterable")
        if len(values) != 2:
            raise ValueError("Values for age should be a minimum and maximum")
        self.values = [int(v) for v in values]
        # Make sure values are lowest first
        if self.values[1] < self.values[0]:
            self.values = [self.values[1], self.values[0]]

    def get_filter_parms(self) -> Dict:
        return dict(age__gte=self.values[0], age__lte=self.values[1])

    def description(self) -> str:
        """
        Return the appropriate description for the currently selected choice.
        """
        values = self.values
        return "have age between %d and %d" % (values[0], values[1])


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
    Set '.filter_parms' on each new filter to be the cumulative filter parameters.
    Set '.count' on each new filter to be the count after applying those filters.

    Returns a tuple containing:
     - an ordered dict with the applied filter objects keyed by field name.
     - a dict with the final set of filter parameters.
    """
    applied_filters = OrderedDict()
    filter_parms = {}

    for field_name in request.GET:
        applied_filter = copy(get_filter_by_name(declared_filters, field_name))
        applied_filter.set_values(request.GET.getlist(field_name))

        filter_parms.update(applied_filter.get_filter_parms())
        applied_filter.count = get_count('voter.NCVoter', filter_parms)
        applied_filter.filter_parms = filter_parms

        applied_filters[field_name] = applied_filter

    return applied_filters, filter_parms
