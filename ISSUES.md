# Known Issues

## IPsec tests skipped on ARM64 (aarch64)

All IPsec/Libreswan tests are skipped on ARM64 because running them crashes
the ARM kernel. To prevent this, `libreswan` is not installed in the Fedora
VM when provisioning on `aarch64` (see `Vagrantfile`).
