# data->>'age' has been imported as text, should be integer

from django.db import migrations, connection


def update_age(apps, schema):
    NCVoter = apps.get_model('voter.NCVoter')

    # Doing these individually would be slow. Maybe we can finesse it.

    # Here's some SQL to update a batch at once (those with age '20'):
    #
    # update voter_ncvoter set data = data || '{"age": 20}' where data->>'age' = '20';
    #
    # I have not been able to come up with SQL that will update all records in one
    # go, but we can iterate pretty easily over the range of reasonable ages
    # and do this in 150 batches rather than individually to millions of records.

    with connection.cursor() as cursor:
        for age in range(150):
            sql = """update voter_ncvoter set data = data || '{"age": %s}' where data->>'age' = '%s';""" % (age, age)
            cursor.execute(sql)
            print("Age: %d, updated rows: %d" % (age, cursor.rowcount))


def make_age_text_again(apps, schema):
    # This is mainly so I can test the migration repeatedly.
    # This is not optimized as I have no intention of running it on production data,
    # but it could be, similarly to the forward method above.
    NCVoter = apps.get_model('voter.NCVoter')

    for voter in NCVoter.objects.filter(data__has_key='age'):
        voter.data['age'] = str(voter.data['age'])
        voter.save()


class Migration(migrations.Migration):

    dependencies = [
        ('voter', '0028_auto_20180531_1319'),
    ]

    operations = [
        migrations.RunPython(
            update_age,
            make_age_text_again
        )
    ]
