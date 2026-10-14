# Automation

Shell scripts under `scripts/` are the operational interface for slice 001.

Ansible is not required and is not installed by this slice. A later playbook can call the same start, seed, and verify steps. That would be another way to operate this composition, not another temperature application.

Terraform is not an interface for this local proof. AWS composition stays in `01_Terraform`.
