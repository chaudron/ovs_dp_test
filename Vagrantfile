#
# NOTE: This script requeres the reload pluging, install it as follows:
#         vagrant plugin install vagrant-reload
#
#       It also need sshfs:
#         vagrant plugin install vagrant-sshfs
#

VAGRANTFILE_API_VERSION = "2"

VM_TYPE = ENV["VM_TYPE"] || "fedora"
VM_CPUS = ENV["VM_CPUS"] || 4
VM_NAME = ENV["VM_NAME"] || VM_TYPE

$provision_fedora = <<END
  dnf -y update
  dnf -y install \
    autoconf \
    automake \
    clang \
    dpdk \
    gcc \
    git \
    iproute-tc \
    lftp \
    libatomic \
    libbpf-devel \
    libpcap-devel \
    libcap-ng \
    libcap-ng-devel \
    libreswan \
    libtool \
    libibverbs-devel \
    libxdp \
    libxdp-devel \
    meson \
    ninja-build \
    nmap-ncat \
    numactl-devel \
    openssl \
    openssl-devel \
    python3-netaddr \
    python3-pyelftools \
    python3-pytest \
    python3-flake8 \
    python3-pip \
    python3-scapy \
    python3-sphinx \
    python3-tftpy \
    tcpdump \
    unbound-devel

  pip install \
     pyftpdlib

  sysctl net.ipv6.conf.all.disable_ipv6=0
  sysctl vm.nr_hugepages=1024

  sed -i 's/net.ipv6.conf.all.disable_ipv6 = 1/net.ipv6.conf.all.disable_ipv6 = 0/g' /etc/sysctl.conf
  echo 'vm.nr_hugepages = 1024' >> /etc/sysctl.conf

  systemctl disable firewalld
  systemctl stop firewalld

  mkdir -p /vagrant/results/$RESULT_DIR

  rpm -U --replacepkgs --nodeps --oldpackage /vagrant/rpms/*.rpm
END

$provision_ubuntu = <<END
  apt install -y \
    automake \
    bc \
    clang \
    dpdk-dev \
    ethtool \
    gcc \
    git \
    init \
    iproute2 \
    iputils-arping \
    iputils-ping \
    isc-dhcp-server \
    kmod \
    lftp \
    libbpf-dev \
    libcap-ng-dev \
    libelf-dev \
    libjemalloc-dev \
    libjemalloc2 \
    libnuma-dev \
    libpcap-dev \
    libreswan \
    libssl-dev \
    libtool \
    libunbound-dev \
    libunwind-dev \
    llvm-dev \
    ncat \
    net-tools \
    ninja-build \
    python3-dev \
    python3-pip \
    selinux-policy-dev \
    sudo \
    systemtap-sdt-dev \
    tcpdump \
    wget

  pip3 install --disable-pip-version-check --user wheel
  pip3 install --disable-pip-version-check --user \
    'hacking>=3.0' 'meson==0.53.2' \
    flake8 netaddr netaddr pyelftools pyftpdlib \
    pyparsing pytest scapy setuptools sphinx tftpy

  sysctl -q -w net.ipv6.conf.all.forwarding=1
  sysctl -q -w net.ipv6.conf.all.disable_ipv6=0

  sed -i 's/net.ipv6.conf.all.disable_ipv6 = 1/net.ipv6.conf.all.disable_ipv6 = 0/' /etc/sysctl.conf
  sed -i 's/#net.ipv6.conf.all.forwarding=1/net.ipv6.conf.all.forwarding=1/' /etc/sysctl.conf

  echo "export PATH=\$PATH:\$HOME/.local/bin" > $HOME/.bashrc

  mkdir -p /vagrant/results/$RESULT_DIR
END

$build_dpdk = <<END
  export DPDK_BUILD=~/dpdk_build/
  rm -rf $DPDK_BUILD
  mkdir -p $DPDK_BUILD
  cd /vagrant/dpdk
  CC=gcc meson -Dtests=false -Dmachine=default \
    -Denable_drivers=net/null,net/tap,net/virtio,net/pcap,net/af_xdp \
    -Ddeveloper_mode=disabled --prefix="$DPDK_BUILD/install" "$DPDK_BUILD" \
    2>&1 | tee BUIKD_dpdk_meson

  set -o pipefail
  ninja -C "$DPDK_BUILD" install 2>&1 | tee BUILD_ninja_dpdk
END

$build_ovs = <<END
  export DPDK_BUILD=~/dpdk_build/
  cd /vagrant/ovs
  ./boot.sh
  [ -f Makefile ] && ./configure && make distclean
  rm -rf ~/ovs_build
  mkdir -p ~/ovs_build
  cd ~/ovs_build
  PKG_CONFIG_PATH=$DPDK_BUILD/install/lib64/pkgconfig:$DPDK_BUILD/install/lib/x86_64-linux-gnu/pkgconfig \
  CFLAGS="-g -O2 -msse4.2 -mpopcnt $EXTRA_CFLAGS" \
    /vagrant/ovs/configure \
      --enable-afxdp \
      --enable-Werror \
      --enable-usdt-probes \
      --localstatedir=/var \
      --prefix=/usr \
      --sysconfdir=/etc \
      --with-dpdk=static \
        | tee BUILD_ovs_configure.log

  set -o pipefail
  make -j $(nproc) | tee BUILD_ovs_make.log
END

$test_check = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  # No RECHECK as it overrides the previous log.
  make check
  cp tests/testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_kernel = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  make check-kernel
  cp tests/system-kmod-testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_offloads = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  make check-offloads
  cp tests/system-offloads-testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_ovsdb_cluster = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  make check-ovsdb-cluster
  cp tests/ovsdb-cluster-testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_system_tso = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  make check-system-tso
  cp tests/system-tso-testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_system_userspace = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  make check-system-userspace
  cp tests/system-userspace-testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_dpdk = <<END
  echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
  sed -i 's|other_config:dpdk-extra=--log-level=pmd.*:error\]|other_config:dpdk-extra="--log-level=pmd.*:error --block=0000:00:05.0"\]|g' /vagrant/ovs/tests/system-dpdk-macros.at

  # Supress CryptographyDeprecationWarning warning from scapy in MFEX Configuration test.
  export PYTHONWARNINGS='ignore'

  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'
  make check-dpdk
  cp tests/system-dpdk-testsuite.log /vagrant/results/$RESULT_DIR
END

$test_check_afxdp = <<END
  cd ~/ovs_build
  export ASAN_OPTIONS='detect_leaks=1:abort_on_error=true:log_path=asan'  
  make check-afxdp
  cp tests/system-afxdp-testsuite.log /vagrant/results/$RESULT_DIR
END

$get_full_test_dir = <<END
  tar -cvzf /vagrant/results/$RESULT_DIR/full_test_results.tgz ~/ovs_build/tests/*
END

#
# Actual Vagrant configuration
#
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  #
  # Provider specific configuration
  #
  config.vm.provider :libvirt do |libvirt|
    libvirt.cpus = VM_CPUS
    libvirt.memory = 4096

    # ARM specific additions
    libvirt.cpu_mode = "host-passthrough"
    libvirt.machine_arch = "aarch64"
    libvirt.machine_type = "virt"
    libvirt.loader = "/usr/share/AAVMF/AAVMF_CODE.fd"
    libvirt.nvram = ""

    libvirt.input :type => "mouse", :bus => "usb"
    libvirt.input :type => "keyboard", :bus => "usb"
    libvirt.usb_controller :model => "qemu-xhci"
  end

  config.vm.provider "virtualbox" do |vb|
    vb.memory = 4096
    vb.cpus = VM_CPUS
  end

  config.vm.synced_folder "./dpdk", "/vagrant/dpdk", type: "sshfs"
  config.vm.synced_folder "./ovs", "/vagrant/ovs", type: "sshfs"
  config.vm.synced_folder "./results", "/vagrant/results", type: "sshfs"
  config.vm.synced_folder "./rpms", "/vagrant/rpms", type: "sshfs", mount_options: ["ro"]

  #
  # Virtual Machine specific configuration
  #
  config.vm.define VM_NAME do |ovs_vm|
    ovs_vm.vm.hostname = VM_NAME

    if VM_TYPE == "ubuntu"
      ovs_vm.vm.box = "generic/ubuntu2204"
      ovs_vm.vm.provision "Linux Provisioning", type: "shell", inline: $provision_ubuntu, env: {"RESULT_DIR" => VM_NAME}
    else
      ovs_vm.vm.box = "generic-a64/fedora39"
      ovs_vm.vm.provision "Linux Provisioning", type: "shell", inline: $provision_fedora, env: {"RESULT_DIR" => VM_NAME}
    end

    ovs_vm.vm.provision "Build dpdk", type: "shell", inline: $build_dpdk
    ovs_vm.vm.provision "Build Open vSwitch", type: "shell", inline: $build_ovs, env: {"EXTRA_CFLAGS" => ENV['EXTRA_CFLAGS'], "CC" => ENV['CC']}
    ovs_vm.vm.provision "Reboot new kernel", type: "reload"
    ovs_vm.vm.provision "Test: check", type: "shell", inline: $test_check, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-kernel", type: "shell", inline: $test_check_kernel, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-offloads", type: "shell", inline: $test_check_offloads, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-ovsdb-cluster", type: "shell", inline: $test_check_ovsdb_cluster, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-system-tso", type: "shell", inline: $test_check_system_tso, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-system-userspace", type: "shell", inline: $test_check_system_userspace, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-dpdk", type: "shell", inline: $test_check_dpdk, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Test: check-afxdp", type: "shell", inline: $test_check_afxdp, env: {"TESTSUITEFLAGS" => ENV['TESTSUITEFLAGS'], "RESULT_DIR" => VM_NAME}
    ovs_vm.vm.provision "Get test directory", type: "shell", inline: $get_full_test_dir, env: {"RESULT_DIR" => VM_NAME}
  end
end
