from django.db.models.expressions import Func
from django.db import migrations, models

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


def _make_matview_migration(src, filters, name):
    data_clause = ("'{" + ','.join((
        '"%s":"%s"' % (k, filters[k])
        for k in sorted(filters)
    )) + "}'")
    count_only = not filters
    query = 'select %s from %s where data @>%s' % ('*', src, data_clause)
    drop_tmpl = ""
    #     DROP MATERIALIZED VIEW IF EXISTS %(name)s__count;
    #     DROP MATERIALIZED VIEW IF EXISTS %(name)s;
    # """
    main_matview_tmpl = """
        CREATE MATERIALIZED VIEW %(name)s AS %(query)s;
        CREATE UNIQUE INDEX %(name)s_pk ON %(name)s(id);
    """
    count_matview_tmpl = """
        CREATE MATERIALIZED VIEW %(name)s__count AS SELECT 1 AS id, COUNT(*) FROM %(count_src)s;
        CREATE UNIQUE INDEX %(name)s__count_pk ON %(name)s__count(id);
    """

    forward = drop_tmpl % locals()
    if not count_only:
        forward = forward + (main_matview_tmpl % locals())
        count_src = name
    else:
        count_src = src
    forward = forward + (count_matview_tmpl % locals())

    return migrations.RunSQL(
        forward,
        """
        DROP MATERIALIZED VIEW IF EXISTS %(name)s__count;
        DROP MATERIALIZED VIEW IF EXISTS %(name)s;
        """ % locals()
    )


def delete_matview(MatView, filters):
    MatView.objects.filter(filters=filters).delete()


def get_matview_name(model, filters):
    app_label, model_name = model.split('.')
    name = '_xx_'.join(
        '%s_%s' % (k, filters[k])
        for k in sorted(filters.keys())
    )
    name = 'matview_mv_%s_%s_%s' % (app_label, model_name, name)
    return name.lower().strip('_')


def _create_matview_instance(model, filters, src, src_name):
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
        migrations.CreateModel(
            name='%s_count' % (name,),
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField()),
            ],
            options={
                'db_table': '%s__count' % (name,),
                'managed': False,
            },
        ),
        migrations.RunPython(
            _create_matview_instance(model, all_filters, parent, src_name),
            lambda apps, schema: delete_matview(apps.get_model("matview", "MatView"), filters)
        ),
    ]
