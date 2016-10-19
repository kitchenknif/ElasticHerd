# ElasticHerd
Python3 + boto3 scripts to create a beowulf cluster on AWS 

## Usage
1. Create config file with filename for keyfile to access node ("keyfile:/path/to/keyfile.pem")
2. ec2_herd.py contains two main functions: 
    - kill_nodes() to kill cluster
    - create_ec2_nodes(node_count, config)
    
create_ec2_nodes() currently creates $node_count$ ubuntu linux nodes (hardcoded AMI), updates all packages, sets up python3 + numpy + scipy ecosystem and installs & configures MPICH. After that it pulls a couple of packages from github (PyTMM & PyATMM). 
In the end you get a list of running nodes in an MPI cluster and a keyfile to ssh into any one of them.

## Known problems
  - kill_nodes() doesn't always manage to shutdown and delete everything in one run, crashes in some race condition.
  - All time delays are relatively randomly chosen (related to previous problem)
  - Cluster is created on the default VPC - probably not a good idea
  - Creating nodes eats a lot of traffic, because each node is created from scratch
  
## TODO
  - ~~Create 1 node, save it as an AMI for all the other nodes => save traffic, faster deployment~~
  - Create cluster on separate VPC
  - Add support for several clusters running at the same time
  - Clean up hard-coded time delays, figure out what causes kill_nodes() to crash
  - ~~Modular install lists (?)~~
  
## TODO - TaskMaster/Worker Class
  - ~~Email when all tasks finished~~
  
  
