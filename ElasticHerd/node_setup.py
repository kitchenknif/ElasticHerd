import paramiko

def print_stdout(stdout):
    for l in stdout.readlines():
        print(l)

def install_mpi_ecosystem_keyfile(hostname, user, keyfile):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    install_mpi_ecosystem(hostname, user, rsa_key)

def install_mpi_ecosystem(hostname, user, rsa_key):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    print("Connecting...")
    ssh.connect(hostname, username=user, pkey=rsa_key)
    print("Connected.")
    #
    # Bring system up-to-date
    #
    print("Updating database...")
    stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq update")
    print_stdout(stdout)
    print_stdout(stderr)
    print("Upgrading software...")
    stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq --yes --force-yes upgrade")
    print_stdout(stdout)
    print_stdout(stderr)

    #
    # Setup Python 3 ecosystem
    #
    install_list = [
                    "build-essential",
                    "nfs-common",
                    "git",
                    "python3",
                    "python3-pip",
                    "python3-numpy",
                    "python3-scipy",
                    "python3-matplotlib",
                    "python3-dev",
                    "python3-pandas",
                    "python3-nose"
                    ]
    for i in install_list:
        print(i)
        stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq --yes --force-yes install {}".format(i))
        print_stdout(stdout)
        print_stdout(stderr)

    #
    # Setup MPICH2
    #
    install_list = [
                    "mpich2"
                    ]
    for i in install_list:
        print(i)
        stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq --yes --force-yes install {}".format(i))
        print_stdout(stdout)
        print_stdout(stderr)


    #
    # Setup Python 3 ecosystem - Pip
    #
    install_list = [
                    "sympy",
                    "mpi4py"
                    ]
    for i in install_list:
        print(i)
        stdin, stdout, stderr = ssh.exec_command("yes | sudo pip3 -q install {}".format(i))
        print_stdout(stdout)
        print_stdout(stderr)


    #
    # Additional stuff from Github - TODO
    #
    install_list = [
                    "https://github.com/kitchenknif/PyTMM.git",
                    "https://github.com/kitchenknif/PyATMM.git"
                    ]
    for i in install_list:
        print(i)
        stdin, stdout, stderr = ssh.exec_command("git clone {}".format(i))
        print_stdout(stdout)
        print_stdout(stderr)
        stdin, stdout, stderr = ssh.exec_command("cd {} && sudo python3 setup.py --quiet install".format(i.split('/')[-1].split('.')[0]))
        print_stdout(stdout)
        print_stdout(stderr)


def mount_efs_share(hostname, user, keyfile, efs_dns):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    ssh.connect(hostname, username=user, pkey=rsa_key)

    stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("mkdir /home/ubuntu/mpishare")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("sudo mount -t nfs4 -o nfsvers=4.1 {}:/ /home/ubuntu/mpishare".format(efs_dns))
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("sudo chown {} /home/ubuntu/mpishare".format(user))
    print_stdout(stdout)
    print_stdout(stderr)


def create_mpi_key(hostname, user, keyfile):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    ssh.connect(hostname, username=user, pkey=rsa_key)

    stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/.ssh && ssh-keygen -b 2048 -t rsa -f id_rsa -q -N \"\"")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/.ssh && cat id_rsa.pub >> authorized_keys")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("cp /home/ubuntu/.ssh/id_rsa /home/ubuntu/mpishare")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("cp /home/ubuntu/.ssh/id_rsa.pub /home/ubuntu/mpishare")
    print_stdout(stdout)
    print_stdout(stderr)


def get_mpi_key_from_share(hostname, user, keyfile):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    ssh.connect(hostname, username=user, pkey=rsa_key)

    stdin, stdout, stderr = ssh.exec_command("cp /home/ubuntu/mpishare/id_rsa /home/ubuntu/.ssh")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("cp /home/ubuntu/mpishare/id_rsa.pub /home/ubuntu/.ssh")
    print_stdout(stdout)
    print_stdout(stderr)
    stdin, stdout, stderr = ssh.exec_command("cat /home/ubuntu/.ssh/id_rsa.pub >> /home/ubuntu/.ssh/authorized_keys")
    print_stdout(stdout)
    print_stdout(stderr)


def create_mpi_hosts_file(hostname, user, keyfile, hosts):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    ssh.connect(hostname, username=user, pkey=rsa_key)

    stdin, stdout, stderr = ssh.exec_command("touch /home/ubuntu/mpishare/mpihosts")
    print_stdout(stdout)
    print_stdout(stderr)
    for host in hosts:
        stdin, stdout, stderr = ssh.exec_command("echo \"{}\"  >> /home/ubuntu/mpishare/mpihosts".format(host))
        print_stdout(stdout)
        print_stdout(stderr)


def create_known_hosts_file(hostname, user, keyfile, hosts):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    ssh.connect(hostname, username=user, pkey=rsa_key)

    stdin, stdout, stderr = ssh.exec_command("touch /home/ubuntu/.ssh/known_hosts")
    print_stdout(stdout)
    print_stdout(stderr)
    for host in hosts:
        stdin, stdout, stderr = ssh.exec_command("ssh-keyscan -H {} >> /home/ubuntu/.ssh/known_hosts".format(host))
        print_stdout(stdout)
        print_stdout(stderr)


def install_nfs(hostname, user, keyfile):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    print("Connecting...")
    ssh.connect(hostname, username=user, pkey=rsa_key)
    print("Connected.")
    print("Updating database...")
    stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq update")
    print_stdout(stdout)
    print_stdout(stderr)
    print("Upgrading software...")
    stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq --yes --force-yes upgrade")
    print_stdout(stdout)
    print_stdout(stderr)

    install_list = [
                    "nfs-common",
                    ]
    install_string = ""
    for i in install_list:
        print(install_string)
        stdin, stdout, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive apt-get -qq --yes --force-yes install {}".format(i))
        print_stdout(stdout)
        print_stdout(stderr)


def pull_code_to_mpi_share(hostname, user, keyfile):
    rsa_key = paramiko.RSAKey.from_private_key_file(keyfile)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                    )
    print("Connecting...")
    ssh.connect(hostname, username=user, pkey=rsa_key)
    print("Connected.")
    #
    # Pull stuff to share
    #
    install_list = [
                    "https://github.com/polyanskiy/refractiveindex.info-database.git",
                    ]
    for i in install_list:
        print(i)
        stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/mpishare && git clone {}".format(i))
        print_stdout(stdout)
        print_stdout(stderr)

# if __name__ == "__main__":
#
#     keyfile = "key.pem"
#     hostname = "public-dns"
#     user = "ubuntu"
#
#     install_mpi_ecosystem_keyfile(hostname, user, keyfile)