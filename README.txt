Hammerspace Benchmark Setup Guide

This README provides step-by-step instructions for setting up and running performance benchmarks (e.g., IOR, MDTEST, IO500, and FIO) on your Hammerspace deployment in AWS. These benchmarks test the global namespace and filesystem performance across tiers (small, medium, large) on instances provisioned via your Terraform project's modules (e.g., "clients", "storage_servers", "ec groups"). The "ansible" module handles configurations securely using AWS Systems Manager (SSM) for Terraform-to-Ansible communication and SSH for Ansible-to-target setup, ensuring clients can drive NFS v4.2 workflows through the Hammerspace Anvil metadata server.

Prerequisites:

- Run these steps in a /root/benchmark-* directory on the Ansible controller or a client instance.

- Ensure ../inventory.ini exists (generated dynamically by Terraform via SSM pushes in the "ansible" module).

- Required tools: Bash, Ansible (for inventory parsing), and access to SSH-configured targets.

Initial Setup

0. Directory and Inventory Check:
   - Ensure you're in a /root/benchmark-* directory.
   - Verify ../inventory.ini is present (used by setup scripts to extract IPs for clients, storage servers, etc., post-SSM/SSH configuration).

1. Run Setup Script:
   - Execute ./setup.sh <test_name> <type> (where <type> is "storage" or "ecgroup").
   - This creates a config file, installs dependencies (e.g., OpenMPI, PDSH), mounts NFS shares via the Anvil, and prepares benchmarks on clients.

Measure Bandwidth with IOR

1. Edit Script:
   - Open ior-Bandwidth-scale-v4.sh and adjust parameters:
     STONE=300  # Stonewall timer in seconds (stops test after 5 minutes if running long)
     LOGD=logs-Cloud-Scale-Bandwidth  # Local folder for high-level logs
     C=4  # Number of clients to test with (defaults to 1 or total from config; update hosts dir for more)
     for s in 20482 40964000; do  # Total data to write in MBs (20GB for page cache fit; ~400TB for stonewalled runs)
     for i in 2 4 8 16; do  # Threads per client (increase until bandwidth peaks; base on max threads per volume)

2. Run the Script:
   - Execute ./ior-Bandwidth-scale-v4.sh.
   - This measures bandwidth on clients driving storage servers over NFS v4.2.

Measure IOPs with IOR

1. Edit and Run Script:
   - Edit ior-IOPs-scale-v4.sh as needed (similar parameters to bandwidth script).
   - Execute ./ior-IOPs-scale-v4.sh.
   - Focuses on IOPS performance across your configured EC groups or storage tiers.

Run FIO

1. Edit Script:
   - Open cloud_data_path_tests.sh and adjust:
     BW_FILE_COUNT='8'  # Files per client (set to match client CPU cores for optimal load)

2. Run the Script:
   - Execute ./cloud_data_path_tests.sh.
   - Tests data path performance on SSH-configured clients interacting with storage servers.

Collect All Logs

1. Run Log Capture:
   - Execute ./capture-logs.sh.
   - This generates a tarball with all JSON results and logs—save it for analysis (e.g., compare across tiers post-SSM/Ansible deployments).

Tips and Integration

- Automation via Ansible: Push these scripts to the Ansible controller using SSM (e.g., via ansible_ssm_jobs.tf), then execute remotely on clients/storage servers over SSH for consistent benchmarking.

- Tier-Specific Runs: Adjust terraform.tfvars for instance types/counts (e.g., small: 4 storage servers with RAID 0 EBS), apply changes, then re-run setup for each tier.

- Monitoring: Use AWS CloudWatch to track metrics during tests (e.g., network throughput on Graviton storage instances).

- Error Handling: If inventory parsing fails, verify SSM-pushed inventory.ini in the "ansible" module.

For issues, check Ansible logs or Terraform outputs for IPs/SSM associations. This setup ensures reliable performance testing of Hammerspace in your modular AWS environment.
