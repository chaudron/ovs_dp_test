# OVS Datapath Test

A simple Vagrant configuration that can be controlled through a Python script
to run all the possible Open vSwitch (OVS) test cases.

It will report back any errors or test cases that are skipped but were not
supposed to be.

## Setup

First, check out the version of OVS and the related DPDK release in the root
of this directory. For example, to check out the latest OVS + DPDK:

```bash
$ git clone https://github.com/openvswitch/ovs.git
$ git clone --branch v25.11.2 http://dpdk.org/git/dpdk-stable dpdk
```

Make sure Vagrant is working on your system and has the `reload` and `sshfs`
plugins installed (see the Vagrantfile for details). In addition, make sure
the Python `rich` module is installed.

## Running Tests

Run all the tests using the following command (takes about 1.5 hours):

```bash
$ ./ovs_unittests.py --clean-vagrant
```

The `--clean-vagrant` option above will re-build the VM. If you already have a
VM ready, you can remove the `--clean-vagrant` option and add the
`--skip-provision` option to speed things up. If you need a re-run and the
build was already done (and there are no code changes), you can also add the
`--skip-build` option.

You can also skip or run a specific test suite only, or run the tests with
ASAN/UBSAN enabled. Add `--help` to see all the possible options.

## Parallel Execution

To run the tests in parallel and avoid the wait, there are tmux bash scripts
that will invoke the `ovs_unittests.py` script multiple times in parallel. It
still has the overhead of building all the OVS binaries in parallel, but it
speeds things up considerably, taking around 35 minutes compared to 90.

Note that the build process might fail occasionally, so you may need to
restart it. See the content of the `run_parallel_tmux.sh` and
`run_ubuntu_parallel_tmux.sh` scripts for more hints on how to restart the
tests in the tmux terminal.

## Notes

> **Note:** The current error checks and skip lists are for running the Fedora
> image. Some failures or skip list entries might not work correctly for Ubuntu.

> **Note (ARM64):** `vagrant destroy` might not work due to NVRAM assignment.
> First manually delete the VM with:
> ```bash
> virsh undefine --nvram ovs_dp_test_fedora
> ```
