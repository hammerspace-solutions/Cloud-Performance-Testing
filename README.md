# Hammerspace Benchmark Setup Guide

This README provides step-by-step instructions for setting up and running performance benchmarks (e.g., IOR, MDTEST, IO500, and FIO) on your Hammerspace deployment in AWS. These benchmarks test the global namespace and filesystem performance across tiers (small, medium, large) on instances provisioned via your Terraform project's modules (e.g., "clients", "storage_servers", "ec groups"). The "ansible" module handles configurations securely using AWS Systems Manager (SSM) for Terraform-to-Ansible communication and SSH for Ansible-to-target setup, ensuring clients can drive NFS v4.2 workflows through the Hammerspace Anvil metadata server.

**Prerequisites**:
- Run these steps in a `/root/benchmark-*` directory on the Ansible controller or a client instance.
- Ensure `../inventory.ini` exists (generated dynamically by Terraform via SSM pushes in the "ansible" module).
- Required tools: Bash, Ansible (for inventory parsing), and access to SSH-configured targets.

## Setup

1. **Directory and Inventory Check**:
   - Ensure you're in a `/root/benchmark-*` directory.
   - Verify `../inventory.ini` is present (used by setup scripts to extract IPs for clients, storage servers, etc., post-SSM/SSH configuration).

2. **Load Ansible**:
   - Make sure that the client running the benchmarks has ansible installed
   - `apt install ansible`

3. **Create AWS Credentials for AWS CLI**:

   If you are running the tests in AWS, one of the shell scripts gets the configuration data from AWS for the clients, storage servers, and Anvil. The script needs a aws configuration file in order to use the aws cli.
   
   - Create a .aws directory in the /root directory
   - `cd .aws`
   - Place the following in a file called `config`. Change the region if you are running somewhere other than us-east-1.

  ```
  [default]
  region = us-east-1
  ```

   - Please the following in a file called `credentials`. You will have to use your own access key and secret access key from IAM.

  ```
  [default]
  aws_access_key_id = AKIA5MBZHLROK512345
  aws_secret_access_key = cQC2Uk+6tPgSA9d77QVFOeGZ95jTKAX312345
  ```

## Running

1. **Run the Script**:
   - `./run-tests.sh <log-name> <storage>`

`log-name` is any descriptive name for your tests.
`storage` can be either `storage` or `ecgroup`

## Tips and Integration
  - **Automation via Ansible**: Push these scripts to the Ansible controller using SSM (e.g., via `ansible_ssm_jobs.tf`), then execute remotely on clients/storage servers over SSH for consisten benchmarking.
  - **Tier-Specific Runs**: Adjust `terraform.tfvars` for instance types/counts (e.g., small: 4 storage servers with RAID-0 EBS), apply changes, then re-run setup for each tier.
  - **Monitoring**: Use AWS CloudWatch to track metrics during tests (e.g., network throughput on Graviton storage instances).
  - **Error Handling**: if inventory parsing fails, verify SSM-pushed inventory.ini in the 'ansible' module.

For issues, check Ansible logs or Terraform outputs for IPs/SSM associatons. This setup ensures reliable performance testing of Hammerspace in your module AWS environment.
