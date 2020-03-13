#Metrics
Metrics page is accessible through menu on the left side. It is shown in the image below.

![Tenant Metrics](tenant_figs/metrics.png)

Metrics can be filtered by name, probe, group and type (active or passive). Any particular metric can be accessed by clicking its name. Also one may see probes associated to metrics by clicking probe's name.

Particular metric's page is shown in the image below.

![Tenant Metric Detail](tenant_figs/metrics_details.png)

Most of the fields is disabled. Tenant users are only allowed to modify four of the configuration values, group and probe version. User may only choose among groups that are associated to him. Exception to this rule is user with superuser permission, (s)he can pick any existing group. In case of probes, users can only choose among versions of the same probe in a drop down menu. Metric configuration is then going to automatically be updated, if necessary.

By clicking **History** button, user can see all the changes made to the metric.

In case user has no permission to modify the probe, there is going to appear a warning message on top of page, as shown in image below.

![Tenant Metric Readonly](tenant_figs/metric_readonly.png)

##Adding new metrics
Tenant users cannot add new metrics by themselves. Metrics can be imported from available metric templates by superuser on [Metric Template Page](tenant_metric_templates.md). If none of the metric templates is satisfying, the user will have to ask a super admin to add new metric template to SuperAdmin POEM.