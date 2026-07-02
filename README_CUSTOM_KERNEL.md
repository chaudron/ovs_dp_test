# Building a Custom Kernel

> **Note:** This is no longer needed for Fedora 44, as `CONFIG_NF_CONNTRACK_TIMEOUT`
> and `CONFIG_NF_CT_NETLINK_TIMEOUT` are included by default. Kept here for
> reference in case future kernel revisions drop these options.

The following steps build a custom kernel with `CONFIG_NF_CONNTRACK_TIMEOUT`
and `CONFIG_NF_CT_NETLINK_TIMEOUT` enabled.

## Install Build Dependencies

```bash
dnf install -y \
  bc \
  bpftool \
  dwarves \
  elfutils-devel \
  fedora-packager \
  fedpkg \
  gcc-plugin-devel \
  glibc-static \
  grubby \
  ncurses-devel \
  perl-generators \
  pesign \
  rpmdevtools \
  rustfmt
```

## Get and Unpack the Source Tree

```bash
koji download-build --arch=src kernel-$(uname -r)

rpmdev-setuptree
rpm -Uvh kernel-*.src.rpm
```

## Set a Specific Kernel Package Identifier

```bash
sed -i 's/# define buildid .local/%define buildid .ovs/' ~/rpmbuild/SPECS/kernel.spec
```

## Install Build Dependencies

```bash
dnf builddep ~/rpmbuild/SPECS/kernel.spec
```

## Unpack the Actual Source Code

```bash
rpmbuild -bp ~/rpmbuild/SPECS/kernel.spec
```

## Modify the Kernel Configuration

```bash
KV=$(uname -r | sed -ne 's/\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p')
BD=~/rpmbuild/BUILD/kernel-$KV-build/kernel-$KV/linux-*/

sed -i 's/# CONFIG_NF_CONNTRACK_TIMEOUT is not set/CONFIG_NF_CONNTRACK_TIMEOUT=y/' \
  $BD/configs/kernel-$KV-$(uname -m).config

sed -i 's/CONFIG_NF_CT_NETLINK=m/CONFIG_NF_CT_NETLINK=m\nCONFIG_NF_CT_NETLINK_TIMEOUT=m/' \
  $BD/configs/kernel-$KV-$(uname -m).config
```

## Build the New RPMs

Build in multiple steps to avoid overwriting the changed config file:

```bash
rpmbuild -bc --short-circuit --with baseonly --without debuginfo --target=$(uname -m) ~/rpmbuild/SPECS/kernel.spec && \
  rpmbuild -bi --short-circuit --with baseonly --without debuginfo --target=$(uname -m) ~/rpmbuild/SPECS/kernel.spec && \
  rpmbuild -bb --short-circuit --with baseonly --without debuginfo --target=$(uname -m) ~/rpmbuild/SPECS/kernel.spec && \
  echo "BUILD_DONE"
```

## Copy the Kernel RPMs to the Vagrant Directory

```bash
cp ~/rpmbuild/RPMS/x86_64/kernel-6.12.13-200.ovs.fc41.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-core-6.12.13-200.ovs.fc41.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-devel-6.12.13-200.ovs.fc41.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-modules-6.12.13-200.ovs.fc41.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-modules-core-6.12.13-200.ovs.fc41.x86_64.rpm rpms/
```

## Update the Vagrantfile

Update the Vagrantfile to install the newly created kernel by placing the RPM
files in the `rpms/` directory; the provisioning script will automatically
install any `*.$(uname -m).rpm` files found there.
