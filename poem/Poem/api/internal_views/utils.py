import json

import requests
from Poem.api.models import MyAPIKey
from Poem.helpers.history_helpers import create_profile_history
from Poem.poem import models as poem_models
from Poem.poem_super_admin import models as admin_models
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from tenant_schemas.utils import schema_context, get_public_schema_name


def error_response(status_code=None, detail=''):
    return Response({'detail': detail}, status=status_code)


def one_value_inline(input):
    if input:
        return json.loads(input)[0]
    else:
        return ''


def two_value_inline(input):
    results = []

    if input:
        data = json.loads(input)

        for item in data:
            if len(item.split(' ')) == 1:
                results.append({
                    'key': item.split(' ')[0],
                    'value': ''
                })
            else:
                val = ' '.join(item.split(' ')[1:])
                results.append(({'key': item.split(' ')[0],
                                 'value': val}))

    return results


def inline_metric_for_db(data):
    result = []

    for item in data:
        if item['key']:
            result.append('{} {}'.format(item['key'], item['value']))

    if result:
        return json.dumps(result)

    else:
        return ''


def two_value_inline_dict(input):
    results = dict()

    if input:
        data = json.loads(input)

        for item in data:
            if len(item.split(' ')) == 1:
                results.update({item.split(' ')[0]: ''})
            else:
                val = ' '.join(item.split(' ')[1:])
                results.update(({item.split(' ')[0]: val}))

    return results


def sync_webapi(api, model):
    token = MyAPIKey.objects.get(name="WEB-API")

    headers = {'Accept': 'application/json', 'x-api-key': token.token}
    response = requests.get(api,
                            headers=headers,
                            timeout=180)
    response.raise_for_status()
    data = response.json()['data']

    data_api = set([p['id'] for p in data])
    data_db = set(model.objects.all().values_list('apiid', flat=True))
    entries_not_indb = data_api.difference(data_db)
    entries_indb = data_api.intersection(data_db)

    new_entries = []
    for p in data:
        if p['id'] in entries_not_indb:
            if p.get('info', False):
                new_entries.append(
                    dict(name=p['info']['name'], description=p['info'].get('description', ''),
                        apiid=p['id'], groupname='')
                )
            else:
                new_entries.append(
                    dict(name=p['name'], description=p.get('description', ''),
                        apiid=p['id'], groupname='')
                )

    if new_entries:
        for entry in new_entries:
            instance = model.objects.create(**entry)

            if isinstance(instance, poem_models.MetricProfiles):
                services = []
                for item in data:
                    if item['id'] == instance.apiid:
                        for service in item['services']:
                            for metric in service['metrics']:
                                services.append(
                                    dict(
                                        service=service['service'],
                                        metric=metric
                                    )
                                )
                        description = item.get('description', '')
                create_profile_history(instance, services, 'poem', description)

            if isinstance(instance, poem_models.Aggregation):
                for item in data:
                    if item['id'] == instance.apiid:
                        aggr_data = {
                            'endpoint_group': item['endpoint_group'],
                            'metric_operation': item['metric_operation'],
                            'profile_operation': item['profile_operation'],
                            'metric_profile': item['metric_profile']['name'],
                            'groups': item['groups']
                        }
                create_profile_history(instance, aggr_data, 'poem')

            if isinstance(instance, poem_models.ThresholdsProfiles):
                for item in data:
                    if item['id'] == instance.apiid:
                        tp_data = {'rules': item['rules']}
                create_profile_history(instance, tp_data, 'poem')

    entries_deleted_onapi = data_db.difference(data_api)
    for p in entries_deleted_onapi:
        instance = model.objects.get(apiid=p)
        poem_models.TenantHistory.objects.filter(
            object_id=instance.id,
            content_type=ContentType.objects.get_for_model(model)
        ).delete()
        instance.delete()

    for p in data:
        if p['id'] in entries_indb:
            instance = model.objects.get(apiid=p['id'])
            if p.get('info', False):
                instance.name = p['info']['name']
                instance.description = p['info'].get('description', '')
            else:
                instance.name = p['name']
                instance.description = p.get('description', '')
            instance.save()


def get_tenant_resources(schema_name):
    with schema_context(schema_name):
        if schema_name == get_public_schema_name():
            metrics = admin_models.MetricTemplate.objects.all()
            met_key = 'metric_templates'
        else:
            metrics = poem_models.Metric.objects.all()
            met_key = 'metrics'
        n_met = metrics.count()

        probes = set()
        for metric in metrics:
            if metric.probekey:
                probes.add(metric.probekey)

        n_probe = len(probes)

        return {met_key: n_met, 'probes': n_probe}
