# Proxmox ACL Setup for Cozystack

cozystack-proxmox - Ansible playbook for setting up Proxmox VE access control
- Create ACLs, users, roles, and API tokens for Cozystack integration
- Generate an encrypted resource file with user credentials and permissions
- Allow to auto-map the GPU resources to the VMs to allow GPU passthrough easily

# secrets
<!-- Create a password with -->
## Generate the token and store in user's home directory
 head -c48 /dev/urandom | base64 > ~/.yourvaultmasterpasswordfile

## Copy the example file
 cp ansible/envs/.host_vars/.thepvesecrets.yml.example ansible/envs/.host_vars/.thepvesecrets.yml

## Edit the file with ansible-vault (encrypt prior to editing)
 ansible-vault encrypt --vault-password-file ~/.yourvaultmasterpasswordfile ansible/envs/.host_vars/.thepvesecrets.yml
 ansible-vault edit --vault-password-file ~/.yourvaultmasterpasswordfile ansible/envs/.host_vars/.thepvesecrets.yml

# USAGE

```bash
ansible-playbook ansible/playbooks/proxmox_acl_setup.yml --vault-password-file ~/.yourvaultmasterpasswordfile
```

```bash
ansible-playbook ansible/playbooks/proxmox_gpu_mapping.yml --vault-password-file ~/.yourvaultmasterpasswordfile
```

License
----
Apache 2.0