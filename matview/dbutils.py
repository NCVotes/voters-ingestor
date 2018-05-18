from django.db.models.expressions import Func
from django.db import migrations

from .models import MatView


class ArrayAppend(Func):
    function = 'array_append'
    template = "%(function)s(%(expressions)s, %(element)s)"
    arity = 1

    def __init__(self, expression: str, element, **extra):
        if not isinstance(element, (str, int)):
            raise TypeError(
                f'Type of "{element}" must be int or str, '
                f'not "{type(element).__name__}".'
            )

        super().__init__(
            expression,
            element=isinstance(element, int) and element or f"'{element}'",
            **extra,
        )


def _make_matview_migration(src, data_clause, name):
    query = 'select %s from %s where data @>%s' % ('*', src, data_clause)
    forward_tmpl = """
        CREATE MATERIALIZED VIEW %(name)s AS %(query)s;
        CREATE UNIQUE INDEX %(name)s_pk ON %(name)s(id);
    """
    forward = (forward_tmpl % locals()) \
        + ("CREATE MATERIALIZED VIEW %(name)s__count AS SELECT COUNT(*) FROM %(name)s" % locals())

    return migrations.RunSQL(
        forward,
        """
        DROP MATERIALIZED VIEW IF EXISTS %(name)s__count;
        DROP MATERIALIZED VIEW IF EXISTS %(name)s;
        """ % locals()
    )


def delete_matview(MatView, filters):
    MatView.objects.filter(filters=filters).delete()


def get_matview_name(filters):
    name = '__'.join(
        '%s_%s' % (k, filters[k])
        for k in sorted(filters.keys())
    )
    name = 'matview_mv_' + name
    return name.lower()


def make_matview_migration(model, filters):
    fkeys = sorted(filters.keys())
    name = get_matview_name(filters)
    data_clause = ''.join(["'{"] +
        [
            '"%s":"%s"' % (k, filters[k])
            for k in fkeys
        ] +
    ["}'"])
    app_label, model_name = model.split('.')
    table_name = ('%s_%s' % (app_label, model_name))

    return [
        _make_matview_migration(table_name, data_clause, name),
        migrations.RunPython(lambda apps, schema: apps.get_model("matview", "MatView").objects.create(
            parent=None,
            model_name=model,
            filters=filters,
            table_name=table_name
        ), lambda apps, schema: delete_matview(apps.get_model("matview", "MatView"), filters)),
    ]
