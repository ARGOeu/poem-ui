from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework import status

from rest_framework_api_key import models as api_models

from queue import Queue

from Poem.poem import models as poem_models
from Poem.poem.saml2.config import tenant_from_request, saml_login_string

from .views import NotFound
from . import serializers


class Tree:
    class Node:
        def __init__(self, nodename):
            self._nodename = nodename
            self._child = []

        def parent(self):
            return self._parent

        def child(self, i):
            return self._child[i]

        def childs(self):
            return self._child

        def numchilds(self):
            return len(self._child)

        def find(self, nodename):
            length = len(self._child)
            if length > 0:
                for i in range(length):
                    if self._child[i].name() == nodename:
                        return i
            return -1

        def name(self):
            return self._nodename

        def is_leaf(self):
            if self.numchilds() == 0:
                return True
            else:
                return False

        def __str__(self):
            return self._nodename

    def __init__(self):
        self.root = None
        self._size = 0

    def __len__(self):
        return self._size

    def addroot(self, e):
        self.root = self.Node(e)
        return self.root

    def breadthfirst(self):
        fringe = Queue()
        fringe.put(self.root)
        while not fringe.empty():
            p = fringe.get()
            yield p
            for c in p.childs():
                fringe.put(c)

    def addchild(self, e, p):
        c = self.Node(e)
        c._parent = p
        p._child.append(c)
        self._size += 1
        return c

    def is_empty(self):
        return len(self) == 0

    def preorder(self, n=None):
        if n is None:
            n = self.root
        for p in self._subtree_preorder(n):
            yield p

    def _subtree_preorder(self, p):
        yield p
        for c in p.childs():
            if c.is_leaf():
                yield c
            else:
                for other in self._subtree_preorder(c):
                    yield other

    def postorder(self, n=None):
        if n is None:
            n = self.root
        for p in self._subtree_postorder(n):
            yield p

    def _subtree_postorder(self, p):
        for c in p.childs():
            if c.is_leaf():
                yield c
            else:
                for other in self._subtree_postorder(c):
                    yield other
        yield p


class GetSamlIdpString(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        tenant = tenant_from_request(request)
        return Response({'result': saml_login_string(tenant)})


class ListMetricsInGroup(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request, group):
        metrics = poem_models.Metrics.objects.\
            filter(groupofmetrics__name__exact=group).\
            values_list('name', flat=True)
        results = sorted(metrics, key=lambda m: m.lower())
        if results or (not results and
                       poem_models.GroupOfMetrics.objects.filter(
                           name__exact=group)):
            return Response({'result': results})
        else:
            raise NotFound(status=404,
                           detail='Group not found')


class ListTokens(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request):
        tokens = api_models.APIKey.objects.all().values_list('client_id', 'token')
        api_format = [dict(name=e[0], token=e[1]) for e in tokens]
        return Response(api_format)


class ListTokenForTenant(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request, name):
        try:
            e = api_models.APIKey.objects.get(client_id=name)

            return Response(e.token)

        except api_models.APIKey.DoesNotExist:
            raise NotFound(status=404,
                           detail='Tenant not found')


class ListUsers(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request, username=None):
        if username:
            try:
                user = poem_models.CustUser.objects.get(username=username)
                serializer = serializers.UsersSerializer(user)
                return Response(serializer.data)

            except poem_models.CustUser.DoesNotExist:
                raise NotFound(status=404,
                            detail='User not found')

        else:
            users = poem_models.CustUser.objects.all()
            serializer = serializers.UsersSerializer(users, many=True)

            return Response(serializer.data)


class ListGroupsForUser(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request, group=None):
        user = request.user

        if user.is_superuser:
            groupsofaggregations = poem_models.GroupOfAggregations.objects.all().values_list('name', flat=True)
            results = {'aggregations': groupsofaggregations}

            groupsofprofiles = poem_models.GroupOfProfiles.objects.all().values_list('name', flat=True)
            results.update({'profiles': groupsofprofiles})

            groupsofprobes = poem_models.GroupOfProbes.objects.all().values_list('name', flat=True)
            results.update({'probes': groupsofprobes})

            groupsofmetrics = poem_models.GroupOfMetrics.objects.all().values_list('name', flat=True)
            results.update({'metrics': groupsofmetrics})

        else:
            groupsofaggregations = user.groupsofaggregations.all().values_list('name', flat=True)
            results = {'aggregations': groupsofaggregations}

            groupsofprofiles = user.groupsofprofiles.all().values_list('name', flat=True)
            results.update({'profiles': groupsofprofiles})

            groupsofprobes = user.groupsofprobes.all().values_list('name', flat=True)
            results.update({'probes': groupsofprobes})

            groupsofmetrics = user.groupsofmetrics.all().values_list('name', flat=True)
            results.update({'metrics': groupsofmetrics})

        if group:
            return Response(results[group.lower()])
        else:
            return Response({'result': results})


class ListAggregations(APIView):
    authentication_classes= (SessionAuthentication,)

    def post(self, request):
        serializer = serializers.AggregationProfileSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            groupaggr = poem_models.GroupOfAggregations.objects.get(name=request.data['groupname'])
            aggr = poem_models.Aggregation.objects.get(apiid=request.data['apiid'])
            groupaggr.aggregations.add(aggr)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        aggr = poem_models.Aggregation.objects.get(apiid=request.data['apiid'])
        aggr.groupname = request.data['groupname']
        aggr.save()

        groupaggr = poem_models.GroupOfAggregations.objects.get(name=request.data['groupname'])
        groupaggr.aggregations.add(aggr)

        return Response(status=status.HTTP_201_CREATED)

    def get(self, request, aggregation_name=None):
        if aggregation_name:
            try:
                aggregation = poem_models.Aggregation.objects.get(name=aggregation_name)
                serializer = serializers.AggregationProfileSerializer(aggregation)
                return Response(serializer.data)

            except poem_models.Aggregation.DoesNotExist:
                raise NotFound(status=404,
                            detail='Aggregation not found')

        else:
            aggregations = poem_models.Aggregation.objects.all()
            serializer = serializers.AggregationProfileSerializer(aggregations, many=True)
            return Response(serializer.data)


class ListProbes(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request, probe_name):
        try:
            probes = poem_models.Probe.objects.get(name=probe_name)
        except poem_models.Probe.DoesNotExist:
            result = dict()
        else:
            result = dict(id=probes.id,
                          name=probes.name,
                          description=probes.description,
                          comment=probes.comment)
        return Response(result)


class ListServices(APIView):
    authentication_classes = (SessionAuthentication,)

    def _is_one_probe_found(self, metrics):
        found_metrics = poem_models.Metric.objects.filter(name__in=metrics)

        for metric in found_metrics:
            if metric.probeversion:
                return True

        return False

    def _get_or_create(self, tree, root, node):
        fn = root.find(node)
        if fn > -1:
            return root.child(fn)
        else:
            return tree.addchild(node, root)

    def _count_leaves(self, tree, root):
        count = 0

        for node in tree.postorder(root):
            if node.is_leaf():
                count += 1

        return count

    def get(self, request):
        servicetype_spmt = dict()
        tree = Tree()
        r = tree.addroot('root')

        for (service_area, service_name, service_type) in \
                poem_models.Service.objects.all().values_list('service_area', 'service_name', 'service_type'):
            metricinstances = poem_models.MetricInstance.objects.filter(service_flavour=service_type)
            unique_metrics = sorted(list(set(m.metric for m in metricinstances)))

            if unique_metrics and self._is_one_probe_found(unique_metrics):
                found_metrics = poem_models.Metric.objects.filter(name__in=unique_metrics)

                sat = self._get_or_create(tree, r, service_area)
                snt = self._get_or_create(tree, sat, service_name)
                stt = self._get_or_create(tree, snt, service_type)

                for metric in found_metrics:
                    if metric.probeversion:
                        mt = tree.addchild(metric.name, stt)
                        tree.addchild(metric.probeversion, mt)

        data = list()
        for sa in r.childs():
            data.append({sa.name(): list(),
                         'rowspan': self._count_leaves(tree, sa)})
            for sn in sa.childs():
                data[-1][sa.name()].append({sn.name(): list(),
                                            'rowspan': self._count_leaves(tree, sn)})
                for st in sn.childs():
                    data[-1][sa.name()][-1][sn.name()].append({st.name(): list(),
                                                               'rowspan': self._count_leaves(tree, st)})
                    for metric in st.childs():
                        data[-1][sa.name()][-1][sn.name()][-1][st.name()].append({metric.name(): metric.childs()[0].name()})
                        # for probe in metric.childs():
                            # data[-1][sa.name()][-1][sn.name()][-1][st.name()][-1][metric.name()].append(probe.name())

        return Response({'tree': data,
                         'rowspan': self._count_leaves(tree, r)})
