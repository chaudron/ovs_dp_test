#!/bin/bash
#
# Simple bash script to run all tests in parallel
#
# All additional parameters are passed to ovs_unittests.py.
#
# So to run with a clean VM, you do:
#   ./run_parallel_tmux.sh -c
#
# Or with skipping the provisioning step:
#   ./run_parallel_tmux.sh -p
#
# Check the results on the tmux output. Some times they fail because ssh(mount)
# seem to timeout. Do the following to re-run the test without a new VM build:
#
#   run_test() { time ./ovs_unittests.py "${@:2}" -p --vagrant-vm-cpus=4 --vagrant-vm-name=fedora-$1 -r $1; }
#   run_test XX_testcase_XX
#

export RUN_TEST="run_test() { sleep \$((RANDOM % 10)); time ./ovs_unittests.py \$2 $@ --vagrant-vm-cpus=4 --vagrant-vm-name=fedora-\$1 -r \$1; }"

tmux new -s ovs_tests                   \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     select-layout even-vertical        \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     select-layout even-vertical        \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     select-layout even-vertical        \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     split-window -v                    \; \
     send-keys "eval '$RUN_TEST'" C-m   \; \
     select-layout even-vertical        \; \
     select-pane -t 1                   \; \
     send-keys 'run_test check' C-m     \; \
     select-pane -t 2                   \; \
     send-keys 'run_test kernel' C-m    \; \
     select-pane -t 3                   \; \
     send-keys 'run_test userspace' C-m \; \
     select-pane -t 4                   \; \
     send-keys 'run_test dpdk' C-m      \; \
     select-pane -t 5                   \; \
     send-keys 'run_test offloads' C-m  \; \
     select-pane -t 6                   \; \
     send-keys 'run_test afxdp' C-m     \; \
     select-pane -t 7                   \; \
     send-keys 'run_test ovsdb' C-m     \; \
     select-pane -t 8                   \; \
     send-keys 'run_test tso' C-m       \; \
     detach
