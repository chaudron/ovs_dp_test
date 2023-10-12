#
# Do the following to build the custom kernel with CONFIG_NF_CONNTRACK_TIMEOUT
# and CONFIG_NF_CT_NETLINK_TIMEOUT enabled.
#

# Install build dependencies:

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
  rpmdevtools


# Get and unpack source tree:

  koji download-build --arch=src kernel-$(uname -r)

  rpmdev-setuptree
  rpm -Uvh kernel-*.src.rpm


# Set specific identifier to kernel package

  sed -i 's/# define buildid .local/%define buildid .ovs/' ~/rpmbuild/SPECS/kernel.spec


# Unpack the actual source code

  rpmbuild -bp ~/rpmbuild/SPECS/kernel.spec


# Make the modifications to the kernel configuration

  KV=$(uname -r | sed -ne 's/\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p')
  BD=~/rpmbuild/BUILD/kernel-$KV/linux-*/

  sed -i 's/# CONFIG_NF_CONNTRACK_TIMEOUT is not set/CONFIG_NF_CONNTRACK_TIMEOUT=y/' $BD/configs/kernel-$KV-x86_64.config
  sed -i 's/CONFIG_NF_CT_NETLINK=m/CONFIG_NF_CT_NETLINK=m\nCONFIG_NF_CT_NETLINK_TIMEOUT=m/' $BD/configs/kernel-$KV-x86_64.config


# Build the new RPMs (in multiple steps, else it will overwrite our changed
# config file).

rpmbuild -bc --short-circuit --with baseonly --without debuginfo --target=$(uname -m) ~/rpmbuild/SPECS/kernel.spec &&
  rpmbuild -bi --short-circuit --with baseonly --without debuginfo --target=$(uname -m) ~/rpmbuild/SPECS/kernel.spec &&
  rpmbuild -bb --short-circuit --with baseonly --without debuginfo --target=$(uname -m) ~/rpmbuild/SPECS/kernel.spec &&
  echo "BUILD_DONE"


# Now copy the kernel files to the vagrant directory

cp ~/rpmbuild/RPMS/x86_64/kernel-5.15.7-200.ovs.fc35.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-core-5.15.7-200.ovs.fc35.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-devel-5.15.7-200.ovs.fc35.x86_64.rpm rpms/
cp ~/rpmbuild/RPMS/x86_64/kernel-modules-5.15.7-200.ovs.fc35.x86_64.rpm rpms/


# Now update the Vagrant file to install the newly created kernel
