This is a simple vagrant configuration that can be controlled through a Python
script to run all the possible Open vSwitch (OVS) test cases.

It will report back the error or any potential test cases that are skipped,
but were not supposed to be.

First, the version of OVS and the related DPDK release should be checked out
in the root of this directory. For example do the following to checkout the
latest OVS + DPDK:

  $ git clone https://github.com/openvswitch/ovs.git
  $ git clone --branch v22.11.3 http://dpdk.org/git/dpdk-stable dpdk

Make sure vagrant is working on your system, and has the 'reload' and 'sshfs'
plugin installed (see the Vagrantfile for details). In addition  make sure the
Python 'rich' module is installed.

Now you can run all the tests using the following command (on my system this
takes about 1.5 hours):

  $ ./ovs_unittests.py --clean-vagrant

The '--clean-vagrant' opion above will re-build the VM. If you already have a
VM ready, you could remove the '--clean-vagrant' option and add the
'--skip-provision' option to speed thinks up. If you need a re-run and the
build was already done (and there are no code changes), you can also add the
'skip-build' option.

You can also skip, or run a specific test suite only, or run the tests with
ASAN/UBSAN enabled. Add --help to see all the possible options.


Being impatient, I would like to run these tests in parallel to avoid the
wait ;) To do this, I hacked some tmux bash scripts together that will invoke
the 'ovs_unittests.py' script multiple times in parallel. It still has the
overhead of building all the OVS binaries in parallel, but it speeds things
up in general. It takes 35 minutes on my system, compared to 90. Also, for
some reason, the build process might fail a lot of times, so you might need
to restart it. See the content of the 'run_parallel_tmux.sh' and
'run_ubuntu_parallel_tmux.sh' scripts for more hints on how to restart the
tests in the tmux terminal.


NOTE: The current error checls, and skiplists are for runnign the Fedora image.
      Some failures or skiplist entries might not work correcrlt for Ubuntu.
