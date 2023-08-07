### Script to generate custom report for CIS Compliance Standards 

1. The list of compliance standards is set in `templates/stds.yaml`

The `rql1` query returns the resources failing the compliance standatd requirement
The `rql2` query returns the total of concerned resources

The results of queries are put in pandas dataframes for merge on a key to represent the join between  
the failed resources and the total giving the total failed, the "pass" are then evaluted as "total - failed"

Parameters `left_on` and `right_on` specify the key on which pandas dataframes are merged

2. The report is generated per account group

Account groups are put in `accgroups.csv`

3. `jinja` template is used to generate the `txt` report `report.j2`

To learn more about Prisma `rql` and how they are used in Compliance Standards 
please refer to [Prisma documentation](https://docs.paloaltonetworks.com/prisma/prisma-cloud/prisma-cloud-admin)
