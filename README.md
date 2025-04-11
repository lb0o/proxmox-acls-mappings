# Proxmox ACL Setup for Cozystack

cozystack-proxmox - Ansible playbook for setting up Proxmox VE access control
- Create ACLs, users, roles, and API tokens for Cozystack integration
- Generate an encrypted resource file with user credentials and permissions
- Allow to auto-map the GPU resources to the VMs to allow GPU passthrough easily

# Secrets

Create a secure password and store it somewhere safe:
```bash
head -c48 /dev/urandom | base64 > ~/.yourvaultmasterpasswordfile
```
Copy the example secrets file to the appropriate location:
```bash
cp ansible/envs/.host_vars/.thepvesecrets.yml.example ansible/envs/.host_vars/.thepvesecrets.yml
```

Encrypt the secrets file before editing:
```bash
ansible-vault encrypt --vault-password-file ~/.yourvaultmasterpasswordfile ansible/envs/.host_vars/.thepvesecrets.yml
```

Usefull ansible-vault commands:
```bash
ansible-vault encrypt
ansible-vault decrypt
ansible-vault edit
ansible-vault view 
```

# usage

```bash
ansible-playbook ansible/playbooks/proxmox_acl_setup.yml --vault-password-file ~/.yourvaultmasterpasswordfile
```

```bash
ansible-playbook ansible/playbooks/proxmox_gpu_mapping.yml --vault-password-file ~/.yourvaultmasterpasswordfile
```

you can erase any created resources by running the playbook with the `-e` option:
```bash
ansible-playbook ansible/playbooks/proxmox_acl_setup.yml --vault-password-file ~/.yourvaultmasterpasswordfile -e "reset=true" 
```


License
----
Apache 2.0