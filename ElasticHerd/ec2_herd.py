import boto3
import paramiko
import time
import configparser

import node_setup

def kill_nodes():
    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')

    efs = boto3.client('efs')

    #
    # Instances
    #

    print("Killing instances...")

    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'pending']}])
    if instances is not None:
        for instance in instances:
            for tag in instance.tags:
                if tag["Key"] == "Name" and tag["Value"] == "elasticHerdInstance":
                    print("Killing instance {}".format(instance.id))
                    ec2_client.terminate_instances(InstanceIds=[instance.id])

                    still_there = True
                    while still_there:
                        still_there = False
                        instance = ec2.Instance(instance.id)
                        if not instance.state["Name"] == "terminated":
                            time.sleep(5)

                    time.sleep(5)
                    break

    #
    # File system share
    #

    print("Killing shared file system...")

    shares = efs.describe_file_systems()["FileSystems"]

    share = None

    for s in shares:
        if s["CreationToken"] == "elasticHerdShare":
            share = s

    if share is not None:
        mount_targets = efs.describe_mount_targets(
                                                    FileSystemId=share["FileSystemId"],
                                                )["MountTargets"]
        for mt in mount_targets:
            print("Killing EFS share's mount target {}".format(mt["MountTargetId"]))
            efs.delete_mount_target(MountTargetId=mt["MountTargetId"])

        mount_targets = efs.describe_mount_targets(
                                                    FileSystemId=share["FileSystemId"],
                                                )["MountTargets"]
        still_there = True
        while still_there:
            still_there = False
            for mt in mount_targets:
                if not mt["LifeCycleState"] == "deleted":
                    time.sleep(5)
                    still_there = True
            mount_targets = efs.describe_mount_targets(
                                                    FileSystemId=share["FileSystemId"],
                                                )["MountTargets"]

        print("Killing EFS share {}".format(share["FileSystemId"]))
        efs.delete_file_system(FileSystemId=share["FileSystemId"])
        still_there = True

        while still_there:
            still_there = False
            time.sleep(5)
            shares = efs.describe_file_systems()["FileSystems"]
            for s in shares:
                if s["CreationToken"] == "elasticHerdShare" and not s['LifeCycleState'] == "deleted":
                    still_there = True


    time.sleep(5)

    #
    # Security groups
    #

    print("Deleting Security groups...")

    groups = ec2.security_groups.filter()
    for group in groups:
        if group.group_name == "elasticHerdInternal" or group.group_name == "elasticHerdExternal":
            time.sleep(5)
            print("Killing Security Group {}".format(group.id))
            group.delete()

    #
    # Key pair
    #

    print("Deleting key pair...")

    key_pair = ec2_client.describe_key_pairs()["KeyPairs"]
    for k in key_pair:
        if k['KeyName'] == "elasticHerd":
            print("killing key pair \"{}\"".format(k["KeyName"]))
            ec2_client.delete_key_pair(
                                        KeyName=k["KeyName"]
                                        )


def create_ec2_nodes(node_count=3, config_file="./elastic_config.cfg"):
    config = configparser.ConfigParser()
    config.read(config_file)
    keyfile = config['elasticherd']['keyfile']

    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')

    efs = boto3.client('efs')

    #
    # Create security groups
    #

    print("Creating security groups...")
    internal_group = ec2.create_security_group(GroupName="elasticHerdInternal", Description='Security group for EFS share and MPI communication')
    ec2_client.authorize_security_group_ingress(GroupId = internal_group.id,
                                         IpPermissions = [
                                             {
                                                 'IpProtocol': '-1',
                                                 'FromPort': -1,
                                                 'ToPort': -1,
                                                 'UserIdGroupPairs': [
                                                     {
                                                         'GroupId':internal_group.id
                                                     }
                                                     ]
                                             }
                                         ]
                                         )

    external_group = ec2.create_security_group(GroupName="elasticHerdExternal", Description='Security group for Masetr node')
    ec2_client.authorize_security_group_ingress(GroupId = external_group.id,
                                         IpPermissions = [
                                             {
                                                 'IpProtocol': 'tcp',
                                                 'FromPort': 22,
                                                 'ToPort': 22,
                                                 'IpRanges': [
                                                    {
                                                        'CidrIp': '0.0.0.0/0'
                                                    },
                                                 ],
                                             }
                                         ]
                                         )

    #
    # File system share
    #

    print("Creating file system share...")
    efs_share = efs.create_file_system(
                                        CreationToken='elasticHerdShare',
                                        PerformanceMode='generalPurpose'
                                        )

    efs.create_tags(
                        FileSystemId=efs_share["FileSystemId"],
                        Tags=[
                                {
                                    'Key': 'Name',
                                    'Value': 'elasticeHerdShare'
                                },
                             ]
                      )
    time.sleep(5)

    # TODO: Should create its own in the future
    # TODO: Should not use hardcoded random subnet...
    vpc = ec2_client.describe_vpcs()["Vpcs"][0]

    subnet = ec2_client.describe_subnets()["Subnets"][0]
    mount_target = efs.create_mount_target(
                                                FileSystemId=efs_share["FileSystemId"],
                                                SubnetId=subnet["SubnetId"],
                                                SecurityGroups=[
                                                                    internal_group.id,
                                                                ]
                                            )
    setting_up = True
    while setting_up:
        setting_up = False
        mt = efs.describe_mount_targets(
                                        MountTargetId=mount_target["MountTargetId"]
                                        )
        if not mt["MountTargets"][0]["LifeCycleState"] == "available":
            setting_up = True
            time.sleep(10)
    #
    # Key pair
    #

    print("Creating key pair...")
    key_pair = ec2_client.create_key_pair(
                                    KeyName='elasticHerd'
                                    )
    with open(keyfile, "w") as f:
        f.write(key_pair["KeyMaterial"])
    #
    # Instances
    #

    print("Creating instances...")
    nodes = ec2.create_instances(
                                    ImageId='ami-ed82e39e',
                                    MinCount=node_count,
                                    MaxCount=node_count,
                                    KeyName='elasticHerd',
                                    SecurityGroupIds=[
                                        internal_group.id,
                                        external_group.id
                                    ],
                                    InstanceType='t2.micro',
                                    Monitoring={
                                        'Enabled': True
                                    },
                                    SubnetId=subnet["SubnetId"],
                                )


    ec2.create_tags(
                        Resources=[node.id for node in nodes],
                        Tags=[
                                {
                                    'Key': 'Name',
                                    'Value': 'elasticHerdInstance'
                                },
                             ]
                      )

    #
    # Configure Instances
    #
    print("Configuring instances...")
    for node in nodes:
        n = ec2.Instance(node.id)
        while not n.state["Name"] == "running":
            time.sleep(5)
            n = ec2.Instance(node.id)

        time.sleep(30)
        print("Configuring instance {}".format(node.id))
        print("Public DNS - {}".format(n.public_dns_name))
        node_setup.install_mpi_ecosystem_keyfile(n.public_dns_name, "ubuntu", keyfile)
        node_setup.mount_efs_share(n.public_dns_name, "ubuntu", keyfile,
                                   "$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone).{}.efs.{}.amazonaws.com".format(efs_share["FileSystemId"],"eu-west-1"))


    n = ec2.Instance(nodes[0].id)
    while not n.state["Name"] == "running":
        time.sleep(5)
        n = ec2.Instance(nodes[0].id)

    time.sleep(1)
    print("Creating SSH RSA key on node {}".format(nodes[0].id))
    node_setup.create_mpi_key(n.public_dns_name, "ubuntu", keyfile)

    node_setup.create_mpi_hosts_file(n.public_dns_name, "ubuntu", keyfile, [ec2.Instance(host.id).public_dns_name for host in nodes])
    node_setup.create_known_hosts_file(n.public_dns_name, "ubuntu", keyfile, [ec2.Instance(host.id).public_dns_name for host in nodes])
    node_setup.pull_code_to_mpi_share(n.public_dns_name, "ubuntu", keyfile)


    for node in nodes[1:]:
        n = ec2.Instance(node.id)
        while not n.state["Name"] == "running":
            time.sleep(5)
            n = ec2.Instance(node.id)

        time.sleep(10)
        print("Getting SSH RSA key from share on node {}".format(node.id))
        node_setup.get_mpi_key_from_share(n.public_dns_name, "ubuntu", keyfile)


    #
    # Return MPI Master Node
    #
    print("Master node public DNS:")
    print(ec2.Instance(nodes[0].id).public_dns_name)
    with open("./nodes.txt", "w") as f:
        for node in nodes:
            f.write("{}\n".format(ec2.Instance(node.id).public_dns_name))

    # instances = ec2.instances.filter(
    #     Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    # for instance in instances:
    #     print(instance.id, instance.instance_type)


if __name__ == "__main__":
    #kill_nodes()
    create_ec2_nodes(node_count=10)