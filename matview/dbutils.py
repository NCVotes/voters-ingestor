from django.db import migrations

from .models import MatView


def _make_matview_migration(src, filters, name):
    """Generate the SQL strings forward and backwards to create and drop materialized views.

    This create a second view which simply materializes a count of the regular one. Both have
    a unique index to allow concurrent updates.
    """

    data_clause = ("'{" + ','.join((
        '"%s":"%s"' % (k, filters[k])
        for k in sorted(filters)
    )) + "}'")
    count_only = not filters
    query = 'select %s from %s where data @>%s' % ('*', src, data_clause)
    main_matview_tmpl = """
        CREATE MATERIALIZED VIEW %(name)s AS %(query)s;
        CREATE UNIQUE INDEX %(name)s_pk ON %(name)s(id);
    """
    count_matview_tmpl = """
        CREATE MATERIALIZED VIEW %(name)s__count AS SELECT 1 AS id, COUNT(*) FROM %(count_src)s;
        CREATE UNIQUE INDEX %(name)s__count_pk ON %(name)s__count(id);
    """

    forward = ""
    if not count_only:
        forward = forward + (main_matview_tmpl % locals())
        count_src = name
    else:
        count_src = src
    forward = forward + (count_matview_tmpl % locals())

    return migrations.RunSQL(
        forward,
        """
        DROP MATERIALIZED VIEW IF EXISTS %(name)s__count CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS %(name)s CASCADE;
        """ % locals()
    )


def get_matview_name(model, filters):
    """Generate the name of a materialized view for a model and a given set of filters."""

    app_label, model_name = model.split('.')
    name = '_xx_'.join(
        '%s_%s' % (k, filters[k])
        for k in sorted(filters.keys())
    )
    name = 'matview_mv_%s_%s_%s' % (app_label, model_name, name)
    return name.lower().strip('_')


def _create_matview_instance(model, filters, src, src_name):
    """Create a python migration function that will create a MatView for our materialized view."""

    def _(apps, schema):
        name = get_matview_name(model, filters)
        parent_id = MatView.objects.get(matview_name=src_name).id if src else None
        apps.get_model("matview", "MatView").objects.create(
            parent_id=parent_id,
            src_name=src_name,
            matview_name=name,
            filters=filters,
        )
    return _


def make_matview_migration(model, parent, filters):
    """Generate a list of migation steps to create one or more materialized views of a data query.

    The generated migrations include a MATERIALIZED VIEW sql statement and a MatView instance to
    represent it for us.

    `model` is a "appname.modelname" style string representing a large queryable model
    `filters` is a dictionary of key/value pairs that much match in the model's `data` JSON field
    `parent` is None if the model will be queried directly
        If `parent` is its own set of filters, it must not share any keys with `filters` and an
        existing materialized view must match the parameters to be queried.

        This allows us to build, for example, materialized views for each of the parties and then
        MVs by gender which query *those* rather than the original table.

        These are not valid, alone:

            make_matview_migration("voter.NCVoter", {"party_cd": "REP"}, {"gender_code": "F"})
            make_matview_migration("voter.NCVoter", {"party_cd": "REP"}, {"gender_code": "M"})

        But these are:

            make_matview_migration("voter.NCVoter", None, {"party_cd": "REP"})
            make_matview_migration("voter.NCVoter", {"party_cd": "REP"}, {"gender_code": "F"})
            make_matview_migration("voter.NCVoter", {"party_cd": "REP"}, {"gender_code": "M"})

        And these versions would be much too slow to update, because each one would have to re-query
        the original large table.

            make_matview_migration("voter.NCVoter", {"party_cd": "REP", "gender_code": "F"})
            make_matview_migration("voter.NCVoter", {"party_cd": "REP", "gender_code": "M"})
    """

    if parent:
        src_name = get_matview_name(model, parent)
        # Keys cannot exist in both parent and subset filter
        assert set(parent) - set(filters) == set(parent)
        all_filters = {}
        all_filters.update(parent)
        all_filters.update(filters)
    else:
        app_label, model_name = model.split('.')
        src_name = ('%s_%s' % (app_label, model_name))
        all_filters = filters

    name = get_matview_name(model, all_filters)

    return [
        _make_matview_migration(src_name, filters, name),
        migrations.RunPython(
            _create_matview_instance(model, all_filters, parent, src_name),
            lambda apps, schema: apps.get_model("matview", "MatView").objects.filter(filters=filters).delete()
        ),
    ]
