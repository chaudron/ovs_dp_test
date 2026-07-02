# Known Issues

## check

- Due to an issue in DPDK, a large amount of additional memory is allocated
  for processes linked with DPDK, causing the
  `monitor-cond-change with many sessions pending` test to fail. The following
  series fixes the issue:
  - `17c59ba22a` eal/x86: defer power intrinsics variable allocation
  - `5803893830` power: defer lcore variable allocation
  - `e07b9b8acd` random: defer seeding to EAL init

## check-kernel

- Due to the instability of Libreswan v4 the
  `IPsec -- Libreswan NxN geneve tunnels + reconciliation` test is skipped.

## check-offloads

- With Fedora 39~41 the following test is failing and needs research:
  `163. conntrack - ICMP related with SNAT (system-traffic.at:7529)`
  A patch was sent upstream:
  [patchwork series 445882](https://patchwork.ozlabs.org/project/openvswitch/list/?series=445882)

## check-afxdp

- The latest libxdp does some probing which results in libbpf warnings being
  present in the OVS logs. For now all libbpf log messages are suppressed,
  but this needs a proper fix.
